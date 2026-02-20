from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio
from motor.core import AgnosticDatabase


class HomeRepo:
    """
    Reads overview metrics from MongoDB collection: bls_oews

    Fields used:
      - year (int)
      - tot_emp (string/int)  e.g. "131,765,830"
      - naics (string)
      - occ_code (string)
      - a_median (string/int) e.g. "48520"
    """

    def __init__(self, db: AgnosticDatabase):
        self.db = db
        self.col = db["bls_oews"]

    @staticmethod
    def _to_float(v: Any) -> float:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return 0.0

    @staticmethod
    def _add_numeric_fields_stage() -> Dict[str, Any]:
        """
        Safely convert tot_emp and a_median into numeric doubles.
        Handles commas and non-numeric values.
        """
        return {
            "$addFields": {
                "tot_emp_num": {
                    "$convert": {
                        "input": {
                            "$replaceAll": {
                                "input": {"$toString": {"$ifNull": ["$tot_emp", "0"]}},
                                "find": ",",
                                "replacement": "",
                            }
                        },
                        "to": "double",
                        "onError": 0,
                        "onNull": 0,
                    }
                },
                "a_median_num": {
                    "$convert": {
                        "input": {
                            "$replaceAll": {
                                "input": {"$toString": {"$ifNull": ["$a_median", "0"]}},
                                "find": ",",
                                "replacement": "",
                            }
                        },
                        "to": "double",
                        "onError": 0,
                        "onNull": 0,
                    }
                },
            }
        }

    async def _total_employment(self, year: int) -> float:
        pipeline = [
            {"$match": {"year": year}},
            self._add_numeric_fields_stage(),
            {"$group": {"_id": None, "total": {"$sum": "$tot_emp_num"}}},
            {"$project": {"_id": 0, "total": 1}},
        ]
        r = await self.col.aggregate(pipeline).to_list(length=1)
        return float(r[0]["total"]) if r else 0.0

    async def latest_year(self) -> int:
        doc = await self.col.find_one(sort=[("year", -1)], projection={"year": 1})
        return int(doc.get("year", 2024)) if doc else 2024

    async def _year_has_data(self, year: int) -> bool:
        if year is None:
            return False
        count = await self.col.count_documents({"year": year}, limit=1)
        return count > 0

    async def _median_salary(self, year: int) -> float:
        doc = await self.col.find_one(
            {
                "year": year,
                "naics": "000000",
                "occ_title": "All Occupations",
                "naics_title": {"$regex": "^Cross-industry$", "$options": "i"},
            },
            {"_id": 0, "a_median": 1},
        )
        return self._to_float(doc.get("a_median")) if doc else 0.0

    async def _top_growing_industry(self, year: int) -> Optional[Dict[str, Any]]:
        if year <= 0:
            return None
        match_stage = {
            "$match": {
                "year": {"$in": [year, year - 1]},
                "naics": {"$ne": "999000"},
                "naics_title": {"$not": {"$regex": "cross[- ]?industry", "$options": "i"}},
            }
        }
        pipeline = [
            match_stage,
            self._add_numeric_fields_stage(),
            {
                "$group": {
                    "_id": {"naics": "$naics", "year": "$year"},
                    "name": {"$first": "$naics_title"},
                    "max_emp": {"$max": "$tot_emp_num"},
                }
            },
            {
                "$group": {
                    "_id": "$_id.naics",
                    "name": {"$first": "$name"},
                    "years": {"$push": {"year": "$_id.year", "emp": "$max_emp"}},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "naics": "$_id",
                    "name": 1,
                    "emp_cur": {
                        "$let": {
                            "vars": {
                                "cur": {
                                    "$arrayElemAt": [
                                        {
                                            "$filter": {
                                                "input": "$years",
                                                "as": "y",
                                                "cond": {"$eq": ["$$y.year", year]},
                                            }
                                        },
                                        0,
                                    ]
                                }
                            },
                            "in": {"$ifNull": ["$$cur.emp", 0]},
                        }
                    },
                    "emp_prev": {
                        "$let": {
                            "vars": {
                                "prev": {
                                    "$arrayElemAt": [
                                        {
                                            "$filter": {
                                                "input": "$years",
                                                "as": "y",
                                                "cond": {"$eq": ["$$y.year", year - 1]},
                                            }
                                        },
                                        0,
                                    ]
                                }
                            },
                            "in": {"$ifNull": ["$$prev.emp", 0]},
                        }
                    },
                }
            },
            {
                "$addFields": {
                    "trend_pct": {
                        "$cond": [
                            {"$gt": ["$emp_prev", 0]},
                            {"$multiply": [{"$divide": [{"$subtract": ["$emp_cur", "$emp_prev"]}, "$emp_prev"]}, 100]},
                            0,
                        ]
                    }
                }
            },
            {"$sort": {"trend_pct": -1}},
            {"$limit": 1},
        ]
        r = await self.col.aggregate(pipeline).to_list(length=1)
        return r[0] if r else None

    async def _top_growing_occupation(self, year: int) -> Optional[Dict[str, Any]]:
        if year <= 0:
            return None
        pipeline = [
            {"$match": {"year": {"$in": [year, year - 1]}}},
            self._add_numeric_fields_stage(),
            {
                "$group": {
                    "_id": {"occ_code": "$occ_code", "year": "$year"},
                    "name": {"$first": "$occ_title"},
                    "max_emp": {"$max": "$tot_emp_num"},
                }
            },
            {
                "$group": {
                    "_id": "$_id.occ_code",
                    "name": {"$first": "$name"},
                    "years": {"$push": {"year": "$_id.year", "emp": "$max_emp"}},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "occ_code": "$_id",
                    "name": 1,
                    "emp_cur": {
                        "$let": {
                            "vars": {
                                "cur": {
                                    "$arrayElemAt": [
                                        {
                                            "$filter": {
                                                "input": "$years",
                                                "as": "y",
                                                "cond": {"$eq": ["$$y.year", year]},
                                            }
                                        },
                                        0,
                                    ]
                                }
                            },
                            "in": {"$ifNull": ["$$cur.emp", 0]},
                        }
                    },
                    "emp_prev": {
                        "$let": {
                            "vars": {
                                "prev": {
                                    "$arrayElemAt": [
                                        {
                                            "$filter": {
                                                "input": "$years",
                                                "as": "y",
                                                "cond": {"$eq": ["$$y.year", year - 1]},
                                            }
                                        },
                                        0,
                                    ]
                                }
                            },
                            "in": {"$ifNull": ["$$prev.emp", 0]},
                        }
                    },
                }
            },
            {
                "$addFields": {
                    "trend_pct": {
                        "$cond": [
                            {"$gt": ["$emp_prev", 0]},
                            {"$multiply": [{"$divide": [{"$subtract": ["$emp_cur", "$emp_prev"]}, "$emp_prev"]}, 100]},
                            0,
                        ]
                    }
                }
            },
            {"$sort": {"trend_pct": -1}},
            {"$limit": 1},
        ]
        r = await self.col.aggregate(pipeline).to_list(length=1)
        return r[0] if r else None

    async def _highest_paying_occupation(self, year: int) -> Optional[Dict[str, Any]]:
        pipeline = [
            {"$match": {"year": year}},
            self._add_numeric_fields_stage(),
            {
                "$group": {
                    "_id": "$occ_code",
                    "name": {"$first": "$occ_title"},
                    "max_salary": {"$max": "$a_median_num"},
                }
            },
            {"$sort": {"max_salary": -1}},
            {"$limit": 1},
            {"$project": {"_id": 0, "occ_code": "$_id", "name": 1, "salary": "$max_salary"}},
        ]
        r = await self.col.aggregate(pipeline).to_list(length=1)
        return r[0] if r else None

    async def _largest_occupation(self, year: int) -> Optional[Dict[str, Any]]:
        pipeline = [
            {"$match": {"year": year}},
            self._add_numeric_fields_stage(),
            {
                "$group": {
                    "_id": "$occ_code",
                    "name": {"$first": "$occ_title"},
                    "max_emp": {"$max": "$tot_emp_num"},
                }
            },
            {"$sort": {"max_emp": -1}},
            {"$limit": 1},
            {"$project": {"_id": 0, "occ_code": "$_id", "name": 1, "employment": "$max_emp"}},
        ]
        r = await self.col.aggregate(pipeline).to_list(length=1)
        return r[0] if r else None

    async def _top_tech_skill(self) -> Optional[Dict[str, Any]]:
        tech_col = self.db["technology_skills"]
        pipeline = [
            {"$match": {"example": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$example",
                    "count": {"$sum": 1},
                    "hot_count": {
                        "$sum": {"$cond": [{"$eq": ["$hot_technology", True]}, 1, 0]}
                    },
                }
            },
            {"$sort": {"hot_count": -1, "count": -1}},
            {"$limit": 1},
            {"$project": {"_id": 0, "name": "$_id", "count": 1, "hot_count": 1}},
        ]
        r = await tech_col.aggregate(pipeline).to_list(length=1)
        return r[0] if r else None

    async def _hot_tech_count(self) -> int:
        tech_col = self.db["technology_skills"]
        return int(await tech_col.count_documents({"hot_technology": True}))

    async def market_ticker(self, year: Optional[int] = None) -> Dict[str, Any]:
        if year is not None and await self._year_has_data(year):
            y = year
        else:
            y = await self.latest_year()
        (
            med_salary,
            prev_salary,
            top_industry,
            top_occ,
            large_occ,
            top_tech_skill,
            hot_tech_count,
        ) = await asyncio.gather(
            self._median_salary(y),
            self._median_salary(y - 1),
            self._top_growing_industry(y),
            self._top_growing_occupation(y),
            self._largest_occupation(y),
            self._top_tech_skill(),
            self._hot_tech_count(),
        )

        sal_trend = 0.0 if prev_salary <= 0 else ((med_salary - prev_salary) / prev_salary) * 100.0

        return {
            "year": y,
            "median_salary": med_salary,
            "salary_trend_pct": sal_trend,
            "top_growing_industry": top_industry,
            "top_growing_occupation": top_occ,
            "largest_occupation": large_occ,
            "top_tech_skill": top_tech_skill,
            "hot_tech_count": hot_tech_count,
        }

    async def overview(self, year: int) -> Dict[str, Any]:
        """
        Returns:
          {
            year,
            total_employment,
            unique_industries,
            unique_job_titles,
            industry_trend_pct,
            median_annual_salary
          }
        """
        add_nums = self._add_numeric_fields_stage()

        pipeline = [
            {"$match": {"year": year}},
            add_nums,
            {
                "$facet": {
                    "totals": [
                        {
                            "$group": {
                                "_id": None,
                                "total_employment": {"$sum": "$tot_emp_num"},
                                "naics_set": {"$addToSet": "$naics"},
                                "occ_set": {"$addToSet": "$occ_code"},
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "total_employment": 1,
                                "unique_industries": {"$size": "$naics_set"},
                                "unique_job_titles": {"$size": "$occ_set"},
                            }
                        },
                    ],
                }
            },
        ]

        agg = await self.col.aggregate(pipeline).to_list(length=1)
        out = agg[0] if agg else {}

        totals = (out.get("totals") or [{}])[0]
        total_employment = float(totals.get("total_employment", 0.0) or 0.0)
        unique_industries = int(totals.get("unique_industries", 0) or 0)
        unique_job_titles = int(totals.get("unique_job_titles", 0) or 0)
        median_annual_salary = await self._median_salary(year)

        # YoY trend: compare current year total employment to previous year
        prev_total = await self._total_employment(year - 1)
        trend_pct = 0.0
        if prev_total > 0:
            trend_pct = ((total_employment - prev_total) / prev_total) * 100.0

        return {
            "year": year,
            "total_employment": total_employment,
            "unique_industries": unique_industries,
            "unique_job_titles": unique_job_titles,
            "industry_trend_pct": trend_pct,
            "median_annual_salary": median_annual_salary,
        }

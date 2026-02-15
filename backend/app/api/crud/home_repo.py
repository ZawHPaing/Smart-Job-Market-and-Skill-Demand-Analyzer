from __future__ import annotations

from typing import Any, Dict, Optional
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
        self.col = db["bls_oews"]

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
                    "salary": [
                        {"$match": {"a_median_num": {"$gt": 0}}},
                        {"$group": {"_id": None, "vals": {"$push": "$a_median_num"}}},
                        {
                            "$project": {
                                "_id": 0,
                                "median_annual_salary": {
                                    "$let": {
                                        "vars": {
                                            "sorted": {
                                                "$sortArray": {"input": "$vals", "sortBy": 1}
                                            }
                                        },
                                        "in": {
                                            "$let": {
                                                "vars": {"n": {"$size": "$$sorted"}},
                                                "in": {
                                                    "$cond": [
                                                        {"$eq": ["$$n", 0]},
                                                        0,
                                                        {
                                                            "$arrayElemAt": [
                                                                "$$sorted",
                                                                {"$floor": {"$divide": ["$$n", 2]}},
                                                            ]
                                                        },
                                                    ]
                                                },
                                            }
                                        },
                                    }
                                },
                            }
                        },
                    ],
                }
            },
        ]

        agg = await self.col.aggregate(pipeline).to_list(length=1)
        out = agg[0] if agg else {}

        totals = (out.get("totals") or [{}])[0]
        salary = (out.get("salary") or [{}])[0]

        total_employment = float(totals.get("total_employment", 0.0) or 0.0)
        unique_industries = int(totals.get("unique_industries", 0) or 0)
        unique_job_titles = int(totals.get("unique_job_titles", 0) or 0)
        median_annual_salary = float(salary.get("median_annual_salary", 0.0) or 0.0)

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

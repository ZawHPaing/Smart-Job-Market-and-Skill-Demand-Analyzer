from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Literal
from functools import lru_cache
import asyncio

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase


def _to_float(v: Any) -> float:
    """Robust numeric parser for BLS fields - handles strings, quoted numbers, and invalid data"""
    if v is None:
        return 0.0
    
    # Handle quoted numbers like "67500" or '67500'
    if isinstance(v, str):
        v = v.strip().strip('"').strip("'")
    
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip()
    if not s or s in ("*", "#", "**", "***", "nan", "NaN", "None", ""):
        return 0.0

    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0


class JobsRepo:
    """
    Jobs/Occupations repository.
    Returns data from bls_oews collection using MAX aggregation:
    - For single year queries, takes MAX tot_emp per occupation
    - For multi-year trends, takes MAX tot_emp per year to handle duplicates
    """
    
    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
        self._onet_cache = None
        self._onet_cache_time = 0
    
    async def _get_onet_socs(self, force_refresh: bool = False) -> set:
        """Cache O*NET SOC codes to avoid repeated distinct() calls"""
        import time
        current_time = time.time()
        
        # Refresh cache every 5 minutes or if forced
        if self._onet_cache is None or force_refresh or current_time - self._onet_cache_time > 300:
            onet_socs = set()
            
            # Run distinct queries in parallel
            collections = ["skills", "technology_skills", "abilities", "knowledge", "work_activities"]
            tasks = [self.db[col].distinct("onet_soc") for col in collections]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                onet_socs.update(result)
            
            self._onet_cache = onet_socs
            self._onet_cache_time = current_time
        
        return self._onet_cache
    
    async def _latest_year(self) -> Optional[int]:
        doc = await self.db["bls_oews"].find_one(
            {"naics": "000000"}, 
            {"year": 1, "_id": 0},
            sort=[("year", -1)]
        )
        return int(doc["year"]) if doc else None
    
    async def get_job_market_trend(self, year: int) -> float:
        """
        Calculate job market growth percentage by comparing total employment
        with previous year using MAX employment values - single aggregation
        """
        pipeline = [
            {
                "$match": {
                    "year": {"$in": [int(year), int(year - 1)]},
                    "occ_code": {"$ne": "00-0000"},
                    "tot_emp": {"$ne": None, "$ne": ""}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": "$year",
                        "occ_code": "$occ_code"
                    },
                    "max_emp": {"$max": "$tot_emp"}
                }
            },
            {
                "$group": {
                    "_id": "$_id.year",
                    "total_emp": {"$sum": "$max_emp"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = await self.db["bls_oews"].aggregate(pipeline).to_list(length=None)
        
        emp_by_year = {r["_id"]: r["total_emp"] for r in results}
        current_emp = _to_float(emp_by_year.get(int(year), 0))
        prev_emp = _to_float(emp_by_year.get(int(year - 1), 0))
        
        if prev_emp == 0:
            return 0.0
        
        growth_pct = ((current_emp - prev_emp) / prev_emp) * 100
        return round(growth_pct, 1)
    
    # -------------------------
    # Jobs list / search - OPTIMIZED MAX APPROACH
    # -------------------------
    async def list_jobs(
        self, 
        year: Optional[int] = None,
        group: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        only_with_details: bool = True
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get list of unique occupations - uses MAX tot_emp per occupation for the year
        """
        if year is None:
            year = await self._latest_year()
            if year is None:
                return 0, []
        
        pipeline = [
            {
                "$match": {
                    "year": int(year),
                    "occ_code": {"$ne": "00-0000"},
                    "occ_title": {"$ne": None, "$ne": ""}
                }
            }
        ]
        
        # Add filters
        if group:
            pipeline[0]["$match"]["group"] = group
        if search:
            pipeline[0]["$match"]["occ_title"] = {"$regex": search, "$options": "i"}
        
        # O*NET SOC filtering
        if only_with_details:
            onet_socs = await self._get_onet_socs()
            if onet_socs:
                # Convert O*NET SOC codes to BLS format (remove .00)
                bls_codes = [soc.replace(".00", "") for soc in onet_socs if isinstance(soc, str)]
                if bls_codes:
                    pipeline[0]["$match"]["occ_code"] = {"$in": list(set(bls_codes))}
        
        # Optimized aggregation without $convert/$trim
        pipeline.extend([
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "group": {"$first": "$group"},
                    "max_emp": {"$max": "$tot_emp"},
                    "all_docs": {"$push": {
                        "tot_emp": "$tot_emp",
                        "a_median": "$a_median"
                    }}
                }
            },
            {
                "$addFields": {
                    "selected_doc": {
                        "$arrayElemAt": [
                            {
                                "$filter": {
                                    "input": "$all_docs",
                                    "as": "doc",
                                    "cond": {"$eq": ["$$doc.tot_emp", "$max_emp"]}
                                }
                            },
                            0
                        ]
                    }
                }
            },
            {
                "$project": {
                    "occ_title": 1,
                    "group": 1,
                    "total_employment": "$max_emp",
                    "a_median": "$selected_doc.a_median"
                }
            },
            {
                "$match": {
                    "total_employment": {"$gt": 0}
                }
            },
            {"$sort": {"total_employment": -1}},
            {"$skip": offset},
            {"$limit": limit}
        ])
        
        rows = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            rows.append({
                "occ_code": str(doc.get("_id", "")),
                "occ_title": str(doc.get("occ_title", "")),
                "group": str(doc.get("group", "")) or None,
                "total_employment": _to_float(doc.get("total_employment", 0)),
                "a_median": _to_float(doc.get("a_median", 0)) or None,
            })
        
        return int(year), rows
    
    async def search_jobs(
        self,
        query: str,
        year: Optional[int] = None,
        limit: int = 20,
        only_with_details: bool = True
    ) -> List[Dict[str, Any]]:
        _, jobs = await self.list_jobs(
            year=year, 
            search=query, 
            limit=limit, 
            offset=0,
            only_with_details=only_with_details
        )
        return jobs
    
    # -------------------------
    # Top jobs - OPTIMIZED MAX APPROACH
    # -------------------------
    async def top_jobs(
        self,
        year: int,
        limit: int = 10,
        by: Literal["employment", "salary"] = "employment",
        group: Optional[str] = None,
        only_with_details: bool = True
    ) -> List[Dict[str, Any]]:
        """Top jobs using MAX tot_emp per occupation"""
        
        pipeline = [
            {
                "$match": {
                    "year": int(year),
                    "occ_code": {"$ne": "00-0000"}
                }
            }
        ]
        
        if group:
            pipeline[0]["$match"]["group"] = group
        
        # O*NET SOC filtering
        if only_with_details:
            onet_socs = await self._get_onet_socs()
            if onet_socs:
                bls_codes = [soc.replace(".00", "") for soc in onet_socs if isinstance(soc, str)]
                if bls_codes:
                    pipeline[0]["$match"]["occ_code"] = {"$in": list(set(bls_codes))}
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "group": {"$first": "$group"},
                    "max_emp": {"$max": "$tot_emp"},
                    "all_docs": {"$push": {
                        "tot_emp": "$tot_emp",
                        "a_median": "$a_median"
                    }}
                }
            },
            {
                "$addFields": {
                    "selected_doc": {
                        "$arrayElemAt": [
                            {
                                "$filter": {
                                    "input": "$all_docs",
                                    "as": "doc",
                                    "cond": {"$eq": ["$$doc.tot_emp", "$max_emp"]}
                                }
                            },
                            0
                        ]
                    }
                }
            },
            {
                "$project": {
                    "occ_title": 1,
                    "group": 1,
                    "total_employment": "$max_emp",
                    "a_median": "$selected_doc.a_median"
                }
            },
            {
                "$match": {
                    "total_employment": {"$gt": 0}
                }
            }
        ])
        
        # Add sorting based on criteria
        if by == "salary":
            pipeline.append({"$match": {"a_median": {"$ne": None, "$gt": 0}}})
            pipeline.append({"$sort": {"a_median": -1}})
        else:
            pipeline.append({"$sort": {"total_employment": -1}})
        
        pipeline.append({"$limit": limit})
        
        rows = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            rows.append({
                "occ_code": str(doc.get("_id", "")),
                "occ_title": str(doc.get("occ_title", "")),
                "total_employment": _to_float(doc.get("total_employment", 0)),
                "a_median": _to_float(doc.get("a_median", 0)) or None,
                "group": str(doc.get("group", "")) or None,
                "growth_pct": None
            })
        
        return rows
    
    async def top_jobs_with_growth(
        self,
        year: int,
        limit: int = 10,
        group: Optional[str] = None,
        only_with_details: bool = True
    ) -> List[Dict[str, Any]]:
        """Top jobs - with O*NET data only"""
        return await self.top_jobs(
            year=year, 
            limit=limit, 
            by="employment", 
            group=group,
            only_with_details=only_with_details
        )
    
    # -------------------------
    # Top jobs trends - OPTIMIZED (SINGLE QUERY)
    # -------------------------
    async def top_jobs_trends(
        self,
        year_from: int,
        year_to: int,
        limit: int = 10,
        group: Optional[str] = None,
        sort_by: Literal["employment", "salary"] = "employment",
        only_with_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get employment trends for top jobs over time - single aggregation
        """
        # First, get top jobs at the end year
        top_jobs_end = await self.top_jobs(
            year=year_to,
            limit=limit,
            by=sort_by,
            group=group,
            only_with_details=only_with_details
        )
        
        if not top_jobs_end:
            return []
        
        occ_codes = [job["occ_code"] for job in top_jobs_end]
        years = list(range(min(year_from, year_to), max(year_from, year_to) + 1))
        
        # Single aggregation for all occupations
        pipeline = [
            {
                "$match": {
                    "occ_code": {"$in": occ_codes},
                    "year": {"$in": years}
                }
            },
            {
                "$group": {
                    "_id": {
                        "occ_code": "$occ_code",
                        "year": "$year"
                    },
                    "max_emp": {"$max": "$tot_emp"}
                }
            },
            {
                "$group": {
                    "_id": "$_id.occ_code",
                    "points": {
                        "$push": {
                            "year": "$_id.year",
                            "employment": "$max_emp"
                        }
                    }
                }
            },
            {
                "$project": {
                    "points": {
                        "$map": {
                            "input": years,
                            "as": "y",
                            "in": {
                                "$let": {
                                    "vars": {
                                        "match": {
                                            "$filter": {
                                                "input": "$points",
                                                "as": "p",
                                                "cond": {"$eq": ["$$p.year", "$$y"]}
                                            }
                                        }
                                    },
                                    "in": {
                                        "$cond": {
                                            "if": {"$gt": [{"$size": "$$match"}, 0]},
                                            "then": {"$arrayElemAt": ["$$match", 0]},
                                            "else": {"year": "$$y", "employment": 0}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ]
        
        # Create lookup map for job titles
        title_map = {job["occ_code"]: job["occ_title"] for job in top_jobs_end}
        
        series = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            code = doc["_id"]
            series.append({
                "occ_code": code,
                "occ_title": title_map.get(code, ""),
                "points": sorted(doc["points"], key=lambda x: x["year"])
            })
        
        return series
    
    # -------------------------
    # Top jobs salary trends - OPTIMIZED (SINGLE QUERY)
    # -------------------------
    async def top_jobs_salary_trends(
        self,
        year_from: int,
        year_to: int,
        limit: int = 10,
        group: Optional[str] = None,
        sort_by: Literal["employment", "salary"] = "employment",
        only_with_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get salary trends for top jobs over time - returns raw salary values
        """
        # First, get top jobs at the end year
        top_jobs_end = await self.top_jobs(
            year=year_to,
            limit=limit,
            by=sort_by,
            group=group,
            only_with_details=only_with_details
        )
        
        if not top_jobs_end:
            return []
        
        occ_codes = [job["occ_code"] for job in top_jobs_end]
        years = list(range(min(year_from, year_to), max(year_from, year_to) + 1))
        
        # Create lookup map for job titles
        title_map = {job["occ_code"]: job["occ_title"] for job in top_jobs_end}
        
        # Single aggregation for all occupations
        pipeline = [
            {
                "$match": {
                    "occ_code": {"$in": occ_codes},
                    "year": {"$in": years}
                }
            },
            {
                "$group": {
                    "_id": {
                        "occ_code": "$occ_code",
                        "year": "$year"
                    },
                    "salary": {"$max": "$a_median"},  # Take max salary for the year
                    "occ_title": {"$first": "$occ_title"}
                }
            },
            {
                "$group": {
                    "_id": "$_id.occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "points": {
                        "$push": {
                            "year": "$_id.year",
                            "salary": "$salary"
                        }
                    }
                }
            },
            {
                "$project": {
                    "occ_title": 1,
                    "points": {
                        "$map": {
                            "input": years,
                            "as": "y",
                            "in": {
                                "$let": {
                                    "vars": {
                                        "match": {
                                            "$filter": {
                                                "input": "$points",
                                                "as": "p",
                                                "cond": {"$eq": ["$$p.year", "$$y"]}
                                            }
                                        }
                                    },
                                    "in": {
                                        "$cond": {
                                            "if": {"$gt": [{"$size": "$$match"}, 0]},
                                            "then": {
                                                "year": "$$y",
                                                "salary": {"$arrayElemAt": ["$$match.salary", 0]}
                                            },
                                            "else": {
                                                "year": "$$y",
                                                "salary": 0
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ]
        
        series = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            code = doc["_id"]
            
            # Sort points by year and carry forward last valid salary
            points = sorted(doc["points"], key=lambda x: x["year"])
            
            # Carry forward last valid salary for missing years
            last_valid = 0
            cleaned_points = []
            for point in points:
                if point["salary"] > 0:
                    last_valid = point["salary"]
                    cleaned_points.append(point)
                else:
                    cleaned_points.append({
                        "year": point["year"],
                        "salary": last_valid  # Use last valid salary instead of 0
                    })
            
            series.append({
                "occ_code": code,
                "occ_title": title_map.get(code, doc.get("occ_title", "")),
                "points": cleaned_points
            })
        
        return series
    
    # -------------------------
    # Dashboard metrics - OPTIMIZED (SINGLE AGGREGATION)
    # -------------------------
    async def dashboard_metrics(self, year: int, only_with_details: bool = True) -> Dict[str, Any]:
        """Dashboard metrics using MAX employment values - single aggregation"""
        
        # Get job market trend (already optimized)
        job_market_trend = await self.get_job_market_trend(year)
        
        # Build match stage for filtering
        match_stage = {
            "year": int(year),
            "occ_code": {"$ne": "00-0000"}
        }
        
        if only_with_details:
            onet_socs = await self._get_onet_socs()
            if onet_socs:
                bls_codes = [soc.replace(".00", "") for soc in onet_socs if isinstance(soc, str)]
                if bls_codes:
                    match_stage["occ_code"] = {"$in": list(set(bls_codes))}
        
        # Single aggregation for all metrics
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "max_emp": {"$max": "$tot_emp"},
                    "all_salaries": {"$push": "$a_median"}
                }
            },
            {
                "$match": {
                    "max_emp": {"$gt": 0}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_jobs": {"$sum": 1},
                    "total_employment": {"$sum": "$max_emp"},
                    "salaries": {"$push": "$all_salaries"}
                }
            },
            {
                "$project": {
                    "total_jobs": 1,
                    "total_employment": 1,
                    "salaries": {
                        "$reduce": {
                            "input": "$salaries",
                            "initialValue": [],
                            "in": {"$concatArrays": ["$$value", "$$this"]}
                        }
                    }
                }
            }
        ]
        
        result = await self.db["bls_oews"].aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "year": int(year),
                "total_jobs": 0,
                "total_employment": 0.0,
                "avg_job_growth_pct": job_market_trend,
                "top_growing_job": None,
                "a_median": 65000.0
            }
        
        doc = result[0]
        total_jobs = doc.get("total_jobs", 0)
        total_employment = _to_float(doc.get("total_employment", 0))
        
        # Calculate median salary
        salaries = [s for s in doc.get("salaries", []) if s is not None and s > 0]
        salaries.sort()
        
        median_salary = 0.0
        if salaries:
            n = len(salaries)
            mid = n // 2
            if n % 2 == 1:
                median_salary = salaries[mid]
            else:
                median_salary = (salaries[mid - 1] + salaries[mid]) / 2.0
        
        return {
            "year": int(year),
            "total_jobs": int(total_jobs),
            "total_employment": round(total_employment, 2),
            "avg_job_growth_pct": job_market_trend,
            "top_growing_job": None,
            "a_median": round(median_salary, 2) if median_salary > 0 else 65000.0
        }
    
    # -------------------------
    # Jobs in industry - KEEPS INDUSTRY FILTER
    # -------------------------
    async def jobs_in_industry(
        self,
        naics: str,
        year: int,
        limit: int = 200,
        offset: int = 0
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Jobs within a specific industry - keeps industry filter"""
        q = {
            "year": int(year),
            "naics": naics,
            "occ_code": {"$ne": "00-0000"}
        }
        
        cursor = self.db["bls_oews"].find(
            q,
            {"_id": 0, "occ_code": 1, "occ_title": 1, "tot_emp": 1, "a_median": 1, "naics_title": 1}
        ).sort("tot_emp", -1).skip(offset).limit(limit)
        
        rows = []
        naics_title = ""
        
        async for doc in cursor:
            if not naics_title:
                naics_title = str(doc.get("naics_title", "")).strip()
            
            rows.append({
                "occ_code": str(doc.get("occ_code", "")),
                "occ_title": str(doc.get("occ_title", "")),
                "employment": _to_float(doc.get("tot_emp")),
                "a_median": _to_float(doc.get("a_median")) or None,
                "naics_title": naics_title
            })
        
        return naics_title, rows
    
    # -------------------------
    # Job groups - OPTIMIZED (SINGLE AGGREGATION)
    # -------------------------
    async def job_groups(self, year: int, only_with_details: bool = True) -> List[Dict[str, str]]:
        """Get distinct occupation groups using MAX approach"""
        
        match_stage = {
            "year": int(year),
            "occ_code": {"$ne": "00-0000"},
            "group": {"$ne": None, "$ne": ""}
        }
        
        if only_with_details:
            onet_socs = await self._get_onet_socs()
            if onet_socs:
                bls_codes = [soc.replace(".00", "") for soc in onet_socs if isinstance(soc, str)]
                if bls_codes:
                    match_stage["occ_code"] = {"$in": list(set(bls_codes))}
        
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$occ_code",
                    "group": {"$first": "$group"}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "groups": {"$addToSet": "$group"}
                }
            }
        ]
        
        result = await self.db["bls_oews"].aggregate(pipeline).to_list(length=1)
        
        if not result:
            return []
        
        groups = sorted(result[0]["groups"])
        return [{"group": g} for g in groups]
    
    # -------------------------
    # Job metrics - OPTIMIZED
    # -------------------------
    async def job_metrics(
        self, 
        occ_code: str, 
        year: int,
        naics: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for a specific job using MAX approach"""
        
        if naics:
            # Specific industry - no MAX needed
            q = {
                "year": int(year), 
                "occ_code": occ_code,
                "naics": naics
            }
            
            doc = await self.db["bls_oews"].find_one(
                q,
                {"_id": 0, "occ_title": 1, "tot_emp": 1, "a_median": 1, "group": 1, "naics_title": 1}
            )
            
            if not doc:
                return {
                    "occ_code": occ_code,
                    "occ_title": "",
                    "year": year,
                    "total_employment": 0.0,
                    "a_median": None,
                    "group": None,
                    "naics": naics,
                    "naics_title": None
                }
            
            return {
                "occ_code": occ_code,
                "occ_title": str(doc.get("occ_title", "")),
                "year": year,
                "total_employment": _to_float(doc.get("tot_emp")),
                "a_median": _to_float(doc.get("a_median")) or None,
                "group": str(doc.get("group", "")) or None,
                "naics": naics,
                "naics_title": str(doc.get("naics_title", ""))
            }
        else:
            # Aggregate across all industries using MAX
            pipeline = [
                {
                    "$match": {
                        "year": int(year),
                        "occ_code": occ_code
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "occ_title": {"$first": "$occ_title"},
                        "group": {"$first": "$group"},
                        "max_emp": {"$max": "$tot_emp"},
                        "all_docs": {"$push": {
                            "tot_emp": "$tot_emp",
                            "a_median": "$a_median"
                        }}
                    }
                },
                {
                    "$addFields": {
                        "selected_doc": {
                            "$arrayElemAt": [
                                {
                                    "$filter": {
                                        "input": "$all_docs",
                                        "as": "doc",
                                        "cond": {"$eq": ["$$doc.tot_emp", "$max_emp"]}
                                    }
                                },
                                0
                            ]
                        }
                    }
                },
                {
                    "$project": {
                        "occ_title": 1,
                        "group": 1,
                        "total_employment": "$max_emp",
                        "a_median": "$selected_doc.a_median"
                    }
                }
            ]
            
            result = await self.db["bls_oews"].aggregate(pipeline).to_list(length=1)
            
            if not result:
                return {
                    "occ_code": occ_code,
                    "occ_title": "",
                    "year": year,
                    "total_employment": 0.0,
                    "a_median": None,
                    "group": None,
                    "naics": None,
                    "naics_title": None
                }
            
            doc = result[0]
            return {
                "occ_code": occ_code,
                "occ_title": str(doc.get("occ_title", "")),
                "year": year,
                "total_employment": _to_float(doc.get("total_employment", 0)),
                "a_median": _to_float(doc.get("a_median", 0)) or None,
                "group": str(doc.get("group", "")) or None,
                "naics": None,
                "naics_title": None
            }
    
    async def job_summary(
        self,
        occ_code: str,
        year_from: int,
        year_to: int,
        naics: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Time series summary for a job using MAX per year"""
        
        years = list(range(min(year_from, year_to), max(year_from, year_to) + 1))
        
        if naics:
            # Specific industry - no MAX needed
            pipeline = [
                {
                    "$match": {
                        "occ_code": occ_code,
                        "naics": naics,
                        "year": {"$in": years}
                    }
                },
                {
                    "$project": {
                        "year": 1,
                        "total_employment": "$tot_emp",
                        "a_median": 1,
                        "occ_title": 1
                    }
                },
                {
                    "$sort": {"year": 1}
                }
            ]
        else:
            # Aggregate across all industries using MAX per year
            pipeline = [
                {
                    "$match": {
                        "occ_code": occ_code,
                        "year": {"$in": years}
                    }
                },
                {
                    "$group": {
                        "_id": "$year",
                        "max_emp": {"$max": "$tot_emp"},
                        "all_salaries": {"$push": "$a_median"},
                        "occ_title": {"$first": "$occ_title"}
                    }
                },
                {
                    "$project": {
                        "year": "$_id",
                        "total_employment": "$max_emp",
                        "a_median": {"$arrayElemAt": ["$all_salaries", 0]},  # Salary from first doc (we'll have only one due to grouping)
                        "occ_title": 1
                    }
                },
                {
                    "$sort": {"year": 1}
                }
            ]
        
        cursor = self.db["bls_oews"].aggregate(pipeline)
        
        series = []
        job_title = ""
        
        # Create a map of year -> data
        year_map = {}
        async for doc in cursor:
            year = doc["year"]
            if not job_title:
                job_title = str(doc.get("occ_title", ""))
            
            year_map[year] = {
                "year": year,
                "total_employment": _to_float(doc.get("total_employment", 0)),
                "a_median": _to_float(doc.get("a_median", 0)) or None
            }
        
        # Build complete series for all years
        complete_series = []
        for y in sorted(years):
            if y in year_map:
                complete_series.append(year_map[y])
            else:
                complete_series.append({
                    "year": y,
                    "total_employment": 0.0,
                    "a_median": None
                })
        
        return job_title, complete_series
    
    # -------------------------
    # Simplified methods
    # -------------------------
    async def job_composition_by_group(self, year: int) -> List[Dict[str, Any]]:
        """Return empty list"""
        return []
    
    async def salary_distribution(
        self,
        year: int,
        group: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return default values"""
        return {
            "year": year,
            "group": group,
            "total_jobs": 0,
            "q1": 0,
            "median": 0,
            "q3": 0,
            "min": 0,
            "max": 0
        }
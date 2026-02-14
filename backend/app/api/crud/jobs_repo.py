from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Literal

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
    Returns data from bls_oews collection using hybrid MAX approach:
    - For single year queries, takes MAX tot_emp per occupation
    - For multi-year trends, takes MAX tot_emp per year to handle duplicates
    """
    
    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
    
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
        with previous year using MAX employment values
        """
        # Get previous year
        prev_year = year - 1
        
        # Calculate total employment for current year using MAX per occupation
        pipeline_current = [
            {
                "$match": {
                    "year": int(year),
                    "occ_code": {"$ne": "00-0000"},
                    "tot_emp": {"$ne": None, "$ne": ""}
                }
            },
            {
                "$addFields": {
                    "tot_emp_num": {
                        "$convert": {
                            "input": {
                                "$trim": {
                                    "input": {
                                        "$toString": "$tot_emp"
                                    }
                                }
                            },
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$occ_code",
                    "max_emp": {"$max": "$tot_emp_num"}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_emp": {"$sum": "$max_emp"}
                }
            }
        ]
        
        # Calculate total employment for previous year using MAX per occupation
        pipeline_prev = [
            {
                "$match": {
                    "year": int(prev_year),
                    "occ_code": {"$ne": "00-0000"},
                    "tot_emp": {"$ne": None, "$ne": ""}
                }
            },
            {
                "$addFields": {
                    "tot_emp_num": {
                        "$convert": {
                            "input": {
                                "$trim": {
                                    "input": {
                                        "$toString": "$tot_emp"
                                    }
                                }
                            },
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$occ_code",
                    "max_emp": {"$max": "$tot_emp_num"}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_emp": {"$sum": "$max_emp"}
                }
            }
        ]
        
        current_result = await self.db["bls_oews"].aggregate(pipeline_current).to_list(length=1)
        prev_result = await self.db["bls_oews"].aggregate(pipeline_prev).to_list(length=1)
        
        current_emp = _to_float(current_result[0]["total_emp"]) if current_result else 0.0
        prev_emp = _to_float(prev_result[0]["total_emp"]) if prev_result else 0.0
        
        if prev_emp == 0:
            return 0.0
        
        # Calculate growth percentage
        growth_pct = ((current_emp - prev_emp) / prev_emp) * 100
        return round(growth_pct, 1)
    
    # -------------------------
    # Jobs list / search - HYBRID MAX APPROACH
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
        
        # First, get all O*NET SOC codes that have data
        onet_socs = set()
        
        if only_with_details:
            # Get all SOC codes that have skills
            cursor = await self.db["skills"].distinct("onet_soc")
            onet_socs.update(cursor)
            
            # Also include those with tech skills
            cursor = await self.db["technology_skills"].distinct("onet_soc")
            onet_socs.update(cursor)
            
            # Include abilities
            cursor = await self.db["abilities"].distinct("onet_soc")
            onet_socs.update(cursor)
            
            # Include knowledge
            cursor = await self.db["knowledge"].distinct("onet_soc")
            onet_socs.update(cursor)
            
            # Include work activities
            cursor = await self.db["work_activities"].distinct("onet_soc")
            onet_socs.update(cursor)
        
        # Build match query
        match_q = {
            "year": int(year),
            "occ_code": {"$ne": "00-0000"},
            "occ_title": {"$ne": None, "$ne": ""}
        }
        
        if group:
            match_q["group"] = group
        if search:
            match_q["occ_title"] = {"$regex": search, "$options": "i"}
        
        # Only include jobs that map to O*NET SOCs with data
        if only_with_details and onet_socs:
            # Convert O*NET SOC codes to BLS format (remove .00)
            bls_codes = []
            for soc in onet_socs:
                if soc and isinstance(soc, str):
                    bls_code = soc.replace(".00", "")
                    bls_codes.append(bls_code)
            
            if bls_codes:
                bls_codes = list(set(bls_codes))
                match_q["occ_code"] = {"$in": bls_codes}
        
        # Aggregate to get MAX tot_emp and associated a_median for each occupation
        pipeline = [
            {"$match": match_q},
            {
                "$addFields": {
                    "tot_emp_num": {
                        "$convert": {
                            "input": {
                                "$trim": {
                                    "input": {
                                        "$toString": "$tot_emp"
                                    }
                                }
                            },
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    },
                    "a_median_num": {
                        "$convert": {
                            "input": {
                                "$trim": {
                                    "input": {
                                        "$toString": "$a_median"
                                    }
                                }
                            },
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    }
                }
            },
            {
                "$sort": {"tot_emp_num": -1}
            },
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "group": {"$first": "$group"},
                    "total_employment": {"$first": "$tot_emp_num"},
                    "a_median": {"$first": "$a_median_num"}
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
        ]
        
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
    # Top jobs - HYBRID MAX APPROACH
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
        
        # First, get all O*NET SOC codes that have data
        onet_socs = set()
        
        if only_with_details:
            # Get all SOC codes that have skills
            cursor = await self.db["skills"].distinct("onet_soc")
            onet_socs.update(cursor)
            
            # Also include those with tech skills
            cursor = await self.db["technology_skills"].distinct("onet_soc")
            onet_socs.update(cursor)
            
            # Include abilities
            cursor = await self.db["abilities"].distinct("onet_soc")
            onet_socs.update(cursor)
        
        # Build match query
        match_q = {
            "year": int(year),
            "occ_code": {"$ne": "00-0000"}
        }
        
        if group:
            match_q["group"] = group
        
        # Only include jobs that map to O*NET SOCs with data
        if only_with_details and onet_socs:
            # Convert O*NET SOC codes to BLS format (remove .00)
            bls_codes = []
            for soc in onet_socs:
                if soc and isinstance(soc, str):
                    bls_code = soc.replace(".00", "")
                    bls_codes.append(bls_code)
            
            if bls_codes:
                bls_codes = list(set(bls_codes))
                match_q["occ_code"] = {"$in": bls_codes}
        
        # Aggregate to get MAX tot_emp and associated values
        pipeline = [
            {"$match": match_q},
            {
                "$addFields": {
                    "tot_emp_num": {
                        "$convert": {
                            "input": {
                                "$trim": {
                                    "input": {
                                        "$toString": "$tot_emp"
                                    }
                                }
                            },
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    },
                    "a_median_num": {
                        "$convert": {
                            "input": {
                                "$trim": {
                                    "input": {
                                        "$toString": "$a_median"
                                    }
                                }
                            },
                            "to": "double",
                            "onError": 0,
                            "onNull": 0
                        }
                    }
                }
            },
            {
                "$sort": {"tot_emp_num": -1}
            },
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "group": {"$first": "$group"},
                    "total_employment": {"$first": "$tot_emp_num"},
                    "a_median": {"$first": "$a_median_num"}
                }
            },
            {
                "$match": {
                    "total_employment": {"$gt": 0}
                }
            }
        ]
        
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
        
        # Sort based on criteria
        if by == "employment":
            rows.sort(key=lambda r: r.get("total_employment", 0.0), reverse=True)
        else:  # salary
            rows = [r for r in rows if r.get("a_median") is not None]
            rows.sort(key=lambda r: r.get("a_median", 0.0), reverse=True)
        
        return rows[:limit]
    
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
    # Top jobs employment trends - HYBRID MAX APPROACH
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
        Get employment trends for top jobs over time - uses MAX tot_emp per year
        to handle cases where multiple documents exist for the same occupation/year
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
        
        # Build years list
        years = list(range(min(year_from, year_to), max(year_from, year_to) + 1))
        
        series = []
        
        for job in top_jobs_end:
            code = job["occ_code"]
            title = job["occ_title"]
            
            # Get ALL documents for this occupation across all years (any NAICS)
            cursor = self.db["bls_oews"].find(
                {
                    "occ_code": code,
                    "year": {"$in": years}
                },
                {
                    "_id": 0,
                    "year": 1,
                    "tot_emp": 1
                }
            ).sort("year", 1)
            
            # Create a map of year -> list of employment values
            year_emp_map = {}
            async for doc in cursor:
                year = doc["year"]
                emp = _to_float(doc.get("tot_emp", 0))
                
                if year not in year_emp_map:
                    year_emp_map[year] = []
                year_emp_map[year].append(emp)
            
            # Build points array using MAX employment value for each year
            points = []
            for y in years:
                if y in year_emp_map:
                    emp = max(year_emp_map[y])
                else:
                    emp = 0
                points.append({"year": y, "employment": emp})
            
            series.append({
                "occ_code": code,
                "occ_title": title,
                "points": points
            })
        
        return series
    
    # -------------------------
    # Top jobs salary trends - HYBRID MAX APPROACH
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
        Get salary trends for top jobs over time - uses MAX tot_emp to select the right document
        Returns list of series with salary data for each year
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
        
        # Build years list
        years = list(range(min(year_from, year_to), max(year_from, year_to) + 1))
        
        series = []
        
        for job in top_jobs_end:
            code = job["occ_code"]
            title = job["occ_title"]
            
            # Get ALL documents for this occupation across all years
            # Then for each year, find the document with MAX tot_emp and use its a_median
            pipeline = [
                {
                    "$match": {
                        "occ_code": code,
                        "year": {"$in": years}
                    }
                },
                {
                    "$addFields": {
                        "tot_emp_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$tot_emp"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        },
                        "a_median_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$a_median"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        }
                    }
                },
                {
                    "$sort": {"tot_emp_num": -1}
                },
                {
                    "$group": {
                        "_id": "$year",
                        "salary": {"$first": "$a_median_num"},
                        "year": {"$first": "$year"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "year": 1,
                        "salary": 1
                    }
                },
                {
                    "$sort": {"year": 1}
                }
            ]
            
            cursor = self.db["bls_oews"].aggregate(pipeline)
            
            # Create a map of year -> salary
            salary_map = {}
            async for doc in cursor:
                salary_map[doc["year"]] = doc["salary"]
            
            # Build points array for all years
            points = []
            for y in years:
                salary = salary_map.get(y, 0)
                points.append({"year": y, "salary": salary})
            
            series.append({
                "occ_code": code,
                "occ_title": title,
                "points": points
            })
        
        return series
    
    # -------------------------
    # Dashboard metrics - HYBRID MAX APPROACH
    # -------------------------
    async def dashboard_metrics(self, year: int, only_with_details: bool = True) -> Dict[str, Any]:
        """Dashboard metrics using MAX employment values"""
        
        # Get job market trend
        job_market_trend = await self.get_job_market_trend(year)
        
        # First, get filtered job list using MAX approach
        _, jobs = await self.list_jobs(
            year=year, 
            limit=10000, 
            offset=0, 
            only_with_details=only_with_details
        )
        
        # Count unique occupations
        total_jobs = len(jobs)
        
        # Sum total employment
        total_employment = sum(job["total_employment"] for job in jobs)
        
        # Get median salary from jobs list
        salaries = [job["a_median"] for job in jobs if job.get("a_median") is not None]
        median_salary = 0.0
        if salaries:
            salaries.sort()
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
    # Job groups - HYBRID MAX APPROACH
    # -------------------------
    async def job_groups(self, year: int, only_with_details: bool = True) -> List[Dict[str, str]]:
        """Get distinct occupation groups using MAX approach"""
        
        # Get filtered job list
        _, jobs = await self.list_jobs(
            year=year, 
            limit=10000, 
            offset=0, 
            only_with_details=only_with_details
        )
        
        # Extract unique groups from jobs list
        groups = set()
        for job in jobs:
            if job.get("group"):
                groups.add(job["group"])
        
        return [{"group": g} for g in sorted(groups)]
    
    # -------------------------
    # Job metrics - HYBRID MAX APPROACH
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
                    "$addFields": {
                        "tot_emp_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$tot_emp"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        },
                        "a_median_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$a_median"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        }
                    }
                },
                {
                    "$sort": {"tot_emp_num": -1}
                },
                {
                    "$group": {
                        "_id": None,
                        "occ_title": {"$first": "$occ_title"},
                        "group": {"$first": "$group"},
                        "total_employment": {"$first": "$tot_emp_num"},
                        "a_median": {"$first": "$a_median_num"}
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
                    "$addFields": {
                        "tot_emp_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$tot_emp"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        },
                        "a_median_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$a_median"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "year": 1,
                        "total_employment": "$tot_emp_num",
                        "a_median": "$a_median_num",
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
                    "$addFields": {
                        "tot_emp_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$tot_emp"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        },
                        "a_median_num": {
                            "$convert": {
                                "input": {
                                    "$trim": {
                                        "input": {
                                            "$toString": "$a_median"
                                        }
                                    }
                                },
                                "to": "double",
                                "onError": 0,
                                "onNull": 0
                            }
                        }
                    }
                },
                {
                    "$sort": {"tot_emp_num": -1}
                },
                {
                    "$group": {
                        "_id": "$year",
                        "total_employment": {"$first": "$tot_emp_num"},
                        "a_median": {"$first": "$a_median_num"},
                        "occ_title": {"$first": "$occ_title"}
                    }
                },
                {
                    "$project": {
                        "year": "$_id",
                        "total_employment": 1,
                        "a_median": 1,
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

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
    Jobs/Occupations repository - SIMPLIFIED.
    Just returns raw data from bls_oews collection.
    Handles both numeric and string numeric fields.
    """
    
    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
    
    async def _latest_year(self) -> Optional[int]:
        doc = await self.db["bls_oews"].find_one(
            {}, 
            {"year": 1, "_id": 0},
            sort=[("year", -1)]
        )
        return int(doc["year"]) if doc else None
    
    # -------------------------
    # Jobs list / search - WITH OPTION 1 FILTERING
    # -------------------------
    async def list_jobs(
        self, 
        year: Optional[int] = None,
        group: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        only_with_details: bool = True  # ADD THIS PARAMETER
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get list of unique occupations - only those with O*NET data
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
            
            print(f"📊 Found {len(onet_socs)} O*NET SOC codes with data")
        
        # Use cross-industry data
        match_q = {
            "year": int(year),
            "naics": "000000",  # Use cross-industry data
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
                    # Convert "15-1252.00" to "15-1252"
                    bls_code = soc.replace(".00", "")
                    bls_codes.append(bls_code)
            
            if bls_codes:
                # Remove duplicates
                bls_codes = list(set(bls_codes))
                match_q["occ_code"] = {"$in": bls_codes}
                print(f"📊 Filtering to {len(bls_codes)} BLS codes with O*NET data")
        
        # Simple distinct query
        pipeline = [
            {"$match": match_q},
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "group": {"$first": "$group"},
                    "tot_emp": {"$first": "$tot_emp"},
                    "a_median": {"$first": "$a_median"}
                }
            },
            {"$sort": {"tot_emp": -1}},
            {"$skip": offset},
            {"$limit": limit}
        ]
        
        rows = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            rows.append({
                "occ_code": str(doc.get("_id", "")),
                "occ_title": str(doc.get("occ_title", "")),
                "group": str(doc.get("group", "")) or None,
                "total_employment": _to_float(doc.get("tot_emp")),
                "median_salary": _to_float(doc.get("a_median")) or None,
            })
        
        print(f"📊 Returning {len(rows)} jobs")
        return int(year), rows
    
    async def search_jobs(
        self,
        query: str,
        year: Optional[int] = None,
        limit: int = 20,
        only_with_details: bool = True  # ADD THIS PARAMETER
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
    # Top jobs - WITH OPTION 1 FILTERING
    # -------------------------
    async def top_jobs(
        self,
        year: int,
        limit: int = 10,
        by: Literal["employment", "salary"] = "employment",
        group: Optional[str] = None,
        only_with_details: bool = True  # ADD THIS PARAMETER
    ) -> List[Dict[str, Any]]:
        """Top jobs from cross-industry data - only those with O*NET data"""
        
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
        
        match_q = {
            "year": int(year),
            "naics": "000000",  # Use cross-industry data
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
        
        pipeline = [
            {"$match": match_q},
            {
                "$group": {
                    "_id": "$occ_code",
                    "occ_title": {"$first": "$occ_title"},
                    "group": {"$first": "$group"},
                    "tot_emp": {"$first": "$tot_emp"},
                    "a_median": {"$first": "$a_median"}
                }
            }
        ]
        
        rows = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            rows.append({
                "occ_code": str(doc.get("_id", "")),
                "occ_title": str(doc.get("occ_title", "")),
                "total_employment": _to_float(doc.get("tot_emp")),
                "median_salary": _to_float(doc.get("a_median")) or None,
                "group": str(doc.get("group", "")) or None,
                "growth_pct": None
            })
        
        # Sort in Python
        key = "total_employment" if by == "employment" else "median_salary"
        rows.sort(key=lambda r: r.get(key, 0.0), reverse=True)
        return rows[:limit]
    
    async def top_jobs_with_growth(
        self,
        year: int,
        limit: int = 10,
        group: Optional[str] = None,
        only_with_details: bool = True  # ADD THIS PARAMETER
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
    # Dashboard metrics - MODIFIED to use only jobs with details
    # -------------------------
    async def dashboard_metrics(self, year: int, only_with_details: bool = True) -> Dict[str, Any]:
        """Dashboard metrics from cross-industry data - only jobs with O*NET data"""
        
        # First, get filtered job list
        _, jobs = await self.list_jobs(
            year=year, 
            limit=10000, 
            offset=0, 
            only_with_details=only_with_details
        )
        
        # Extract job codes
        job_codes = [job["occ_code"] for job in jobs]
        
        # Count unique occupations
        pipeline_count = [
            {
                "$match": {
                    "year": int(year),
                    "naics": "000000",
                    "occ_code": {"$in": job_codes, "$ne": "00-0000"},
                    "occ_title": {"$ne": None}
                }
            },
            {"$group": {"_id": "$occ_code"}},
            {"$count": "total"}
        ]
        
        count_result = await self.db["bls_oews"].aggregate(pipeline_count).to_list(length=1)
        total_jobs = count_result[0]["total"] if count_result else 0
        
        # Sum total employment
        pipeline_emp = [
            {
                "$match": {
                    "year": int(year),
                    "naics": "000000",
                    "occ_code": {"$in": job_codes, "$ne": "00-0000"},
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
                    "_id": None,
                    "total_emp": {"$sum": "$tot_emp_num"}
                }
            }
        ]
        
        emp_result = await self.db["bls_oews"].aggregate(pipeline_emp).to_list(length=1)
        total_employment = _to_float(emp_result[0]["total_emp"]) if emp_result else 0.0
        
        # Get median salary
        pipeline_salary = [
            {
                "$match": {
                    "year": int(year),
                    "naics": "000000",
                    "occ_code": {"$in": job_codes, "$ne": "00-0000"},
                    "a_median": {"$ne": None, "$ne": ""}
                }
            },
            {
                "$addFields": {
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
                "$match": {
                    "a_median_num": {"$gt": 0}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "salaries": {"$push": "$a_median_num"}
                }
            }
        ]
        
        salary_result = await self.db["bls_oews"].aggregate(pipeline_salary).to_list(length=1)
        median_salary = 0.0
        if salary_result:
            salaries = salary_result[0].get("salaries", [])
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
            "avg_job_growth_pct": 0.0,
            "top_growing_job": None,
            "median_job_salary": round(median_salary, 2) if median_salary > 0 else 65000.0
        }
    
    # -------------------------
    # Top jobs trends - SIMPLIFIED
    # -------------------------
    async def top_jobs_trends(
        self,
        year_from: int,
        year_to: int,
        limit: int = 4,
        group: Optional[str] = None,
        only_with_details: bool = True  # ADD THIS PARAMETER
    ) -> List[Dict[str, Any]]:
        """Return empty list for now"""
        return []
    
    # -------------------------
    # Jobs in industry - NO CHANGE
    # -------------------------
    async def jobs_in_industry(
        self,
        naics: str,
        year: int,
        limit: int = 200,
        offset: int = 0
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Jobs within a specific industry"""
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
                "median_salary": _to_float(doc.get("a_median")) or None,
                "naics_title": naics_title
            })
        
        return naics_title, rows
    
    # -------------------------
    # Job groups - MODIFIED to use only jobs with details
    # -------------------------
    async def job_groups(self, year: int, only_with_details: bool = True) -> List[Dict[str, str]]:
        """Get distinct occupation groups from cross-industry data - only jobs with O*NET data"""
        
        # Get filtered job list
        _, jobs = await self.list_jobs(
            year=year, 
            limit=10000, 
            offset=0, 
            only_with_details=only_with_details
        )
        
        job_codes = [job["occ_code"] for job in jobs]
        
        pipeline = [
            {
                "$match": {
                    "year": int(year),
                    "naics": "000000",
                    "occ_code": {"$in": job_codes, "$ne": "00-0000"},
                    "group": {"$ne": None, "$ne": ""}
                }
            },
            {"$group": {"_id": "$group"}},
            {"$sort": {"_id": 1}}
        ]
        
        groups = []
        async for doc in self.db["bls_oews"].aggregate(pipeline):
            groups.append({"group": str(doc.get("_id", "")).strip()})
        
        return groups
    
    # -------------------------
    # Simplified methods - NO CHANGE
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
    
    async def job_metrics(
        self, 
        occ_code: str, 
        year: int,
        naics: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for a specific job"""
        q = {
            "year": int(year), 
            "occ_code": occ_code
        }
        
        if naics:
            q["naics"] = naics
        else:
            q["naics"] = "000000"  # Default to cross-industry
        
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
                "median_salary": None,
                "group": None,
                "naics": naics,
                "naics_title": None
            }
        
        return {
            "occ_code": occ_code,
            "occ_title": str(doc.get("occ_title", "")),
            "year": year,
            "total_employment": _to_float(doc.get("tot_emp")),
            "median_salary": _to_float(doc.get("a_median")) or None,
            "group": str(doc.get("group", "")) or None,
            "naics": naics,
            "naics_title": str(doc.get("naics_title", "")) if naics else None
        }
    
    async def job_summary(
        self,
        occ_code: str,
        year_from: int,
        year_to: int,
        naics: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Return single year summary"""
        metrics = await self.job_metrics(occ_code, year_to, naics)
        return metrics.get("occ_title", ""), [{
            "year": year_to,
            "total_employment": metrics["total_employment"],
            "median_salary": metrics["median_salary"]
        }]
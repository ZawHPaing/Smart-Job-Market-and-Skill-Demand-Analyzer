from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from collections import defaultdict
import asyncio
import time

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase


def _to_float(v: Any) -> float:
    """Robust numeric parser for O*NET fields"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except:
        return 0.0


def _scale_to_percentage(value: float, scale: str = "IM") -> float:
    """Convert O*NET scale (0-5 or 0-100) to percentage"""
    if scale in ["IM", "RL"]:  # Importance (0-5)
        return round((value / 5.0) * 100, 1)
    elif scale in ["LV", "RT"]:  # Level (0-7)
        return round((value / 7.0) * 100, 1)
    return round(value, 1)


def _get_education_description(category: int) -> str:
    """Map education category to description"""
    education_levels = {
        0: "No formal educational credential",
        1: "Primary school",
        2: "Secondary school",
        3: "Some college courses",
        4: "Associate's degree",
        5: "Bachelor's degree",
        6: "Post-baccalaureate certificate",
        7: "Master's degree",
        8: "Post-master's certificate",
        9: "Doctoral degree",
        10: "Post-doctoral training",
        11: "First professional degree",
        12: "Post-professional degree"
    }
    return education_levels.get(category, "Not specified")


class JobDetailRepo:
    """
    Repository for job details using O*NET collections with 3-hour caching.
    - abilities
    - education_training_experience
    - knowledge
    - skills
    - technology_skills
    - tools_used
    - work_activities
    
    Uses optimized MAX aggregation to match JobsRepo methodology.
    All caches last 3 hours (10800 seconds).
    """
    
    # Add caches
    _job_detail_cache: Dict[str, Dict[str, Any]] = {}
    _job_detail_cache_time: Dict[str, float] = {}
    _job_growth_cache: Dict[str, float] = {}
    _job_growth_cache_time: Dict[str, float] = {}
    _job_salary_cache: Dict[str, float] = {}
    _job_salary_cache_time: Dict[str, float] = {}
    _top_industry_cache: Dict[str, Dict[str, Any]] = {}
    _top_industry_cache_time: Dict[str, float] = {}
    _onet_soc_cache: Dict[str, Optional[str]] = {}
    _onet_soc_cache_time: Dict[str, float] = {}
    _experience_cache: Dict[str, str] = {}
    _experience_cache_time: Dict[str, float] = {}
    
    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
    
    # -------------------------
    # OPTIMIZED BLS DATA METHODS - WITH CACHING
    # -------------------------
    
    async def get_job_by_occ_code(self, occ_code: str, year: int) -> Optional[Dict[str, Any]]:
        """
        Get basic job info using MAX tot_emp approach - with 3-hour cache.
        Year is required to match specific year data.
        """
        cache_key = f"job_{occ_code}_{year}"
        now = time.time()
        
        # Check cache
        if cache_key in self._job_detail_cache:
            if now - self._job_detail_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ Job detail cache HIT for {occ_code} {year}")
                return self._job_detail_cache[cache_key]
        
        pipeline = [
            {
                "$match": {
                    "occ_code": occ_code,
                    "year": year
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
                    "_id": 0,
                    "occ_code": occ_code,
                    "occ_title": 1,
                    "group": 1,
                    "tot_emp": "$max_emp",
                    "a_median": "$selected_doc.a_median"
                }
            }
        ]
        
        result = await self.db["bls_oews"].aggregate(pipeline).to_list(length=1)
        
        if result:
            doc = result[0]
            job_data = {
                "occ_code": occ_code,
                "occ_title": str(doc.get("occ_title", "")),
                "tot_emp": _to_float(doc.get("tot_emp", 0)),
                "a_median": _to_float(doc.get("a_median", 0)),
                "group": doc.get("group")
            }
            
            # Update cache
            self._job_detail_cache[cache_key] = job_data
            self._job_detail_cache_time[cache_key] = now
            
            return job_data
        return None
    
    async def get_job_growth_trend(self, occ_code: str) -> float:
        """
        Calculate job growth percentage - with 3-hour cache.
        Matches JobsRepo.get_job_market_trend methodology
        """
        cache_key = f"growth_{occ_code}"
        now = time.time()
        
        # Check cache
        if cache_key in self._job_growth_cache:
            if now - self._job_growth_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ Job growth cache HIT for {occ_code}")
                return self._job_growth_cache[cache_key]
        
        pipeline = [
            {
                "$match": {
                    "occ_code": occ_code
                }
            },
            {
                "$group": {
                    "_id": "$year",
                    "max_emp": {"$max": "$tot_emp"}
                }
            },
            {
                "$sort": {"_id": -1}
            },
            {
                "$limit": 2
            }
        ]
        
        results = await self.db["bls_oews"].aggregate(pipeline).to_list(length=2)
        
        if len(results) < 2:
            return 0.0
        
        current = results[0]
        previous = results[1]
        
        current_emp = _to_float(current.get("max_emp", 0))
        prev_emp = _to_float(previous.get("max_emp", 0))
        
        if prev_emp == 0:
            return 0.0
        
        growth_pct = ((current_emp - prev_emp) / prev_emp) * 100
        result = round(growth_pct, 1)
        
        # Update cache
        self._job_growth_cache[cache_key] = result
        self._job_growth_cache_time[cache_key] = now
        
        return result
    
    async def get_job_salary_trend(self, occ_code: str) -> float:
        """
        Calculate salary growth percentage - with 3-hour cache.
        Takes salary from document with MAX tot_emp for each year
        """
        cache_key = f"salary_{occ_code}"
        now = time.time()
        
        # Check cache
        if cache_key in self._job_salary_cache:
            if now - self._job_salary_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ Job salary cache HIT for {occ_code}")
                return self._job_salary_cache[cache_key]
        
        pipeline = [
            {
                "$match": {
                    "occ_code": occ_code
                }
            },
            {
                "$group": {
                    "_id": "$year",
                    "max_emp": {"$max": "$tot_emp"},
                    "all_salaries": {"$push": "$a_median"}
                }
            },
            {
                "$sort": {"_id": -1}
            },
            {
                "$limit": 2
            }
        ]
        
        results = await self.db["bls_oews"].aggregate(pipeline).to_list(length=2)
        
        if len(results) < 2:
            return 0.0
        
        current = results[0]
        previous = results[1]
        
        # Take first salary (from document with max emp)
        current_salary = _to_float(current.get("all_salaries", [0])[0]) if current.get("all_salaries") else 0
        prev_salary = _to_float(previous.get("all_salaries", [0])[0]) if previous.get("all_salaries") else 0
        
        if prev_salary == 0:
            return 0.0
        
        growth_pct = ((current_salary - prev_salary) / prev_salary) * 100
        result = round(growth_pct, 1)
        
        # Update cache
        self._job_salary_cache[cache_key] = result
        self._job_salary_cache_time[cache_key] = now
        
        return result
    
    async def get_top_industry(self, occ_code: str, year: int) -> Optional[Dict[str, Any]]:
        """
        Get the top non-cross-industry industry for this occupation by total employment.
        Uses MAX aggregation to find the document with highest tot_emp for each industry,
        then selects the industry with highest employment excluding:
        - "Cross-industry" (naics 000000)
        - "Cross-industry, private ownership only" (naics 000001)
        With 3-hour cache.
        """
        cache_key = f"top_ind_{occ_code}_{year}"
        now = time.time()
        
        # Check cache
        if cache_key in self._top_industry_cache:
            if now - self._top_industry_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ Top industry cache HIT for {occ_code} {year}")
                return self._top_industry_cache[cache_key]
        
        pipeline = [
            {
                "$match": {
                    "occ_code": occ_code,
                    "year": year,
                    "naics": {"$nin": ["000000", "000001"]},  # Exclude both cross-industry codes
                    "naics_title": {"$nin": ["Cross-industry", "Cross-industry, private ownership only"]}  # Also exclude by title for safety
                }
            },
            {
                "$group": {
                    "_id": "$naics",
                    "naics_title": {"$first": "$naics_title"},
                    "max_emp": {"$max": "$tot_emp"},
                    "all_docs": {"$push": {
                        "tot_emp": "$tot_emp",
                        "naics_title": "$naics_title"
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
                    "_id": 0,
                    "naics": "$_id",
                    "naics_title": 1,
                    "tot_emp": "$max_emp"
                }
            },
            {
                "$sort": {"tot_emp": -1}
            },
            {
                "$limit": 1
            }
        ]
        
        result = await self.db["bls_oews"].aggregate(pipeline).to_list(length=1)
        
        if result:
            doc = result[0]
            industry_data = {
                "naics": doc.get("naics", ""),
                "naics_title": str(doc.get("naics_title", "")),
                "tot_emp": _to_float(doc.get("tot_emp", 0))
            }
            
            # Update cache
            self._top_industry_cache[cache_key] = industry_data
            self._top_industry_cache_time[cache_key] = now
            
            return industry_data
        return None
    
    # -------------------------
    # O*NET DATA METHODS
    # -------------------------
    
    async def get_experience_required(self, onet_soc: str) -> str:
        """Get experience required from education/training data - with 3-hour cache."""
        cache_key = f"exp_{onet_soc}"
        now = time.time()
        
        # Check cache
        if cache_key in self._experience_cache:
            if now - self._experience_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ Experience cache HIT for {onet_soc}")
                return self._experience_cache[cache_key]
        
        doc = await self.db["education_training_experience"].find_one(
            {
                "onet_soc": onet_soc,
                "element_name": "Related Work Experience"
            },
            {"_id": 0, "data_value": 1, "category": 1}
        )
        
        if doc:
            value = _to_float(doc.get("data_value", 0))
            if value >= 8:
                result = "10+ years"
            elif value >= 7:
                result = "8-10 years"
            elif value >= 6:
                result = "6-8 years"
            elif value >= 5:
                result = "4-6 years"
            elif value >= 4:
                result = "2-4 years"
            elif value >= 3:
                result = "1-2 years"
            elif value >= 2:
                result = "6 months - 1 year"
            elif value >= 1:
                result = "Less than 6 months"
            else:
                result = "None"
        else:
            result = "Not specified"
        
        # Update cache
        self._experience_cache[cache_key] = result
        self._experience_cache_time[cache_key] = now
        
        return result
    
    async def get_onet_soc(self, occ_code: str) -> Optional[str]:
        """Map BLS OCC code to O*NET SOC code format - with 3-hour cache."""
        cache_key = f"onet_{occ_code}"
        now = time.time()
        
        # Check cache
        if cache_key in self._onet_soc_cache:
            if now - self._onet_soc_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ ONET SOC cache HIT for {occ_code}")
                return self._onet_soc_cache[cache_key]
        
        if not occ_code:
            result = None
        else:
            occ_code = occ_code.strip()
            
            if ".00" in occ_code:
                result = occ_code
            elif "-" in occ_code and len(occ_code) >= 6:
                result = f"{occ_code}.00"
            else:
                result = None
        
        # Update cache
        self._onet_soc_cache[cache_key] = result
        self._onet_soc_cache_time[cache_key] = now
        
        return result
    
    async def find_onet_soc_by_title(self, title: str) -> Optional[str]:
        """Find O*NET SOC code by job title - with 3-hour cache."""
        cache_key = f"onet_title_{title}"
        now = time.time()
        
        # Check cache
        if cache_key in self._onet_soc_cache:
            if now - self._onet_soc_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ ONET title cache HIT for {title[:30]}...")
                return self._onet_soc_cache[cache_key]
        
        if not title:
            return None
        
        doc = await self.db["skills"].find_one(
            {"title": {"$regex": title, "$options": "i"}},
            {"onet_soc": 1}
        )
        if doc:
            result = doc.get("onet_soc")
            # Update cache
            self._onet_soc_cache[cache_key] = result
            self._onet_soc_cache_time[cache_key] = now
            return result
        
        for collection in ["abilities", "knowledge", "work_activities"]:
            doc = await self.db[collection].find_one(
                {"title": {"$regex": title, "$options": "i"}},
                {"onet_soc": 1}
            )
            if doc:
                result = doc.get("onet_soc")
                # Update cache
                self._onet_soc_cache[cache_key] = result
                self._onet_soc_cache_time[cache_key] = now
                return result
        
        return None
    
    async def get_skills(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get skills from O*NET skills collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["skills"].find(
            q,
            {"_id": 0, "element_name": 1, "data_value": 1, "scale_id": 1}
        )
        
        skills = []
        async for doc in cursor:
            value = _to_float(doc.get("data_value", 0))
            scale = doc.get("scale_id", "IM")
            skills.append({
                "name": str(doc.get("element_name", "")),
                "value": _scale_to_percentage(value, scale),
                "type": "skill",
                "element_id": doc.get("element_id"),
                "scale_id": scale
            })
        
        skills.sort(key=lambda x: x["value"], reverse=True)
        return skills
    
    async def get_technology_skills(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get technology skills from O*NET technology_skills collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["technology_skills"].find(
            q,
            {"_id": 0, "example": 1, "commodity_title": 1, "hot_technology": 1, "in_demand": 1}
        )
        
        tech_skills = []
        async for doc in cursor:
            hot_tech = doc.get("hot_technology", False)
            in_demand = doc.get("in_demand", False)
            
            # Assign percentage based on flags
            if hot_tech and in_demand:
                value = 95.0  # Both flags: highest priority
            elif hot_tech:
                value = 85.0  # Only hot tech
            elif in_demand:
                value = 75.0  # Only in demand
            else:
                value = 65.0  # Neither flag
            
            tech_skills.append({
                "name": str(doc.get("example", "")),
                "value": value,
                "type": "tech",
                "commodity_title": str(doc.get("commodity_title", "")),
                "hot_technology": hot_tech,
                "in_demand": in_demand
            })
        
        # Sort by value (percentage) in descending order
        # This will put skills with both flags first, then hot tech, then in demand, then others
        tech_skills.sort(key=lambda x: x["value"], reverse=True)
        return tech_skills
    
    async def get_tools(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get tools from O*NET tools_used collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["tools_used"].find(
            q,
            {"_id": 0, "example": 1, "commodity_title": 1}
        )
        
        tools = []
        async for doc in cursor:
            tools.append({
                "name": str(doc.get("example", "")),
                "value": 60.0,
                "type": "tool",
                "commodity_title": str(doc.get("commodity_title", ""))
            })
        
        # Sort by name (alphabetical) since tools don't have importance values
        tools.sort(key=lambda x: x["name"])
        return tools
    
    async def get_abilities(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get abilities from O*NET abilities collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["abilities"].find(
            q,
            {"_id": 0, "element_name": 1, "data_value": 1, "scale_id": 1, "element_id": 1}
        )
        
        abilities = []
        category_map = {
            "1.A.1": "Cognitive",
            "1.A.2": "Physical",
            "1.A.3": "Psychomotor",
            "1.A.4": "Sensory",
            "1.B.1": "Social",
            "1.B.2": "Personal"
        }
        
        async for doc in cursor:
            element_id = str(doc.get("element_id", ""))
            category = "Cognitive"
            for prefix, cat in category_map.items():
                if element_id.startswith(prefix):
                    category = cat
                    break
            
            value = _to_float(doc.get("data_value", 0))
            scale = doc.get("scale_id", "IM")
            
            abilities.append({
                "name": str(doc.get("element_name", "")),
                "category": category,
                "value": _scale_to_percentage(value, scale),
                "element_id": element_id
            })
        
        abilities.sort(key=lambda x: x["value"], reverse=True)
        return abilities
    
    async def get_knowledge(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get knowledge areas from O*NET knowledge collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["knowledge"].find(
            q,
            {"_id": 0, "element_name": 1, "data_value": 1, "scale_id": 1, "element_id": 1}
        )
        
        knowledge = []
        async for doc in cursor:
            value = _to_float(doc.get("data_value", 0))
            scale = doc.get("scale_id", "IM")
            percentage = _scale_to_percentage(value, scale)
            
            level = "Basic"
            if percentage >= 80:
                level = "Expert"
            elif percentage >= 60:
                level = "Advanced"
            elif percentage >= 40:
                level = "Intermediate"
            
            knowledge.append({
                "name": str(doc.get("element_name", "")),
                "level": level,
                "value": percentage,
                "element_id": doc.get("element_id")
            })
        
        knowledge.sort(key=lambda x: x["value"], reverse=True)
        return knowledge
    
    async def get_education(self, onet_soc: str) -> Optional[Dict[str, Any]]:
        """Get education requirements from O*NET education collection"""
        q = {
            "onet_soc": onet_soc,
            "element_name": "Required Level of Education"
        }
        
        doc = await self.db["education_training_experience"].find_one(
            q,
            {"_id": 0, "category": 1, "data_value": 1}
        )
        
        if doc:
            category = int(doc.get("category", 0))
            value = _to_float(doc.get("data_value", 0))
            
            return {
                "category": category,
                "description": _get_education_description(category),
                "required_level": _get_education_description(category),
                "value": _scale_to_percentage(value, "RL")
            }
        return None
    
    async def get_work_activities(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get work activities from O*NET work_activities collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["work_activities"].find(
            q,
            {"_id": 0, "element_name": 1, "data_value": 1, "scale_id": 1, "element_id": 1}
        )
        
        activities = []
        async for doc in cursor:
            value = _to_float(doc.get("data_value", 0))
            scale = doc.get("scale_id", "IM")
            activities.append({
                "name": str(doc.get("element_name", "")),
                "value": _scale_to_percentage(value, scale),
                "element_id": doc.get("element_id")
            })
        
        activities.sort(key=lambda x: x["value"], reverse=True)
        return activities
    
    # -------------------------
    # COMPLETE JOB DETAIL - OPTIMIZED PARALLEL FETCHING WITH ALL ITEMS
    # -------------------------
    
    async def get_complete_job_detail(self, occ_code: str, year: int = 2024) -> Dict[str, Any]:
        """Get complete job details - optimized with parallel fetching and 3-hour cache."""
        
        cache_key = f"complete_{occ_code}_{year}"
        now = time.time()
        
        # Check cache for complete result
        if cache_key in self._job_detail_cache:
            if now - self._job_detail_cache_time.get(cache_key, 0) < 10800:  # 3 hours
                print(f"✅ Complete job detail cache HIT for {occ_code} {year}")
                return self._job_detail_cache[cache_key]
        
        # Get basic job info using optimized method (matches JobsRepo)
        basic_info = await self.get_job_by_occ_code(occ_code, year)
        
        # Get O*NET SOC code
        onet_soc = await self.get_onet_soc(occ_code)
        
        # If no matching SOC, try to find by title
        if not onet_soc and basic_info:
            title = basic_info.get("occ_title", "")
            onet_soc = await self.find_onet_soc_by_title(title)
        
        # Initialize result
        result = {
            "occ_code": occ_code,
            "occ_title": basic_info.get("occ_title", "") if basic_info else "",
            "basic_info": {
                "occ_code": occ_code,
                "occ_title": basic_info.get("occ_title", "") if basic_info else "",
                "soc_code": onet_soc,
                "year": year
            },
            "metrics": [],
            "skills": [],
            "tech_skills": [],
            "soft_skills": [],
            "activities": [],
            "abilities": [],
            "knowledge": [],
            "education": None,
            "tools": [],
            "work_activities": []
        }
        
        if not onet_soc or not basic_info:
            return result
        
        # Fetch all O*NET data in parallel
        tasks = [
            self.get_skills(onet_soc),
            self.get_technology_skills(onet_soc),
            self.get_tools(onet_soc),
            self.get_abilities(onet_soc),
            self.get_knowledge(onet_soc),
            self.get_education(onet_soc),
            self.get_work_activities(onet_soc),
        ]
        
        # Fetch trend data and industry in parallel
        trend_tasks = [
            self.get_job_growth_trend(occ_code),
            self.get_job_salary_trend(occ_code),
            self.get_experience_required(onet_soc),
            self.get_top_industry(occ_code, year)  # Added industry
        ]
        
        # Wait for all data
        onet_results = await asyncio.gather(*tasks)
        trend_results = await asyncio.gather(*trend_tasks)
        
        skills, tech_skills, tools, abilities, knowledge, education, activities = onet_results
        # Unpack trend_results - now includes industry
        growth_trend, salary_trend, experience, industry = trend_results
        
        # Categorize skills - soft skills should come from the top skills list
        all_skills = skills
        tech_skills_list = tech_skills
        soft_skills_list = []
        
        # Define soft skills keywords to identify them in the skills list
        soft_keywords = [
            "communication", "teamwork", "collaboration", "leadership", "problem solving", 
            "critical thinking", "active learning", "social", "coordination",
            "negotiation", "persuasion", "service", "management", "speaking",
            "writing", "listening", "cooperating", "instructing", "interpersonal",
            "adaptability", "flexibility", "creativity", "initiative", "dependability",
            "attention to detail", "organization", "time management", "emotional intelligence",
            "conflict resolution", "decision making", "mentoring", "training"
        ]
        
        # First, add all skills and mark them
        for skill in all_skills:
            skill_name = skill["name"].lower()
            # Check if it's a soft skill
            if any(keyword in skill_name for keyword in soft_keywords):
                skill["type"] = "soft"
                soft_skills_list.append(skill)
            else:
                skill["type"] = "general"
        
        # Sort soft skills by value and take top ones
        soft_skills_list.sort(key=lambda x: x["value"], reverse=True)
        
        # Generate metrics
        metrics = []
        if basic_info:
            total_employment = _to_float(basic_info.get("tot_emp", 0))
            median_salary = _to_float(basic_info.get("a_median", 0))
            
            growth_direction = "up" if growth_trend >= 0 else "down"
            salary_direction = "up" if salary_trend >= 0 else "down"
            
            metrics = [
                {
                    "title": "Total Employment",
                    "value": total_employment,
                    "trend": {"value": abs(growth_trend), "direction": growth_direction},
                    "color": "cyan",
                    "format": "fmtM"
                },
                {
                    "title": "Job Trend",
                    "value": growth_trend,  # Keep as number, frontend will add % sign
                    "trend": {"value": abs(growth_trend), "direction": growth_direction},
                    "color": "green",
                    "suffix": "%"  # Add suffix for percentage
                },
                {
                    "title": "Top Industry",
                    "value": industry["naics_title"] if industry else "Various",
                    "color": "coral",
                    "format": "industry"
                },
                {
                    "title": "Median Annual Salary",
                    "value": median_salary,
                    "prefix": "$",
                    "trend": {"value": abs(salary_trend), "direction": salary_direction},
                    "color": "amber",
                    "format": "fmtK"
                }
            ]
        
        # Update result with ALL items (removed limits, all sorted by value descending)
        result.update({
            "metrics": metrics,
            "skills": all_skills,  # ← ALL skills, already sorted by value
            "tech_skills": tech_skills_list,  # ← ALL tech skills, already sorted by value
            "soft_skills": soft_skills_list,  # ← ALL soft skills, already sorted by value
            "activities": activities,  # ← ALL activities, already sorted by value
            "abilities": abilities,  # ← ALL abilities, already sorted by value
            "knowledge": knowledge,  # ← ALL knowledge, already sorted by value
            "education": education,
            "tools": tools,  # ← ALL tools, sorted alphabetically
            "work_activities": activities,  # ← ALL work activities, already sorted by value
            "industry": industry  # Add industry to the result
        })
        
        # Update cache with complete result
        self._job_detail_cache[cache_key] = result
        self._job_detail_cache_time[cache_key] = now
        
        return result
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from collections import defaultdict
import asyncio

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
    Repository for job details using O*NET collections:
    - abilities
    - education_training_experience
    - knowledge
    - skills
    - technology_skills
    - tools_used
    - work_activities
    
    Uses optimized MAX aggregation to match JobsRepo methodology.
    """
    
    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
    
    # -------------------------
    # OPTIMIZED BLS DATA METHODS - MATCHING JOBSREPO
    # -------------------------
    
    async def get_job_by_occ_code(self, occ_code: str, year: int = 2024) -> Optional[Dict[str, Any]]:
        """
        Get basic job info using MAX tot_emp approach - matches JobsRepo.top_jobs()
        Single aggregation for maximum performance.
        """
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
            return {
                "occ_code": occ_code,
                "occ_title": str(doc.get("occ_title", "")),
                "tot_emp": _to_float(doc.get("tot_emp", 0)),
                "a_median": _to_float(doc.get("a_median", 0)),
                "group": doc.get("group")
            }
        return None
    
    async def get_job_growth_trend(self, occ_code: str) -> float:
        """
        Calculate job growth percentage - optimized single aggregation
        Matches JobsRepo.get_job_market_trend methodology
        """
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
        return round(growth_pct, 1)
    
    async def get_job_salary_trend(self, occ_code: str) -> float:
        """
        Calculate salary growth percentage - optimized single aggregation
        Takes salary from document with MAX tot_emp for each year
        """
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
        return round(growth_pct, 1)
    
    # -------------------------
    # O*NET DATA METHODS (KEEP AS IS - THESE ARE FAST ENOUGH)
    # -------------------------
    
    async def get_experience_required(self, onet_soc: str) -> str:
        """Get experience required from education/training data"""
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
                return "10+ years"
            elif value >= 7:
                return "8-10 years"
            elif value >= 6:
                return "6-8 years"
            elif value >= 5:
                return "4-6 years"
            elif value >= 4:
                return "2-4 years"
            elif value >= 3:
                return "1-2 years"
            elif value >= 2:
                return "6 months - 1 year"
            elif value >= 1:
                return "Less than 6 months"
            else:
                return "None"
        
        return "Not specified"
    
    async def get_skill_intensity(self, onet_soc: str) -> float:
        """Calculate average skill intensity (average of top skills)"""
        skills = await self.get_skills(onet_soc)
        if skills:
            top_skills = skills[:10]
            avg_value = sum(s["value"] for s in top_skills) / len(top_skills)
            return round(avg_value / 10, 1)
        return 0.0
    
    async def get_onet_soc(self, occ_code: str) -> Optional[str]:
        """Map BLS OCC code to O*NET SOC code format"""
        if not occ_code:
            return None
        
        occ_code = occ_code.strip()
        
        if ".00" in occ_code:
            return occ_code
        
        if "-" in occ_code and len(occ_code) >= 6:
            return f"{occ_code}.00"
        
        return None
    
    async def find_onet_soc_by_title(self, title: str) -> Optional[str]:
        """Find O*NET SOC code by job title"""
        if not title:
            return None
        
        doc = await self.db["skills"].find_one(
            {"title": {"$regex": title, "$options": "i"}},
            {"onet_soc": 1}
        )
        if doc:
            return doc.get("onet_soc")
        
        for collection in ["abilities", "knowledge", "work_activities"]:
            doc = await self.db[collection].find_one(
                {"title": {"$regex": title, "$options": "i"}},
                {"onet_soc": 1}
            )
            if doc:
                return doc.get("onet_soc")
        
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
            tech_skills.append({
                "name": str(doc.get("example", "")),
                "value": 85.0 if doc.get("hot_technology") else 65.0,
                "type": "tech",
                "commodity_title": str(doc.get("commodity_title", "")),
                "hot_technology": doc.get("hot_technology", False),
                "in_demand": doc.get("in_demand", False)
            })
        
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
    # COMPLETE JOB DETAIL - OPTIMIZED PARALLEL FETCHING
    # -------------------------
    
    async def get_complete_job_detail(self, occ_code: str, year: int = 2024) -> Dict[str, Any]:
        """Get complete job details - optimized with parallel fetching"""
        
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
                "soc_code": onet_soc
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
        
        # Fetch trend data in parallel (these are now optimized)
        trend_tasks = [
            self.get_job_growth_trend(occ_code),
            self.get_job_salary_trend(occ_code),
            self.get_experience_required(onet_soc),
            self.get_skill_intensity(onet_soc)
        ]
        
        # Wait for all data
        onet_results = await asyncio.gather(*tasks)
        trend_results = await asyncio.gather(*trend_tasks)
        
        skills, tech_skills, tools, abilities, knowledge, education, activities = onet_results
        growth_trend, salary_trend, experience, skill_intensity = trend_results
        
        # Categorize skills
        all_skills = skills
        tech_skills_list = tech_skills
        soft_skills_list = []
        
        soft_keywords = ["communication", "teamwork", "leadership", "problem solving", 
                        "critical thinking", "active learning", "social", "coordination",
                        "negotiation", "persuasion", "service", "management", "speaking",
                        "writing", "listening", "cooperating", "instructing", "interpersonal"]
        
        for skill in all_skills:
            skill_name = skill["name"].lower()
            if any(keyword in skill_name for keyword in soft_keywords):
                skill["type"] = "soft"
                soft_skills_list.append(skill)
            else:
                skill["type"] = "general"
        
        # Generate metrics (matches JobsRepo format)
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
                    "value": f"{growth_trend:+.1f}%",
                    "trend": {"value": abs(growth_trend), "direction": growth_direction},
                    "color": "green"
                },
                {
                    "title": "Experience Required",
                    "value": experience,
                    "color": "purple"
                },
                {
                    "title": "Skill Intensity",
                    "value": str(skill_intensity),
                    "suffix": "/10",
                    "color": "coral"
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
        
        # Update result
        result.update({
            "metrics": metrics,
            "skills": all_skills[:10],
            "tech_skills": tech_skills_list,
            "soft_skills": soft_skills_list[:6],
            "activities": activities[:6],
            "abilities": abilities[:6],
            "knowledge": knowledge[:4],
            "education": education,
            "tools": tools[:6],
            "work_activities": activities[:6]
        })
        
        return result
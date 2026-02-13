from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from collections import defaultdict

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
    """
    
    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
    
    async def get_job_by_occ_code(self, occ_code: str) -> Optional[Dict[str, Any]]:
        """Get basic job info from bls_oews collection"""
        doc = await self.db["bls_oews"].find_one(
            {"occ_code": occ_code},
            {"_id": 0, "occ_code": 1, "occ_title": 1, "year": 1, "tot_emp": 1, "a_median": 1}
        )
        return doc
    
    async def get_onet_soc(self, occ_code: str) -> Optional[str]:
        """
        Map BLS OCC code to O*NET SOC code format.
        BLS uses format: "43-0000"
        O*NET uses format: "43-0000.00"
        """
        if not occ_code:
            return None
        
        # Clean the code
        occ_code = occ_code.strip()
        
        # If it already has .00, return as is
        if ".00" in occ_code:
            return occ_code
        
        # If it's in format "43-0000", add ".00"
        if "-" in occ_code and len(occ_code) >= 6:
            return f"{occ_code}.00"
        
        # Try to find by title if code doesn't match expected format
        return None
    
    async def find_onet_soc_by_title(self, title: str) -> Optional[str]:
        """Find O*NET SOC code by job title"""
        if not title:
            return None
        
        # Try to find in skills collection first
        doc = await self.db["skills"].find_one(
            {"title": {"$regex": title, "$options": "i"}},
            {"onet_soc": 1}
        )
        if doc:
            return doc.get("onet_soc")
        
        # Try other collections
        for collection in ["abilities", "knowledge", "work_activities"]:
            doc = await self.db[collection].find_one(
                {"title": {"$regex": title, "$options": "i"}},
                {"onet_soc": 1}
            )
            if doc:
                return doc.get("onet_soc")
        
        return None
    
    # -------------------------
    # Skills (from skills collection)
    # -------------------------
    async def get_skills(self, onet_soc: str) -> List[Dict[str, Any]]:
        """Get skills from O*NET skills collection"""
        q = {"onet_soc": onet_soc}
        cursor = self.db["skills"].find(
            q,
            {"_id": 0, "element_name": 1, "data_value": 1, "scale_id": 1, "scale_name": 1}
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
    
    # -------------------------
    # Technology Skills (from technology_skills collection)
    # -------------------------
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
    
    # -------------------------
    # Tools Used (from tools_used collection)
    # -------------------------
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
    
    # -------------------------
    # Abilities (from abilities collection)
    # -------------------------
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
    
    # -------------------------
    # Knowledge (from knowledge collection)
    # -------------------------
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
    
    # -------------------------
    # Education (from education_training_experience collection)
    # -------------------------
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
    
    # -------------------------
    # Work Activities (from work_activities collection)
    # -------------------------
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
    # Complete job detail
    # -------------------------
    async def get_complete_job_detail(self, occ_code: str) -> Dict[str, Any]:
        """Get complete job details from all O*NET collections"""
        
        # Get basic job info from BLS
        basic_info = await self.get_job_by_occ_code(occ_code)
        
        # Get O*NET SOC code
        onet_soc = await self.get_onet_soc(occ_code)
        
        # If no matching SOC, try to find by title
        if not onet_soc and basic_info:
            title = basic_info.get("occ_title", "")
            onet_soc = await self.find_onet_soc_by_title(title)
            print(f"🔍 Found by title: {title} -> {onet_soc}")  # Debug log
        
        print(f"🔍 OCC Code: {occ_code} -> ONET SOC: {onet_soc}")  # Debug log
        
        # Initialize with empty data
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
        
        if not onet_soc:
            print(f"⚠️ No ONET SOC found for {occ_code}")
            return result
        
        # Fetch all data in parallel
        import asyncio
        
        print(f"📊 Fetching data for ONET SOC: {onet_soc}")
        
        skills_task = self.get_skills(onet_soc)
        tech_skills_task = self.get_technology_skills(onet_soc)
        tools_task = self.get_tools(onet_soc)
        abilities_task = self.get_abilities(onet_soc)
        knowledge_task = self.get_knowledge(onet_soc)
        education_task = self.get_education(onet_soc)
        activities_task = self.get_work_activities(onet_soc)
        
        skills, tech_skills, tools, abilities, knowledge, education, activities = await asyncio.gather(
            skills_task, tech_skills_task, tools_task, abilities_task, 
            knowledge_task, education_task, activities_task
        )
        
        print(f"✅ Skills found: {len(skills)}")
        print(f"✅ Tech skills found: {len(tech_skills)}")
        print(f"✅ Abilities found: {len(abilities)}")
        print(f"✅ Knowledge found: {len(knowledge)}")
        print(f"✅ Activities found: {len(activities)}")
        print(f"✅ Education found: {education is not None}")
        
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
        
        # Generate metrics from BLS data
        metrics = []
        if basic_info:
            metrics = [
                {
                    "title": "Total Postings",
                    "value": _to_float(basic_info.get("tot_emp", 0)),
                    "trend": {"value": 5.2, "direction": "up"},
                    "color": "cyan",
                    "format": "fmtK"
                },
                {
                    "title": "Job Trend",
                    "value": "+5.2%",
                    "trend": {"value": 2.5, "direction": "up"},
                    "color": "green"
                },
                {
                    "title": "Experience Required",
                    "value": "3-5 years",
                    "color": "purple"
                },
                {
                    "title": "Skill Intensity",
                    "value": "8.2",
                    "suffix": "/10",
                    "color": "coral"
                },
                {
                    "title": "Median Annual Salary",
                    "value": _to_float(basic_info.get("a_median", 0)),
                    "prefix": "$",
                    "trend": {"value": 5.2, "direction": "up"},
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
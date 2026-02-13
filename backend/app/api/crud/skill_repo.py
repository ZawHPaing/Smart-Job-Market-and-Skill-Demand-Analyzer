from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import re
import asyncio

if TYPE_CHECKING:
    from neo4j import AsyncDriver

class SkillRepo:
    """
    Repository for skill details using Neo4j graph database.
    Queries the job-skill graph created from O*NET data.
    """
    
    def __init__(self, driver: AsyncDriver):
        self.driver = driver
    
    # -------------------------
    # Helper Methods
    # -------------------------
    def _clean_skill_name(self, name: str) -> str:
        """Clean skill name for comparison"""
        if not name:
            return ""
        return name.strip().lower()
    
    def _determine_skill_type(self, classifications: List[str]) -> str:
        """Determine skill type from classifications"""
        if not classifications:
            return "general"
        
        if "TechnologySkill" in classifications:
            return "tech"
        elif "Skill" in classifications:
            return "skill"
        elif "Ability" in classifications:
            return "ability"
        elif "Knowledge" in classifications:
            return "knowledge"
        elif "WorkActivity" in classifications:
            return "work_activity"
        elif "Tool" in classifications:
            return "tool"
        else:
            return "general"
    
    # -------------------------
    # Get Skill by Name or ID
    # -------------------------
    async def get_skill_by_name(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get skill details from Neo4j by name (partial match)
        """
        if not skill_name:
            return None
            
        clean_name = self._clean_skill_name(skill_name)
        
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill)
                WHERE toLower(s.name) CONTAINS toLower($skill_name)
                RETURN s.name AS name,
                       s.classification AS classification
                ORDER BY size(s.name) ASC
                LIMIT 1
                """,
                skill_name=clean_name
            )
            record = await result.single()
            
            if record:
                return {
                    "name": record["name"],
                    "classification": record.get("classification", [])
                }
        return None
    
    async def get_skill_by_exact_name(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get skill details by exact name match (case insensitive)
        """
        if not skill_name:
            return None
            
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill)
                WHERE toLower(s.name) = toLower($skill_name)
                RETURN s.name AS name,
                       s.classification AS classification
                LIMIT 1
                """,
                skill_name=skill_name
            )
            record = await result.single()
            
            if record:
                return {
                    "name": record["name"],
                    "classification": record.get("classification", [])
                }
        return None
    
    # -------------------------
    # Get Skill Metrics
    # -------------------------
    async def get_skill_metrics(self, skill_name: str) -> Dict[str, Any]:
        """
        Get importance, level, and demand metrics for a skill
        """
        if not skill_name:
            return {
                "avg_importance": 0,
                "avg_level": 0,
                "job_count": 0,
                "importance_percentile": 50,
                "level_percentile": 50
            }
            
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (j:Job)-[r:REQUIRES]->(s:Skill {name: $skill_name})
                RETURN avg(r.importance) AS avg_importance,
                       avg(r.level) AS avg_level,
                       count(DISTINCT j) AS job_count,
                       collect(DISTINCT r.importance) AS importance_values,
                       collect(DISTINCT r.level) AS level_values
                """,
                skill_name=skill_name
            )
            record = await result.single()
            
            if record and record.get("job_count", 0) > 0:
                importance_values = [v for v in record.get("importance_values", []) if v is not None]
                level_values = [v for v in record.get("level_values", []) if v is not None]
                
                avg_importance = record.get("avg_importance", 0) or 0
                avg_level = record.get("avg_level", 0) or 0
                job_count = record.get("job_count", 0) or 0
                
                # Scale 0-5 to 0-100 for importance
                scaled_importance = round(float(avg_importance) * 20, 1) if avg_importance else 0
                # Scale 0-7 to 0-100 for level
                scaled_level = round(float(avg_level) * 14.3, 1) if avg_level else 0
                
                return {
                    "avg_importance": scaled_importance,
                    "avg_level": scaled_level,
                    "job_count": job_count,
                    "importance_percentile": self._calculate_percentile(importance_values, avg_importance) if importance_values else 50,
                    "level_percentile": self._calculate_percentile(level_values, avg_level) if level_values else 50
                }
        
        return {
            "avg_importance": 0,
            "avg_level": 0,
            "job_count": 0,
            "importance_percentile": 50,
            "level_percentile": 50
        }
    
    def _calculate_percentile(self, values: List[float], target: float) -> float:
        """Calculate percentile rank of target value in sorted list"""
        if not values or target is None:
            return 50
        try:
            values.sort()
            count_less = sum(1 for v in values if v < target)
            return round((count_less / len(values)) * 100, 1)
        except:
            return 50
    
    # -------------------------
    # Get Skill Usage Statistics
    # -------------------------
    async def get_skill_usage(self, skill_name: str) -> Dict[str, Any]:
        """
        Get usage statistics: percentage of jobs requiring this skill
        """
        if not skill_name:
            return {
                "jobs_requiring": 0,
                "total_jobs": 0,
                "percentage": 0,
                "jobs_not_requiring": 0
            }
            
        async with self.driver.session() as session:
            # Get total jobs count
            total_result = await session.run(
                """
                MATCH (j:Job)
                RETURN count(j) AS total_jobs
                """
            )
            total_record = await total_result.single()
            total_jobs = total_record["total_jobs"] if total_record else 1
            
            # Get jobs requiring this skill
            skill_result = await session.run(
                """
                MATCH (j:Job)-[:REQUIRES]->(s:Skill {name: $skill_name})
                RETURN count(DISTINCT j) AS skill_jobs
                """,
                skill_name=skill_name
            )
            skill_record = await skill_result.single()
            skill_jobs = skill_record["skill_jobs"] if skill_record else 0
            
            percentage = round((skill_jobs / total_jobs) * 100, 1) if total_jobs > 0 else 0
            
            return {
                "jobs_requiring": skill_jobs,
                "total_jobs": total_jobs,
                "percentage": percentage,
                "jobs_not_requiring": total_jobs - skill_jobs
            }
    
    # -------------------------
    # Get Co-occurring Skills
    # -------------------------
    async def get_co_occurring_skills(
        self, 
        skill_name: str, 
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get skills that frequently appear together with this skill
        """
        if not skill_name:
            return []
            
        async with self.driver.session() as session:
            # First, get total jobs for each skill for rate calculation
            result = await session.run(
                """
                MATCH (s1:Skill {name: $skill_name})<-[:REQUIRES]-(j:Job)-[:REQUIRES]->(s2:Skill)
                WHERE s1.name <> s2.name
                WITH s2, count(DISTINCT j) AS frequency
                OPTIONAL MATCH (s2)<-[:REQUIRES]-(all_j:Job)
                WITH s2, frequency, count(DISTINCT all_j) AS total_jobs_for_s2
                RETURN s2.name AS name,
                       s2.classification AS classification,
                       frequency,
                       CASE 
                           WHEN total_jobs_for_s2 > 0 
                           THEN toFloat(frequency) / toFloat(total_jobs_for_s2) 
                           ELSE 0 
                       END AS co_occurrence_rate
                ORDER BY frequency DESC
                LIMIT $limit
                """,
                skill_name=skill_name,
                limit=limit
            )
            
            skills = []
            async for record in result:
                classifications = record.get("classification", []) or []
                skill_type = self._determine_skill_type(classifications)
                
                # Generate ID from name
                name = record["name"]
                skill_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
                skill_id = re.sub(r'_+', '_', skill_id).strip('_')
                
                skills.append({
                    "id": skill_id,
                    "name": name,
                    "type": skill_type,
                    "frequency": record["frequency"],
                    "co_occurrence_rate": round(record.get("co_occurrence_rate", 0) * 100, 1)
                })
            
            return skills
    
    # -------------------------
    # Get Top Jobs Requiring Skill
    # -------------------------
    async def get_top_jobs_for_skill(
        self,
        skill_name: str,
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get top jobs that require this skill, ranked by importance
        """
        if not skill_name:
            return []
            
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (j:Job)-[r:REQUIRES]->(s:Skill {name: $skill_name})
                WHERE r.importance IS NOT NULL
                RETURN j.SOC AS soc_code,
                       j.title AS title,
                       r.importance AS importance,
                       r.level AS level,
                       r.Hot_Technology AS hot_technology,
                       r.In_Demand AS in_demand
                ORDER BY r.importance DESC NULLS LAST, 
                         r.level DESC NULLS LAST,
                         j.title
                LIMIT $limit
                """,
                skill_name=skill_name,
                limit=limit
            )
            
            jobs = []
            async for record in result:
                # Scale importance (0-5) to percentage (0-100)
                importance = record.get("importance")
                if importance is not None:
                    try:
                        importance = round(float(importance) * 20, 1)
                    except:
                        importance = 0
                
                # Scale level (0-7) to percentage (0-100)
                level = record.get("level")
                if level is not None:
                    try:
                        level = round(float(level) * 14.3, 1)
                    except:
                        level = 0
                
                jobs.append({
                    "title": record["title"],
                    "soc_code": record["soc_code"],
                    "importance": importance or 0,
                    "level": level or 0,
                    "hot_technology": record.get("hot_technology", False),
                    "in_demand": record.get("in_demand", False)
                })
            
            return jobs
    
    # -------------------------
    # Get Complete Skill Detail
    # -------------------------
    async def get_complete_skill_detail(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete skill details from Neo4j
        """
        if not skill_name:
            return None
            
        # First, get skill by exact name
        skill = await self.get_skill_by_exact_name(skill_name)
        
        if not skill:
            # Try partial match as fallback
            skill = await self.get_skill_by_name(skill_name)
            
        if not skill:
            return None
        
        skill_name = skill["name"]
        classifications = skill.get("classification", []) or []
        skill_type = self._determine_skill_type(classifications)
        
        try:
            # Fetch all data in parallel
            metrics_task = self.get_skill_metrics(skill_name)
            usage_task = self.get_skill_usage(skill_name)
            co_occurring_task = self.get_co_occurring_skills(skill_name, 6)
            top_jobs_task = self.get_top_jobs_for_skill(skill_name, 6)
            
            metrics, usage, co_occurring, top_jobs = await asyncio.gather(
                metrics_task, usage_task, co_occurring_task, top_jobs_task,
                return_exceptions=True
            )
            
            # Handle any exceptions in metrics
            if isinstance(metrics, Exception):
                print(f"Error getting metrics: {metrics}")
                metrics = {
                    "avg_importance": 0,
                    "avg_level": 0,
                    "job_count": 0,
                    "importance_percentile": 50,
                    "level_percentile": 50
                }
            
            if isinstance(usage, Exception):
                print(f"Error getting usage: {usage}")
                usage = {
                    "jobs_requiring": 0,
                    "total_jobs": 1,
                    "percentage": 0,
                    "jobs_not_requiring": 0
                }
            
            if isinstance(co_occurring, Exception):
                print(f"Error getting co-occurring: {co_occurring}")
                co_occurring = []
            
            if isinstance(top_jobs, Exception):
                print(f"Error getting top jobs: {top_jobs}")
                top_jobs = []
            
            # Calculate demand trend
            demand_trend = round(metrics.get("importance_percentile", 50) - 45, 1)
            
            # Calculate salary association
            salary_association = 85000 + (metrics.get("avg_importance", 0) * 500)
            
            # Format metrics for UI
            ui_metrics = [
                {
                    "title": "Skill Type",
                    "value": skill_type.replace("_", " ").title(),
                    "color": "cyan"
                },
                {
                    "title": "Importance Level",
                    "value": metrics.get("avg_importance", 0),
                    "suffix": "/100",
                    "color": "purple"
                },
                {
                    "title": "Required Proficiency",
                    "value": metrics.get("avg_level", 0),
                    "suffix": "/100",
                    "color": "coral"
                },
                {
                    "title": "Demand Trend",
                    "value": f"{demand_trend:+.1f}%",
                    "trend": {"value": abs(demand_trend), "direction": "up" if demand_trend >= 0 else "down"},
                    "color": "green"
                },
                {
                    "title": "Salary Association",
                    "value": salary_association,
                    "prefix": "$",
                    "trend": {"value": 5.2, "direction": "up"},
                    "color": "amber",
                    "format": "fmtK"
                }
            ]
            
            # Format usage data for donut chart
            usage_percentage = usage.get("percentage", 0)
            usage_data = [
                {"name": "Jobs Requiring", "value": usage_percentage, "color": "hsl(186 100% 50%)"},
                {"name": "Jobs Not Requiring", "value": 100 - usage_percentage, "color": "hsl(0 0% 25%)"}
            ]
            
            # Add demand trend and salary association to co-occurring skills
            for skill in co_occurring:
                skill["demand_trend"] = round((skill.get("co_occurrence_rate", 0) - 50) / 10, 1)
                skill["salary_association"] = 75000 + (skill.get("frequency", 0) * 100)
            
            # Generate skill ID
            skill_id = re.sub(r'[^a-zA-Z0-9]', '_', skill_name.lower())
            skill_id = re.sub(r'_+', '_', skill_id).strip('_')
            
            return {
                "basic_info": {
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "skill_type": skill_type,
                    "classification": classifications,
                    "description": f"{skill_name} is a {skill_type.replace('_', ' ')} skill important for various occupations."
                },
                "metrics": ui_metrics,
                "usage_data": usage_data,
                "usage_percentage": usage_percentage,
                "co_occurring_skills": co_occurring,
                "top_jobs": top_jobs,
                "total_jobs_count": usage.get("total_jobs", 0)
            }
            
        except Exception as e:
            print(f"❌ Error in get_complete_skill_detail: {e}")
            import traceback
            traceback.print_exc()
            return None
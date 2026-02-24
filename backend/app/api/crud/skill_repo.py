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
    # Get Tech Skill Flags
    # -------------------------
    async def get_tech_skill_flags(self, skill_name: str) -> Dict[str, bool]:
        """
        Get hot_technology and in_demand flags for technology skills
        """
        if not skill_name:
            return {"hot_technology": False, "in_demand": False}
        
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (j:Job)-[r:REQUIRES]->(s:Skill {name: $skill_name})
                WHERE r.Hot_Technology IS NOT NULL OR r.In_Demand IS NOT NULL
                RETURN COLLECT(DISTINCT r.Hot_Technology) AS hot_tech_values,
                       COLLECT(DISTINCT r.In_Demand) AS in_demand_values
                """,
                skill_name=skill_name
            )
            record = await result.single()
            
            if record:
                hot_tech_values = record.get("hot_tech_values", [])
                in_demand_values = record.get("in_demand_values", [])
                
                return {
                    "hot_technology": any(hot for hot in hot_tech_values if hot),
                    "in_demand": any(demand for demand in in_demand_values if demand)
                }
        
        return {"hot_technology": False, "in_demand": False}
    
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
    # Get Co-occurring Skills - KEEP ORIGINAL VERSION
    # -------------------------
    async def get_co_occurring_skills(
        self, 
        skill_name: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get skills that frequently appear together with this skill.
        Works for ALL skill types (tech, ability, knowledge, work_activity, etc.)
        
        Args:
            skill_name: Name of the skill
            limit: Optional maximum number of skills to return. If None, returns all.
        """
        if not skill_name:
            return []
            
        async with self.driver.session() as session:
            # First, get the total number of jobs that require the target skill
            total_jobs_result = await session.run(
                """
                MATCH (j:Job)-[:REQUIRES]->(s:Skill {name: $skill_name})
                RETURN count(DISTINCT j) AS total_target_jobs
                """,
                skill_name=skill_name
            )
            total_jobs_record = await total_jobs_result.single()
            total_target_jobs = total_jobs_record["total_target_jobs"] if total_jobs_record else 0
            
            if total_target_jobs == 0:
                return []
            
            # Use a very high limit to effectively get all skills
            # Assuming no skill has more than 1000 co-occurring skills
            query_limit = 1000
            
            # Now find co-occurring skills with proper calculations
            result = await session.run(
                """
                // Find jobs that require the target skill
                MATCH (s1:Skill {name: $skill_name})<-[:REQUIRES]-(j:Job)
                
                // Find other skills required by those same jobs
                MATCH (j)-[r2:REQUIRES]->(s2:Skill)
                WHERE s1.name <> s2.name
                
                // Aggregate by skill to avoid duplicates
                WITH s2, 
                    COLLECT(DISTINCT j) AS jobs,
                    COLLECT(r2) AS relationships,
                    COLLECT(r2.Hot_Technology) AS hot_tech_values,
                    COLLECT(r2.In_Demand) AS in_demand_values
                
                // Calculate metrics
                WITH s2, 
                    SIZE(jobs) AS co_occurrence_frequency,
                    REDUCE(s = 0.0, rel IN relationships | s + rel.importance) / SIZE(relationships) AS avg_importance,
                    REDUCE(s = 0.0, rel IN relationships | s + rel.level) / SIZE(relationships) AS avg_level,
                    // Check if any relationship has Hot_Technology or In_Demand as true
                    CASE 
                        WHEN SIZE(hot_tech_values) > 0 THEN ANY(hot IN hot_tech_values WHERE hot = true)
                        ELSE false
                    END AS hot_technology,
                    CASE 
                        WHEN SIZE(in_demand_values) > 0 THEN ANY(demand IN in_demand_values WHERE demand = true)
                        ELSE false
                    END AS in_demand
                
                // Get total jobs for each co-occurring skill (for rate calculation)
                OPTIONAL MATCH (s2)<-[:REQUIRES]-(all_j:Job)
                WITH s2, 
                    co_occurrence_frequency,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    COUNT(DISTINCT all_j) AS total_jobs_for_s2
                
                // Calculate co-occurrence rate using the target skill's job count as denominator
                WITH s2, 
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    CASE 
                        WHEN $total_target_jobs > 0 
                        THEN toFloat(co_occurrence_frequency) / toFloat($total_target_jobs) * 100
                        ELSE 0 
                    END AS co_occurrence_rate
                
                RETURN s2.name AS name,
                    s2.classification AS classification,
                    co_occurrence_frequency AS frequency,
                    total_jobs_for_s2 AS usage_count,
                    co_occurrence_rate,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand
                ORDER BY co_occurrence_rate DESC, co_occurrence_frequency DESC
                LIMIT $query_limit
                """,
                skill_name=skill_name,
                total_target_jobs=total_target_jobs,
                query_limit=query_limit
            )
            
            skills = []
            async for record in result:
                classifications = record.get("classification", []) or []
                skill_type = self._determine_skill_type(classifications)
                
                # Generate ID from name
                name = record["name"]
                skill_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
                skill_id = re.sub(r'_+', '_', skill_id).strip('_')
                
                # Scale importance (0-5) to percentage (0-100)
                avg_importance = record.get("avg_importance")
                if avg_importance is not None:
                    try:
                        avg_importance = round(float(avg_importance) * 20, 1)
                    except:
                        avg_importance = 0
                else:
                    avg_importance = 0
                
                # Scale level (0-7) to percentage (0-100)
                avg_level = record.get("avg_level")
                if avg_level is not None:
                    try:
                        avg_level = round(float(avg_level) * 14.3, 1)
                    except:
                        avg_level = 0
                else:
                    avg_level = 0
                
                # Get hot_technology and in_demand flags - ensure they're booleans
                hot_technology = record.get("hot_technology", False)
                in_demand = record.get("in_demand", False)
                
                # Ensure they're actual booleans
                if hot_technology is None:
                    hot_technology = False
                if in_demand is None:
                    in_demand = False
                
                # Ensure co_occurrence_rate is never None
                co_occurrence_rate = record.get("co_occurrence_rate")
                if co_occurrence_rate is None:
                    co_occurrence_rate = 0
                
                skills.append({
                    "id": skill_id,
                    "name": name,
                    "type": skill_type,
                    "frequency": record.get("frequency", 0),
                    "usage_count": record.get("usage_count", 0),
                    "co_occurrence_rate": round(float(co_occurrence_rate), 1),
                    "avg_importance": avg_importance,
                    "avg_level": avg_level,
                    "hot_technology": hot_technology,
                    "in_demand": in_demand,
                    "demand_trend": 0,  # KEEP original field
                    "salary_association": 0  # KEEP original field
                })
            
            # Remove any remaining duplicates just in case (by name)
            unique_skills = []
            seen_names = set()
            for skill in skills:
                if skill["name"] not in seen_names:
                    seen_names.add(skill["name"])
                    unique_skills.append(skill)
            
            # If limit is provided, apply it, otherwise return all
            if limit is not None:
                return unique_skills[:limit]
            else:
                return unique_skills
    
    # -------------------------
    # NEW: Get Co-occurring Skills with Correlation Analysis
    # -------------------------
    # -------------------------
# NEW: Get Co-occurring Skills with Correlation Analysis
# -------------------------
    # -------------------------
# Get Co-occurring Skills with Correlation Analysis - FIXED Chi-Square
# -------------------------
    async def get_co_occurring_skills_with_correlation(
        self, 
        skill_name: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get skills that frequently appear together with this skill,
        including lift and chi-square correlation analysis.
        
        Args:
            skill_name: Name of the skill
            limit: Optional maximum number of skills to return. If None, returns all.
        """
        if not skill_name:
            return []
            
        async with self.driver.session() as session:
            # First, get the total number of jobs that require the target skill
            total_jobs_result = await session.run(
                """
                MATCH (j:Job)-[:REQUIRES]->(s:Skill {name: $skill_name})
                RETURN count(DISTINCT j) AS total_target_jobs
                """,
                skill_name=skill_name
            )
            total_jobs_record = await total_jobs_result.single()
            total_target_jobs = total_jobs_record["total_target_jobs"] if total_jobs_record else 0
            
            if total_target_jobs == 0:
                return []
            
            # Also get total jobs overall
            total_all_jobs_result = await session.run(
                """
                MATCH (j:Job)
                RETURN count(j) AS total_all_jobs
                """
            )
            total_all_jobs_record = await total_all_jobs_result.single()
            total_all_jobs = total_all_jobs_record["total_all_jobs"] if total_all_jobs_record else 1
            
            # Use a very high limit to effectively get all skills
            query_limit = 1000
            
            # Now find co-occurring skills with proper calculations including lift and chi-square
            result = await session.run(
                """
                // Find jobs that require the target skill
                MATCH (s1:Skill {name: $skill_name})<-[:REQUIRES]-(j:Job)
                
                // Find other skills required by those same jobs
                MATCH (j)-[r2:REQUIRES]->(s2:Skill)
                WHERE s1.name <> s2.name
                
                // Aggregate by skill to avoid duplicates
                WITH s2, 
                    COLLECT(DISTINCT j) AS jobs,
                    COLLECT(r2) AS relationships,
                    COLLECT(r2.Hot_Technology) AS hot_tech_values,
                    COLLECT(r2.In_Demand) AS in_demand_values
                
                // Calculate metrics
                WITH s2, 
                    SIZE(jobs) AS co_occurrence_frequency,
                    REDUCE(s = 0.0, rel IN relationships | s + rel.importance) / SIZE(relationships) AS avg_importance,
                    REDUCE(s = 0.0, rel IN relationships | s + rel.level) / SIZE(relationships) AS avg_level,
                    // Check if any relationship has Hot_Technology or In_Demand as true
                    CASE 
                        WHEN SIZE(hot_tech_values) > 0 THEN ANY(hot IN hot_tech_values WHERE hot = true)
                        ELSE false
                    END AS hot_technology,
                    CASE 
                        WHEN SIZE(in_demand_values) > 0 THEN ANY(demand IN in_demand_values WHERE demand = true)
                        ELSE false
                    END AS in_demand
                
                // Get total jobs for each co-occurring skill (for rate calculation)
                OPTIONAL MATCH (s2)<-[:REQUIRES]-(all_j:Job)
                WITH s2, 
                    co_occurrence_frequency,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    COUNT(DISTINCT all_j) AS total_jobs_for_s2
                
                // Calculate co-occurrence rate using the target skill's job count as denominator
                WITH s2, 
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    CASE 
                        WHEN $total_target_jobs > 0 
                        THEN toFloat(co_occurrence_frequency) / toFloat($total_target_jobs) * 100
                        ELSE 0 
                    END AS co_occurrence_rate
                
                // Calculate LIFT: P(A&B) / (P(A) * P(B))
                // P(A) = total_target_jobs / total_all_jobs
                // P(B) = total_jobs_for_s2 / total_all_jobs
                // P(A&B) = co_occurrence_frequency / total_all_jobs
                WITH s2, 
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    co_occurrence_rate,
                    $total_target_jobs AS target_jobs,
                    $total_all_jobs AS all_jobs,
                    CASE 
                        WHEN $total_target_jobs > 0 AND total_jobs_for_s2 > 0 AND $total_all_jobs > 0
                        THEN (toFloat(co_occurrence_frequency) * toFloat($total_all_jobs)) / 
                            (toFloat($total_target_jobs) * toFloat(total_jobs_for_s2))
                        ELSE 0
                    END AS lift
                
                // Calculate CHI-SQUARE correctly using the 2x2 contingency table
                WITH s2, 
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    co_occurrence_rate,
                    lift,
                    target_jobs,
                    all_jobs,
                    // Contingency table values:
                    // a = jobs with BOTH skills (co_occurrence_frequency)
                    // b = jobs with target skill ONLY (target_jobs - co_occurrence_frequency)
                    // c = jobs with other skill ONLY (total_jobs_for_s2 - co_occurrence_frequency)
                    // d = jobs with NEITHER skill (all_jobs - target_jobs - total_jobs_for_s2 + co_occurrence_frequency)
                    co_occurrence_frequency AS a,
                    target_jobs - co_occurrence_frequency AS b,
                    total_jobs_for_s2 - co_occurrence_frequency AS c,
                    all_jobs - target_jobs - total_jobs_for_s2 + co_occurrence_frequency AS d
                
                // Calculate chi-square using formula: χ² = Σ((O-E)²/E)
                // First calculate expected frequencies under independence
                WITH s2, 
                    a, b, c, d,
                    all_jobs,
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    co_occurrence_rate,
                    lift,
                    target_jobs,
                    // Expected frequencies
                    (toFloat(target_jobs) * toFloat(total_jobs_for_s2)) / toFloat(all_jobs) AS expected_a,
                    (toFloat(target_jobs) * toFloat(all_jobs - total_jobs_for_s2)) / toFloat(all_jobs) AS expected_b,
                    (toFloat(all_jobs - target_jobs) * toFloat(total_jobs_for_s2)) / toFloat(all_jobs) AS expected_c,
                    (toFloat(all_jobs - target_jobs) * toFloat(all_jobs - total_jobs_for_s2)) / toFloat(all_jobs) AS expected_d
                
                // Calculate chi-square safely, avoiding division by zero
                WITH s2, 
                    a, b, c, d,
                    expected_a, expected_b, expected_c, expected_d,
                    all_jobs,
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    co_occurrence_rate,
                    lift,
                    target_jobs,
                    // Calculate chi-square = sum of (observed - expected)² / expected
                    CASE 
                        WHEN expected_a > 0 AND expected_b > 0 AND expected_c > 0 AND expected_d > 0
                        THEN 
                            (toFloat(a - expected_a) * toFloat(a - expected_a)) / expected_a +
                            (toFloat(b - expected_b) * toFloat(b - expected_b)) / expected_b +
                            (toFloat(c - expected_c) * toFloat(c - expected_c)) / expected_c +
                            (toFloat(d - expected_d) * toFloat(d - expected_d)) / expected_d
                        ELSE 0
                    END AS chi_square
                
                // Determine significance (p < 0.05 for chi-square > 3.84 with 1 df)
                WITH s2, 
                    co_occurrence_frequency,
                    total_jobs_for_s2,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    co_occurrence_rate,
                    lift,
                    chi_square,
                    a, b, c, d,
                    CASE 
                        WHEN chi_square > 3.84 THEN true
                        ELSE false
                    END AS is_significant,
                    // Determine correlation type based on lift
                    CASE 
                        WHEN lift > 1.5 THEN 'strong_positive'
                        WHEN lift > 1.1 THEN 'moderate_positive'
                        WHEN lift > 0.9 THEN 'neutral'
                        WHEN lift > 0.5 THEN 'moderate_negative'
                        ELSE 'strong_negative'
                    END AS correlation_type
                
                RETURN s2.name AS name,
                    s2.classification AS classification,
                    co_occurrence_frequency AS frequency,
                    total_jobs_for_s2 AS usage_count,
                    co_occurrence_rate,
                    avg_importance,
                    avg_level,
                    hot_technology,
                    in_demand,
                    lift,
                    chi_square,
                    is_significant,
                    correlation_type,
                    a, b, c, d  // Include these for debugging
                ORDER BY lift DESC, co_occurrence_frequency DESC, co_occurrence_rate DESC
                LIMIT $query_limit
                """,
                skill_name=skill_name,
                total_target_jobs=total_target_jobs,
                total_all_jobs=total_all_jobs,
                query_limit=query_limit
            )
            
            skills = []
            async for record in result:
                classifications = record.get("classification", []) or []
                skill_type = self._determine_skill_type(classifications)
                
                # Generate ID from name
                name = record["name"]
                skill_id = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
                skill_id = re.sub(r'_+', '_', skill_id).strip('_')
                
                # Scale importance (0-5) to percentage (0-100)
                avg_importance = record.get("avg_importance")
                if avg_importance is not None:
                    try:
                        avg_importance = round(float(avg_importance) * 20, 1)
                    except:
                        avg_importance = 0
                else:
                    avg_importance = 0
                
                # Scale level (0-7) to percentage (0-100)
                avg_level = record.get("avg_level")
                if avg_level is not None:
                    try:
                        avg_level = round(float(avg_level) * 14.3, 1)
                    except:
                        avg_level = 0
                else:
                    avg_level = 0
                
                # Get hot_technology and in_demand flags
                hot_technology = record.get("hot_technology", False)
                in_demand = record.get("in_demand", False)
                
                if hot_technology is None:
                    hot_technology = False
                if in_demand is None:
                    in_demand = False
                
                co_occurrence_rate = record.get("co_occurrence_rate")
                if co_occurrence_rate is None:
                    co_occurrence_rate = 0
                
                lift = record.get("lift", 0)
                if lift is None:
                    lift = 0
                chi_square = record.get("chi_square", 0)
                if chi_square is None:
                    chi_square = 0
                is_significant = record.get("is_significant", False)
                correlation_type = record.get("correlation_type", "neutral")
                
                # Debug print for small samples
                a = record.get("a", 0)
                b = record.get("b", 0)
                c = record.get("c", 0)
                d = record.get("d", 0)
                
                # If any expected cell is too small, chi-square might be unreliable
                if a + b + c + d < 20 or a < 5 or b < 5 or c < 5 or d < 5:
                    # Mark as not significant if sample too small
                    is_significant = False
                
                skills.append({
                    "id": skill_id,
                    "name": name,
                    "type": skill_type,
                    "frequency": record.get("frequency", 0),
                    "usage_count": record.get("usage_count", 0),
                    "co_occurrence_rate": round(float(co_occurrence_rate), 1),
                    "avg_importance": avg_importance,
                    "avg_level": avg_level,
                    "hot_technology": hot_technology,
                    "in_demand": in_demand,
                    "demand_trend": 0,
                    "salary_association": 0,
                    "lift": round(float(lift), 2),
                    "chi_square": round(float(chi_square), 2),
                    "is_significant": is_significant,
                    "correlation_type": correlation_type
                })
            
            # Remove duplicates
            unique_skills = []
            seen_names = set()
            for skill in skills:
                if skill["name"] not in seen_names:
                    seen_names.add(skill["name"])
                    unique_skills.append(skill)
            
            if limit is not None:
                return unique_skills[:limit]
            else:
                return unique_skills
        
    # -------------------------
    # Get Skill Correlations - NEW METHOD
    # -------------------------
    async def get_skill_correlations(
        self, 
        skill_name: str,
        min_lift: float = 1.0,
        only_significant: bool = False
    ) -> Dict[str, Any]:
        """
        Get detailed correlation analysis for a skill including lift and chi-square statistics.
        
        Args:
            skill_name: Name of the skill
            min_lift: Minimum lift value to include (default 1.0)
            only_significant: Only return statistically significant correlations
        
        Returns:
            Dictionary with correlation analysis
        """
        if not skill_name:
            return {"correlations": [], "summary": {}}
        
        # Get all co-occurring skills with lift and chi-square
        all_skills = await self.get_co_occurring_skills_with_correlation(skill_name, limit=None)
        
        # Filter based on parameters
        filtered_skills = []
        for skill in all_skills:
            lift = skill.get("lift", 0)
            is_significant = skill.get("is_significant", False)
            
            if lift >= min_lift and (not only_significant or is_significant):
                filtered_skills.append(skill)
        
        # Calculate summary statistics
        if filtered_skills:
            lifts = [s.get("lift", 0) for s in filtered_skills]
            chi_squares = [s.get("chi_square", 0) for s in filtered_skills if s.get("chi_square", 0) > 0]
            
            summary = {
                "total_correlations": len(filtered_skills),
                "avg_lift": round(sum(lifts) / len(lifts), 2) if lifts else 0,
                "max_lift": max(lifts) if lifts else 0,
                "min_lift": min(lifts) if lifts else 0,
                "significant_count": sum(1 for s in filtered_skills if s.get("is_significant", False)),
                "correlation_types": {
                    "strong_positive": sum(1 for s in filtered_skills if s.get("correlation_type") == "strong_positive"),
                    "moderate_positive": sum(1 for s in filtered_skills if s.get("correlation_type") == "moderate_positive"),
                    "neutral": sum(1 for s in filtered_skills if s.get("correlation_type") == "neutral"),
                    "moderate_negative": sum(1 for s in filtered_skills if s.get("correlation_type") == "moderate_negative"),
                    "strong_negative": sum(1 for s in filtered_skills if s.get("correlation_type") == "strong_negative")
                }
            }
        else:
            summary = {
                "total_correlations": 0,
                "avg_lift": 0,
                "max_lift": 0,
                "min_lift": 0,
                "significant_count": 0,
                "correlation_types": {}
            }
        
        # Sort by lift descending
        filtered_skills.sort(key=lambda x: x.get("lift", 0), reverse=True)
        
        return {
            "correlations": filtered_skills,
            "summary": summary
        }
    
    # -------------------------
    # Get Top Jobs Requiring Skill - UPDATED to get all jobs
    # -------------------------
    async def get_top_jobs_for_skill(
        self,
        skill_name: str,
        limit: int = 6  # This parameter is now IGNORED - we return ALL jobs
    ) -> List[Dict[str, Any]]:
        """
        Get ALL jobs that require this skill - returns jobs without sorting by importance
        so they can be sorted by employment after adding BLS data
        Works for ALL skill types
        
        Args:
            skill_name: Name of the skill
            limit: This parameter is now IGNORED - we return ALL jobs
            
        Returns:
            List of ALL jobs that require this skill
        """
        if not skill_name:
            return []
        
        # Remove the limit - get ALL jobs
        # Use a very high limit to get all jobs (assuming max jobs per skill is under 1000)
        query_limit = 1000  # Get up to 1000 jobs (should be enough for all)
            
        async with self.driver.session() as session:
            # First, check if the skill exists and has any jobs
            check_result = await session.run(
                """
                MATCH (j:Job)-[r:REQUIRES]->(s:Skill {name: $skill_name})
                RETURN count(j) as job_count
                """,
                skill_name=skill_name
            )
            check_record = await check_result.single()
            job_count = check_record["job_count"] if check_record else 0
            
            if job_count == 0:
                return []
            
            print(f"📊 Found {job_count} jobs requiring skill: {skill_name}")
            
            # Now get ALL jobs - no filtering, no sorting by importance
            result = await session.run(
                """
                MATCH (j:Job)-[r:REQUIRES]->(s:Skill {name: $skill_name})
                RETURN j.SOC AS soc_code,
                    j.title AS title,
                    COALESCE(r.importance, 0) AS importance,
                    COALESCE(r.level, 0) AS level,
                    COALESCE(r.Hot_Technology, false) AS hot_technology,
                    COALESCE(r.In_Demand, false) AS in_demand
                ORDER BY j.title  // Simple alphabetical order - we'll sort by employment after getting BLS data
                """,  # REMOVED THE LIMIT CLAUSE
                skill_name=skill_name
                # REMOVED: limit=query_limit
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
                else:
                    importance = 0
                
                # Scale level (0-7) to percentage (0-100)
                level = record.get("level")
                if level is not None:
                    try:
                        level = round(float(level) * 14.3, 1)
                    except:
                        level = 0
                else:
                    level = 0
                
                jobs.append({
                    "title": record["title"],
                    "soc_code": record["soc_code"],
                    "importance": importance,
                    "level": level,
                    "hot_technology": record.get("hot_technology", False),
                    "in_demand": record.get("in_demand", False)
                })
            
            print(f"📤 Returning {len(jobs)} jobs from Neo4j for skill: {skill_name}")
            return jobs
    
    # -------------------------
    # Get Network Graph Data
    # -------------------------
    async def get_skill_network_graph(
        self,
        skill_name: str,
        limit: int = 10,
        include_correlation: bool = False
    ) -> Dict[str, List]:
        """
        Get data formatted for undirected network graph visualization.
        Returns nodes and links for the top co-occurring skills.
        
        Args:
            skill_name: Name of the skill
            limit: Maximum number of co-occurring skills to include
            include_correlation: Whether to include correlation data (lift, significance)
        """
        if not skill_name:
            return {"nodes": [], "links": []}
        
        # Get co-occurring skills - use correlation version if requested
        if include_correlation:
            co_occurring = await self.get_co_occurring_skills_with_correlation(skill_name, limit)
        else:
            co_occurring = await self.get_co_occurring_skills(skill_name, limit)
        
        # Create nodes array
        nodes = []
        
        # Add the main skill node
        main_skill_id = re.sub(r'[^a-zA-Z0-9]', '_', skill_name.lower())
        main_skill_id = re.sub(r'_+', '_', main_skill_id).strip('_')
        
        main_node = {
            "id": main_skill_id,
            "name": skill_name,
            "group": "1",
            "value": 30,
            "usage_count": None
        }
        
        # Add correlation fields if available
        if include_correlation:
            main_node["lift"] = None
            main_node["is_significant"] = None
        
        nodes.append(main_node)
        
        # Add co-occurring skill nodes
        for i, skill in enumerate(co_occurring):
            node = {
                "id": skill["id"],
                "name": skill["name"],
                "group": "2",
                "value": 25 - (i * 1.5),
                "usage_count": skill.get("usage_count", 0),
                "co_occurrence_rate": skill.get("co_occurrence_rate", 0),
                "avg_importance": skill.get("avg_importance", 0),
                "avg_level": skill.get("avg_level", 0)
            }
            
            # Add correlation fields if available
            if include_correlation:
                node["lift"] = skill.get("lift", 0)
                node["is_significant"] = skill.get("is_significant", False)
            
            nodes.append(node)
        
        # Create undirected links
        links = []
        for skill in co_occurring:
            link = {
                "source": main_skill_id,
                "target": skill["id"],
                "value": skill.get("co_occurrence_rate", 50) / 10,
                "co_occurrence_rate": skill.get("co_occurrence_rate", 0)
            }
            
            # Add correlation fields if available
            if include_correlation:
                link["lift"] = skill.get("lift", 0)
                link["is_significant"] = skill.get("is_significant", False)
            
            links.append(link)
        
        return {
            "nodes": nodes,
            "links": links
        }
    
    # -------------------------
    # Get Complete Skill Detail - UPDATED to optionally include correlations
    # -------------------------
    async def get_complete_skill_detail(
        self, 
        skill_name: str,
        include_correlations: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete skill details from Neo4j
        
        Args:
            skill_name: Name of the skill
            include_correlations: Whether to include lift/chi-square correlation analysis
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
            tech_flags_task = self.get_tech_skill_flags(skill_name)
            
            # Get co-occurring skills - use correlation version if requested
            if include_correlations:
                co_occurring_task = self.get_co_occurring_skills_with_correlation(skill_name, limit=None)
                correlations_task = self.get_skill_correlations(skill_name, min_lift=1.0)
            else:
                co_occurring_task = self.get_co_occurring_skills(skill_name, limit=None)
                correlations_task = None
            
            network_graph_task = self.get_skill_network_graph(
                skill_name, 10, include_correlation=include_correlations
            )
            # Get ALL jobs from Neo4j
            top_jobs_task = self.get_top_jobs_for_skill(skill_name, limit=1000)
            
            # Gather tasks
            tasks = [metrics_task, usage_task, tech_flags_task, co_occurring_task, network_graph_task, top_jobs_task]
            if correlations_task:
                tasks.append(correlations_task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            metrics = results[0]
            usage = results[1]
            tech_flags = results[2]
            co_occurring = results[3]
            network_graph = results[4]
            top_jobs = results[5]
            correlations = results[6] if len(results) > 6 else None
            
            # Handle any exceptions
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
            
            if isinstance(tech_flags, Exception):
                print(f"Error getting tech flags: {tech_flags}")
                tech_flags = {"hot_technology": False, "in_demand": False}
            
            if isinstance(co_occurring, Exception):
                print(f"Error getting co-occurring: {co_occurring}")
                co_occurring = []
            
            if isinstance(network_graph, Exception):
                print(f"Error getting network graph: {network_graph}")
                network_graph = {"nodes": [], "links": []}
            
            if isinstance(top_jobs, Exception):
                print(f"Error getting top jobs: {top_jobs}")
                top_jobs = []
            
            if correlations and isinstance(correlations, Exception):
                print(f"Error getting correlations: {correlations}")
                correlations = None
            
            print(f"📊 Retrieved {len(top_jobs)} jobs from Neo4j for skill: {skill_name}")
            
            # Format metrics for UI - CONDITIONAL BASED ON SKILL TYPE
            ui_metrics = []
            
            # Base metrics all skills have
            ui_metrics.append({
                "title": "Skill Type",
                "value": skill_type.replace("_", " ").title(),
                "color": "cyan"
            })
            
            # For Technology Skills - show Hot Technology and In Demand
            if skill_type == "tech":
                ui_metrics.extend([
                    {
                        "title": "Hot Technology",
                        "value": "Yes" if tech_flags.get("hot_technology") else "No",
                        "color": "coral" if tech_flags.get("hot_technology") else "amber"
                    },
                    {
                        "title": "In Demand",
                        "value": "Yes" if tech_flags.get("in_demand") else "No",
                        "color": "green" if tech_flags.get("in_demand") else "amber"
                    }
                ])
            # For Tools - remove importance and proficiency, just show basic info
            elif skill_type == "tool":
                # Tools only get skill type, no other KPIs
                pass
            # For all other skills (ability, knowledge, work_activity, etc.) - show importance and proficiency
            else:
                ui_metrics.extend([
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
                    }
                ])
            
            # Add jobs requiring metric for all skills - BUT USE THE ACTUAL COUNT OF JOBS WE RETRIEVED
            # This will be filtered later when we add BLS data, but at least it matches what we're showing
            jobs_requiring_count = len(top_jobs)
            ui_metrics.append({
                "title": "Jobs Requiring",
                "value": jobs_requiring_count,
                "format": "fmtK",
                "color": "green"
            })
            
            # Format usage data for donut chart - UPDATE THIS TOO
            usage_percentage = round((jobs_requiring_count / usage.get("total_jobs", 1)) * 100, 1) if usage.get("total_jobs", 0) > 0 else 0
            usage_data = [
                {"name": "Jobs Requiring", "value": usage_percentage, "color": "hsl(186 100% 50%)"},
                {"name": "Jobs Not Requiring", "value": 100 - usage_percentage, "color": "hsl(0 0% 25%)"}
            ]
            
            # Generate skill ID
            skill_id = re.sub(r'[^a-zA-Z0-9]', '_', skill_name.lower())
            skill_id = re.sub(r'_+', '_', skill_id).strip('_')
            
            # Build response
            response = {
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
                "network_graph": network_graph,
                "top_jobs": top_jobs,
                "total_jobs_count": jobs_requiring_count  # Use the filtered count
            }
            
            # Add correlation analysis if requested and available
            if include_correlations and correlations:
                response["correlation_analysis"] = correlations
            
            return response
            
        except Exception as e:
            print(f"Error in get_complete_skill_detail: {e}")
            import traceback
            traceback.print_exc()
            return None
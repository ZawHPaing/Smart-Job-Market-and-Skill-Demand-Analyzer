# app/api/routes/search.py
from __future__ import annotations

from typing import Optional, TYPE_CHECKING, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db, get_neo4j_driver
from app.api.crud.jobs_repo import JobsRepo
from app.api.crud.industries_repo import IndustryRepo
from app.api.crud.skill_repo import SkillRepo
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase
    from neo4j import AsyncDriver

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def unified_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(5, ge=1, le=20, description="Results per category"),
    year: int = Query(2024, description="Year for employment data"),
    mongodb: "AgnosticDatabase" = Depends(get_db),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Unified search across jobs, industries, and skills.
    Returns results grouped by category.
    """
    cache_key = f"search_{q}_{limit}_{year}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    jobs_repo = JobsRepo(mongodb)
    industries_repo = IndustryRepo(mongodb)
    skills_repo = SkillRepo(neo4j_driver)
    
    # Search jobs
    _, jobs = await jobs_repo.list_jobs(
        year=year,
        search=q,
        limit=limit,
        offset=0,
        only_with_details=False  # Include all jobs, not just those with O*NET data
    )
    
    # Search industries - FIXED: use the correct method signature
    # Get all industries and filter manually since list_industries doesn't have search param
    year_to_use, all_industries = await industries_repo.list_industries(year=year)
    
    # Filter industries by search query
    filtered_industries = []
    if all_industries:
        q_lower = q.lower()
        for ind in all_industries:
            if q_lower in ind.get("naics_title", "").lower() or q in ind.get("naics", ""):
                filtered_industries.append(ind)
                if len(filtered_industries) >= limit:
                    break
    
    # Search skills
    async with neo4j_driver.session() as session:
        skills_result = await session.run(
            """
            MATCH (s:Skill)
            WHERE toLower(s.name) CONTAINS toLower($search_term)
            RETURN s.name AS name, 
                   s.classification AS classification,
                   COUNT { (j:Job)-[:REQUIRES]->(s) } AS job_count
            ORDER BY job_count DESC
            LIMIT $limit
            """,
            search_term=q,
            limit=limit
        )
        
        skills = []
        async for record in skills_result:
            classifications = record.get("classification", [])
            skill_type = "tech" if "TechnologySkill" in classifications else "skill"
            
            # Generate ID
            skill_id = record["name"].lower().replace(" ", "_").replace("/", "_").replace(",", "")
            
            skills.append({
                "id": skill_id,
                "name": record["name"],
                "type": skill_type,
                "job_count": record.get("job_count", 0)
            })
    
    response = {
        "jobs": jobs[:limit],
        "industries": filtered_industries[:limit],
        "skills": skills[:limit]
    }
    
    cache.set(cache_key, response, ttl=3600)  # Cache for 1 hour
    return response


@router.get("/jobs")
async def search_jobs(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    year: int = Query(2024),
    mongodb: "AgnosticDatabase" = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search only jobs"""
    cache_key = f"search_jobs_{q}_{limit}_{year}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    jobs_repo = JobsRepo(mongodb)
    _, jobs = await jobs_repo.list_jobs(
        year=year,
        search=q,
        limit=limit,
        offset=0,
        only_with_details=False
    )
    
    cache.set(cache_key, jobs, ttl=3600)
    return jobs


@router.get("/industries")
async def search_industries(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    year: int = Query(2024),
    mongodb: "AgnosticDatabase" = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search only industries by filtering after fetching"""
    cache_key = f"search_industries_{q}_{limit}_{year}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    industries_repo = IndustryRepo(mongodb)
    year_to_use, all_industries = await industries_repo.list_industries(year=year)
    
    # Filter industries by search query
    filtered_industries = []
    if all_industries:
        q_lower = q.lower()
        for ind in all_industries:
            if q_lower in ind.get("naics_title", "").lower() or q in ind.get("naics", ""):
                filtered_industries.append(ind)
                if len(filtered_industries) >= limit:
                    break
    
    cache.set(cache_key, filtered_industries, ttl=3600)
    return filtered_industries


@router.get("/skills")
async def search_skills(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
) -> List[Dict[str, Any]]:
    """Search only skills"""
    cache_key = f"search_skills_{q}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (s:Skill)
            WHERE toLower(s.name) CONTAINS toLower($search_term)
            RETURN s.name AS name, 
                   s.classification AS classification,
                   COUNT { (j:Job)-[:REQUIRES]->(s) } AS job_count
            ORDER BY job_count DESC
            LIMIT $limit
            """,
            search_term=q,
            limit=limit
        )
        
        skills = []
        async for record in result:
            classifications = record.get("classification", [])
            skill_type = "tech" if "TechnologySkill" in classifications else "skill"
            
            skill_id = record["name"].lower().replace(" ", "_").replace("/", "_").replace(",", "")
            
            skills.append({
                "id": skill_id,
                "name": record["name"],
                "type": skill_type,
                "job_count": record.get("job_count", 0)
            })
    
    cache.set(cache_key, skills, ttl=3600)
    return skills
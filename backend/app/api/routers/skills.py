from __future__ import annotations

from typing import Optional, TYPE_CHECKING, List, Any, Dict

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.database.neo4j import get_neo4j_driver
from app.api.crud.skill_repo import SkillRepo
from app.models.skill_models import SkillDetailResponse
from app.api.crud.job_detail_repo import JobDetailRepo
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase
    from neo4j import AsyncDriver

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/search")
async def search_skills(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
) -> List[dict]:
    """Search for skills by name - don't cache search results"""
    repo = SkillRepo(neo4j_driver)
    
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
            skills.append({
                "id": record["name"].lower().replace(" ", "_").replace("/", "_").replace(",", ""),
                "name": record["name"],
                "type": "tech" if "TechnologySkill" in record.get("classification", []) else "skill",
                "job_count": record.get("job_count", 0)
            })
        
        return skills


@router.get("/{skill_id}", response_model=SkillDetailResponse)
async def get_skill_detail(
    skill_id: str,
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
    mongodb: "AgnosticDatabase" = Depends(get_db),
) -> SkillDetailResponse:
    """Get complete skill details from Neo4j"""
    # Check cache
    cache_key = f"skill_detail_{skill_id}"
    cached = cache.get(cache_key)
    if cached:
        return SkillDetailResponse(**cached)
    
    repo = SkillRepo(neo4j_driver)
    job_detail_repo = JobDetailRepo(mongodb)
    
    # Convert skill_id back to name (handle both formats)
    # First, try to clean the ID
    skill_name = skill_id.replace("_", " ").replace("-", " ").strip()
    
    # If it's all lowercase, capitalize properly
    if skill_name.islower():
        skill_name = skill_name.title()
    
    print(f"🔍 Looking for skill: '{skill_name}' (from ID: {skill_id})")
    
    # Try to find the skill
    skill_detail = await repo.get_complete_skill_detail(skill_name)
    
    # If not found, try searching with original format
    if not skill_detail:
        print(f"⚠️ Skill not found with name '{skill_name}', trying to find by partial match...")
        skill = await repo.get_skill_by_name(skill_name)
        if skill:
            print(f"✅ Found skill by partial match: {skill['name']}")
            skill_detail = await repo.get_complete_skill_detail(skill["name"])
    
    # If still not found, try exact match with case-insensitive
    if not skill_detail:
        print(f"⚠️ Still not found, trying case-insensitive search...")
        async with neo4j_driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill)
                WHERE toLower(s.name) = toLower($skill_name)
                RETURN s.name AS name
                LIMIT 1
                """,
                skill_name=skill_name
            )
            record = await result.single()
            if record:
                exact_name = record["name"]
                print(f"✅ Found skill with exact match: {exact_name}")
                skill_detail = await repo.get_complete_skill_detail(exact_name)
    
    if not skill_detail:
        print(f"❌ Skill not found: {skill_name}")
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}. Please try searching from the Jobs page."
        )
    
    # Enhance top jobs with BLS salary data
    enhanced_jobs = []
    for job in skill_detail.get("top_jobs", []):
        soc_code = job.get("soc_code")
        if soc_code:
            # Get BLS data for this occupation
            bls_data = await job_detail_repo.get_job_by_occ_code(soc_code.replace(".00", ""))
            if bls_data:
                job["median_salary"] = bls_data.get("a_median")
                job["employment"] = bls_data.get("tot_emp")
            else:
                # Add placeholder data if BLS data not found
                job["median_salary"] = 75000
                job["employment"] = 10000
        enhanced_jobs.append(job)
    
    skill_detail["top_jobs"] = enhanced_jobs
    
    response = SkillDetailResponse(**skill_detail)
    cache.set(cache_key, response.dict())
    return response


@router.get("/{skill_id}/jobs")
async def get_skill_jobs(
    skill_id: str,
    limit: int = Query(10, ge=1, le=50),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
    mongodb: "AgnosticDatabase" = Depends(get_db),
) -> List[dict]:
    """Get top jobs for a specific skill"""
    cache_key = f"skill_jobs_{skill_id}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = SkillRepo(neo4j_driver)
    job_detail_repo = JobDetailRepo(mongodb)
    
    skill_name = skill_id.replace("_", " ").replace("-", " ").title()
    
    jobs = await repo.get_top_jobs_for_skill(skill_name, limit)
    
    # Enhance with BLS data
    enhanced_jobs = []
    for job in jobs:
        soc_code = job.get("soc_code")
        if soc_code:
            bls_data = await job_detail_repo.get_job_by_occ_code(soc_code.replace(".00", ""))
            if bls_data:
                job["median_salary"] = bls_data.get("a_median")
                job["employment"] = bls_data.get("tot_emp")
        enhanced_jobs.append(job)
    
    cache.set(cache_key, enhanced_jobs)
    return enhanced_jobs


@router.get("/{skill_id}/co-occurring")
async def get_co_occurring_skills(
    skill_id: str,
    limit: int = Query(6, ge=1, le=20),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
) -> List[dict]:
    """Get co-occurring skills for a specific skill"""
    cache_key = f"skill_cooccurring_{skill_id}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = SkillRepo(neo4j_driver)
    skill_name = skill_id.replace("_", " ").replace("-", " ").title()
    
    skills = await repo.get_co_occurring_skills(skill_name, limit)
    
    cache.set(cache_key, skills)
    return skills


@router.get("/{skill_id}/metrics")
async def get_skill_metrics(
    skill_id: str,
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
) -> dict:
    """Get metrics for a specific skill"""
    cache_key = f"skill_metrics_{skill_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = SkillRepo(neo4j_driver)
    skill_name = skill_id.replace("_", " ").replace("-", " ").title()
    
    metrics = await repo.get_skill_metrics(skill_name)
    
    cache.set(cache_key, metrics)
    return metrics
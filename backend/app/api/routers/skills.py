from __future__ import annotations

from typing import Optional, TYPE_CHECKING, List, Any, Dict

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db, get_neo4j_driver
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
    year: int = Query(..., description="Year for salary data (2011-2024)"),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
    mongodb: "AgnosticDatabase" = Depends(get_db),
) -> SkillDetailResponse:
    """Get complete skill details from Neo4j with year-specific salary data.
    Jobs are sorted by total employment (number of people in that occupation)
    for the selected year, highest first."""
    
    # Check cache with year
    cache_key = f"skill_detail_{skill_id}_{year}"
    cached = cache.get(cache_key)
    if cached:
        return SkillDetailResponse(**cached)
    
    repo = SkillRepo(neo4j_driver)
    job_detail_repo = JobDetailRepo(mongodb)
    
    # Convert skill_id back to name (handle both formats)
    skill_name = skill_id.replace("_", " ").replace("-", " ").strip()
    
    # If it's all lowercase, capitalize properly
    if skill_name.islower():
        skill_name = skill_name.title()
    
    print(f"🔍 Looking for skill: '{skill_name}' (from ID: {skill_id}) with year: {year}")
    
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
    
    # Get ALL jobs that require this skill from Neo4j
    jobs_from_neo4j = skill_detail.get("top_jobs", [])
    print(f"📊 Received {len(jobs_from_neo4j)} jobs from Neo4j for {skill_name}")
    
    # Enhance each job with BLS employment and salary data for the selected year
    enhanced_jobs = []
    jobs_without_data = 0
    
    for job in jobs_from_neo4j:
        soc_code = job.get("soc_code")
        if soc_code:
            # Get BLS data for this occupation for the specific year
            bls_data = await job_detail_repo.get_job_by_occ_code(soc_code.replace(".00", ""), year)
            if bls_data:
                # Get employment (tot_emp) - this is the actual number of people employed in this occupation
                employment = bls_data.get("tot_emp")
                # Only include jobs that have employment data and it's > 0
                if employment and employment > 0:
                    job_with_bls = job.copy()
                    job_with_bls["median_salary"] = bls_data.get("a_median")
                    job_with_bls["employment"] = employment
                    enhanced_jobs.append(job_with_bls)
                else:
                    jobs_without_data += 1
            else:
                jobs_without_data += 1
        else:
            jobs_without_data += 1
    
    print(f"📊 After BLS enhancement: {len(enhanced_jobs)} jobs with employment data, {jobs_without_data} jobs skipped")
    
    # SORT BY EMPLOYMENT (number of people in the occupation) - HIGHEST FIRST
    enhanced_jobs.sort(key=lambda x: x.get("employment", 0) or 0, reverse=True)
    
    # Log the top jobs and their employment numbers for debugging
    print(f"📊 Top jobs for {skill_name} sorted by employment (year {year}):")
    for i, job in enumerate(enhanced_jobs[:10]):  # Show top 10
        print(f"  {i+1}. {job['title']}: {job.get('employment', 0):,} employed, ${job.get('median_salary', 0):,} median salary")
    
    # Update the skill detail with ALL enhanced and sorted jobs
    skill_detail["top_jobs"] = enhanced_jobs  # Store ALL jobs
    skill_detail["year"] = year  # Add year to response
    
    # Update the KPI to match the number of jobs we're actually displaying
    # Find the "Jobs Requiring" metric and update its value
    for metric in skill_detail["metrics"]:
        if metric["title"] == "Jobs Requiring":
            metric["value"] = len(enhanced_jobs)
            break
    
    # Update the total_jobs_count to match
    skill_detail["total_jobs_count"] = len(enhanced_jobs)
    
    response = SkillDetailResponse(**skill_detail)
    cache.set(cache_key, response.dict())
    return response


@router.get("/{skill_id}/jobs")
async def get_skill_jobs(
    skill_id: str,
    year: int = Query(..., description="Year for salary data (2011-2024)"),
    limit: int = Query(10, ge=1, le=50),
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
    mongodb: "AgnosticDatabase" = Depends(get_db),
) -> List[dict]:
    """Get top jobs for a specific skill with year-specific salary data.
    Jobs are sorted by total employment (number of people in that occupation)
    for the selected year, highest first."""
    cache_key = f"skill_jobs_{skill_id}_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = SkillRepo(neo4j_driver)
    job_detail_repo = JobDetailRepo(mongodb)
    
    skill_name = skill_id.replace("_", " ").replace("-", " ").title()
    
    # Get ALL jobs from Neo4j (the method now returns all jobs regardless of limit param)
    jobs = await repo.get_top_jobs_for_skill(skill_name, limit=limit)  # limit param is ignored in the method
    print(f"📊 Received {len(jobs)} jobs from Neo4j for {skill_name} in /jobs endpoint")
    
    # Enhance with BLS data for the selected year
    enhanced_jobs = []
    for job in jobs:
        soc_code = job.get("soc_code")
        if soc_code:
            bls_data = await job_detail_repo.get_job_by_occ_code(soc_code.replace(".00", ""), year)
            if bls_data:
                employment = bls_data.get("tot_emp")
                if employment and employment > 0:
                    job_with_bls = job.copy()
                    job_with_bls["median_salary"] = bls_data.get("a_median")
                    job_with_bls["employment"] = employment
                    enhanced_jobs.append(job_with_bls)
    
    # Sort by employment (number of people employed) - highest first
    enhanced_jobs.sort(key=lambda x: x.get("employment", 0) or 0, reverse=True)
    
    # Log top jobs for debugging
    print(f"📊 Sorted jobs for {skill_name}: got {len(enhanced_jobs)} jobs with employment data")
    for i, job in enumerate(enhanced_jobs[:5]):
        print(f"  {i+1}. {job['title']}: {job.get('employment', 0):,} employed")
    
    # Apply the requested limit AFTER sorting
    result = enhanced_jobs[:limit]
    print(f"📤 Returning {len(result)} jobs (limited to {limit})")
    
    cache.set(cache_key, result)
    return result


@router.get("/{skill_id}/co-occurring")
async def get_co_occurring_skills(
    skill_id: str,
    limit: int = Query(None, ge=1, le=1000),  # Optional limit, can get all
    neo4j_driver: AsyncDriver = Depends(get_neo4j_driver),
) -> List[dict]:
    """Get co-occurring skills for a specific skill.
    If no limit provided, returns all co-occurring skills."""
    cache_key = f"skill_cooccurring_{skill_id}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = SkillRepo(neo4j_driver)
    skill_name = skill_id.replace("_", " ").replace("-", " ").title()
    
    # Pass limit=None to get all skills
    skills = await repo.get_co_occurring_skills(skill_name, limit=limit)
    
    # Log the breakdown by type for debugging
    if skills:
        type_counts: Dict[str, int] = {}
        for skill in skills:
            skill_type = skill.get("type", "unknown")
            type_counts[skill_type] = type_counts.get(skill_type, 0) + 1
        
        print(f"📊 Co-occurring skills for {skill_name} - breakdown by type:")
        for skill_type, count in type_counts.items():
            print(f"  - {skill_type}: {count}")
    
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
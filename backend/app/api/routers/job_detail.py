from __future__ import annotations

from typing import Optional, TYPE_CHECKING, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.api.crud.job_detail_repo import JobDetailRepo
from app.models.job_detail_models import JobDetailResponse
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/job-detail", tags=["job-detail"])


@router.get("/{occ_code}", response_model=JobDetailResponse)
async def get_job_detail(
    occ_code: str,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobDetailResponse:
    """Get complete job details from O*NET collections"""
    # URL decode if needed
    occ_code = occ_code.strip()
    
    # Check cache
    cache_key = f"job_detail_{occ_code}"
    cached = cache.get(cache_key)
    if cached:
        return JobDetailResponse(**cached)
    
    repo = JobDetailRepo(db)
    
    data = await repo.get_complete_job_detail(occ_code)
    
    if not data.get("basic_info", {}).get("occ_title"):
        raise HTTPException(
            status_code=404, 
            detail=f"Job not found for occ_code={occ_code}"
        )
    
    response = JobDetailResponse(**data)
    cache.set(cache_key, response.dict())
    return response


@router.get("/{occ_code}/skills", response_model=List[Dict[str, Any]])
async def get_job_skills(
    occ_code: str,
    limit: int = Query(20, ge=1, le=100),
    db: "AgnosticDatabase" = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get skills for a specific job"""
    cache_key = f"job_skills_{occ_code}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = JobDetailRepo(db)
    onet_soc = await repo.get_onet_soc(occ_code)
    
    if not onet_soc:
        return []
    
    skills = await repo.get_skills(onet_soc)
    result = skills[:limit]
    
    cache.set(cache_key, result)
    return result


@router.get("/{occ_code}/technology-skills", response_model=List[Dict[str, Any]])
async def get_job_technology_skills(
    occ_code: str,
    db: "AgnosticDatabase" = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get technology skills for a specific job"""
    cache_key = f"job_tech_skills_{occ_code}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = JobDetailRepo(db)
    onet_soc = await repo.get_onet_soc(occ_code)
    
    if not onet_soc:
        return []
    
    result = await repo.get_technology_skills(onet_soc)
    cache.set(cache_key, result)
    return result


@router.get("/{occ_code}/abilities", response_model=List[Dict[str, Any]])
async def get_job_abilities(
    occ_code: str,
    limit: int = Query(10, ge=1, le=50),
    db: "AgnosticDatabase" = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get abilities for a specific job"""
    cache_key = f"job_abilities_{occ_code}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = JobDetailRepo(db)
    onet_soc = await repo.get_onet_soc(occ_code)
    
    if not onet_soc:
        return []
    
    abilities = await repo.get_abilities(onet_soc)
    result = abilities[:limit]
    
    cache.set(cache_key, result)
    return result


@router.get("/{occ_code}/knowledge", response_model=List[Dict[str, Any]])
async def get_job_knowledge(
    occ_code: str,
    limit: int = Query(10, ge=1, le=50),
    db: "AgnosticDatabase" = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get knowledge areas for a specific job"""
    cache_key = f"job_knowledge_{occ_code}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = JobDetailRepo(db)
    onet_soc = await repo.get_onet_soc(occ_code)
    
    if not onet_soc:
        return []
    
    knowledge = await repo.get_knowledge(onet_soc)
    result = knowledge[:limit]
    
    cache.set(cache_key, result)
    return result
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.api.crud.forecast_repo import ForecastRepo
from app.models.forecast_models import ForecastResponse
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/", response_model=ForecastResponse)
async def get_forecast(
    year: int = Query(2025, description="Forecast year (2025-2028)"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> ForecastResponse:
    """Get complete forecast dashboard for specified year"""
    
    if year < 2025 or year > 2028:
        raise HTTPException(
            status_code=400,
            detail="Forecast year must be between 2025 and 2028"
        )
    
    # Check cache
    cache_key = f"forecast_complete_{year}"
    cached = cache.get(cache_key)
    if cached:
        return ForecastResponse(**cached)
    
    repo = ForecastRepo(db)
    forecast_data = await repo.get_complete_forecast(year)
    
    response = ForecastResponse(**forecast_data)
    cache.set(cache_key, response.dict())
    
    return response


@router.get("/industries")
async def forecast_industries(
    limit: int = Query(6, ge=1, le=20),
    forecast_years: int = Query(4, ge=1, le=5),
    db: "AgnosticDatabase" = Depends(get_db),
):
    """Get forecasts for top industries"""
    cache_key = f"forecast_industries_{limit}_{forecast_years}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = ForecastRepo(db)
    forecasts = await repo.forecast_top_industries(limit, forecast_years)
    
    cache.set(cache_key, forecasts)
    return forecasts


@router.get("/jobs")
async def forecast_jobs(
    limit: int = Query(8, ge=1, le=20),
    forecast_years: int = Query(4, ge=1, le=5),
    db: "AgnosticDatabase" = Depends(get_db),
):
    """Get forecasts for top jobs"""
    cache_key = f"forecast_jobs_{limit}_{forecast_years}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = ForecastRepo(db)
    forecasts = await repo.forecast_top_jobs(limit, forecast_years)
    
    cache.set(cache_key, forecasts)
    return forecasts


@router.get("/industry/{naics}")
async def forecast_single_industry(
    naics: str,
    industry_title: Optional[str] = None,
    forecast_years: int = Query(4, ge=1, le=5),
    db: "AgnosticDatabase" = Depends(get_db),
):
    """Get forecast for a specific industry"""
    cache_key = f"forecast_industry_{naics}_{forecast_years}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = ForecastRepo(db)
    
    if not industry_title:
        # Get title from industries repo
        from app.api.crud.industries_repo import IndustryRepo
        ind_repo = IndustryRepo(db)
        industry_title = await ind_repo.get_naics_title(naics, 2024)
    
    forecast = await repo.forecast_industry(naics, industry_title, forecast_years)
    
    cache.set(cache_key, forecast)
    return forecast


@router.get("/job/{occ_code}")
async def forecast_single_job(
    occ_code: str,
    job_title: Optional[str] = None,
    forecast_years: int = Query(4, ge=1, le=5),
    db: "AgnosticDatabase" = Depends(get_db),
):
    """Get forecast for a specific job"""
    cache_key = f"forecast_job_{occ_code}_{forecast_years}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    repo = ForecastRepo(db)
    
    if not job_title:
        # Get title from jobs repo
        from app.api.crud.jobs_repo import JobsRepo
        job_repo = JobsRepo(db)
        job_title = await job_repo.get_job_title(occ_code, 2024)
    
    forecast = await repo.forecast_job(occ_code, job_title, forecast_years)
    
    cache.set(cache_key, forecast)
    return forecast
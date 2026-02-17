from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Literal

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.api.crud.industries_repo import IndustryRepo
from app.models.industry_models import (
    IndustryCard,
    IndustryListResponse,
    IndustryItem,
    IndustryDashboardMetrics,
    IndustryTopJobsResponse,
    IndustryTopJobResponse,
    IndustryJobsResponse,
    IndustryDetailMetrics,
    IndustrySummaryResponse,
    IndustryTopResponse,
    IndustryYearPoint,
    JobDetail,
    TopGrowingIndustry,
    IndustryTopTrendsResponse,
    IndustryTrendSeries,
    IndustryCompositionResponse,
    IndustryTrendPoint,
    IndustryCompositionRow,
    IndustryTopOccCompositionResponse,
)
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/industries", tags=["industries"])


@router.get("/", response_model=IndustryListResponse)
async def list_industries(
    year: Optional[int] = Query(None, description="If omitted, uses latest year in bls_oews"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryListResponse:
    cache_key = f"industries_list_{year}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryListResponse(**cached)
    
    repo = IndustryRepo(db)
    y, industries = await repo.list_industries(year)

    if not industries:
        raise HTTPException(status_code=404, detail="No industries found")

    response = IndustryListResponse(
        year=y,
        count=len(industries),
        industries=[IndustryItem(**i) for i in industries],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/metrics/{year}", response_model=IndustryDashboardMetrics)
async def dashboard_metrics(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryDashboardMetrics:
    cache_key = f"industry_metrics_{year}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryDashboardMetrics(**cached)
    
    repo = IndustryRepo(db)
    data = await repo.dashboard_metrics(year)

    top = data.get("top_growing_industry")
    top_obj = TopGrowingIndustry(**top) if top else None

    response = IndustryDashboardMetrics(
        year=data["year"],
        total_industries=data["total_industries"],
        total_employment=data["total_employment"],
        avg_industry_growth_pct=data["avg_industry_growth_pct"],
        top_growing_industry=top_obj,
        median_industry_salary=data["median_industry_salary"],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top", response_model=IndustryTopResponse)
async def top_industries(
    year: int = Query(...),
    limit: int = Query(6, ge=1, le=1000),
    by: str = Query("employment", pattern="^(employment|salary)$"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryTopResponse:
    cache_key = f"industries_top_{year}_{limit}_{by}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryTopResponse(**cached)
    
    repo = IndustryRepo(db)

    if by == "salary":
        rows = await repo.top_industries(year=year, limit=limit, by="salary")
        response = IndustryTopResponse(year=year, by=by, limit=limit, industries=[IndustryCard(**r) for r in rows])
    else:
        rows = await repo.top_industries_with_growth(year=year, limit=limit)
        response = IndustryTopResponse(year=year, by=by, limit=limit, industries=[IndustryCard(**r) for r in rows])
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top-trends", response_model=IndustryTopTrendsResponse)
async def top_industries_trends(
    year_from: int = Query(2019),
    year_to: int = Query(2024),
    limit: int = Query(10, ge=1, le=20),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryTopTrendsResponse:
    cache_key = f"industries_trends_{year_from}_{year_to}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryTopTrendsResponse(**cached)
    
    repo = IndustryRepo(db)
    series = await repo.top_industries_trends(year_from=year_from, year_to=year_to, limit=limit)

    response = IndustryTopTrendsResponse(
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        limit=limit,
        series=[
            IndustryTrendSeries(
                naics=s["naics"],
                naics_title=s["naics_title"],
                points=[IndustryTrendPoint(**p) for p in s["points"]],
            )
            for s in series
        ],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/composition", response_model=IndustryCompositionResponse)
async def industry_composition(
    year: int = Query(...),
    limit: int = Query(6, ge=1, le=20),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryCompositionResponse:
    cache_key = f"industries_composition_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryCompositionResponse(**cached)
    
    repo = IndustryRepo(db)
    rows = await repo.composition_by_industry(year=year, limit=limit)

    response = IndustryCompositionResponse(
        year=year,
        limit=limit,
        rows=[IndustryCompositionRow(**r) for r in rows],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/composition-top-occupations", response_model=IndustryTopOccCompositionResponse)
async def composition_top_occupations(
    year: int = Query(...),
    industries_limit: int = Query(6, ge=1, le=50),
    top_n_occ: int = Query(3, ge=1, le=10),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryTopOccCompositionResponse:
    cache_key = f"industries_top_occ_{year}_{industries_limit}_{top_n_occ}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryTopOccCompositionResponse(**cached)
    
    repo = IndustryRepo(db)

    data = await repo.top_occupations_composition(
        year=year,
        industries_limit=industries_limit,
        top_n_occ=top_n_occ,
    )

    response = IndustryTopOccCompositionResponse(
        year=year,
        industries_limit=industries_limit,
        top_n_occ=top_n_occ,
        rows=data.get("rows", []),
        legend=data.get("legend", []),
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/{naics}/top-jobs", response_model=IndustryTopJobsResponse)
async def top_jobs(
    naics: str,
    year: int = Query(...),
    limit: int = Query(6, ge=1, le=2000),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryTopJobsResponse:
    cache_key = f"industries_{naics}_top_jobs_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryTopJobsResponse(**cached)
    
    repo = IndustryRepo(db)
    naics_title, rows = await repo.top_jobs_in_industry(naics, year, limit)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No jobs found for naics={naics} in {year}")

    response = IndustryTopJobsResponse(
        naics=naics,
        naics_title=naics_title,
        year=year,
        limit=limit,
        jobs=[JobDetail(**r) for r in rows],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/{naics}/top-job", response_model=IndustryTopJobResponse)
async def top_job(
    naics: str,
    year: int = Query(...),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryTopJobResponse:
    cache_key = f"industries_{naics}_top_job_{year}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryTopJobResponse(**cached)
    
    repo = IndustryRepo(db)
    naics_title, row = await repo.top_job_in_industry(naics, year)

    job = JobDetail(**row) if row else None

    response = IndustryTopJobResponse(
        naics=naics,
        naics_title=naics_title,
        year=year,
        job=job,
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/{naics}/jobs", response_model=IndustryJobsResponse)
async def jobs(
    naics: str,
    year: int = Query(...),
    limit: int = Query(200, ge=1, le=5000),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryJobsResponse:
    cache_key = f"industries_{naics}_jobs_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryJobsResponse(**cached)
    
    repo = IndustryRepo(db)
    rows = await repo.jobs_in_industry(naics, year)
    naics_title = rows[0]["naics_title"] if rows else await repo.get_naics_title(naics, year)

    rows = rows[:limit]

    response = IndustryJobsResponse(
        naics=naics,
        naics_title=naics_title,
        year=year,
        count=len(rows),
        jobs=[JobDetail(**r) for r in rows],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/{naics}/metrics", response_model=IndustryDetailMetrics)
async def industry_metrics(
    naics: str,
    year: int = Query(...),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryDetailMetrics:
    cache_key = f"industries_{naics}_metrics_{year}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryDetailMetrics(**cached)
    
    repo = IndustryRepo(db)
    naics_title, total_emp, med_sal = await repo.industry_metrics(naics, year)

    if total_emp == 0:
        raise HTTPException(status_code=404, detail=f"No data for naics={naics} in {year}")

    response = IndustryDetailMetrics(
        naics=naics,
        naics_title=naics_title,
        year=year,
        total_employment=total_emp,
        median_salary=med_sal,
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/{naics}/summary", response_model=IndustrySummaryResponse)
async def industry_summary(
    naics: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustrySummaryResponse:
    cache_key = f"industries_{naics}_summary_{year_from}_{year_to}"
    cached = cache.get(cache_key)
    if cached:
        return IndustrySummaryResponse(**cached)
    
    repo = IndustryRepo(db)
    naics_title, series = await repo.industry_summary(naics, year_from, year_to)

    response = IndustrySummaryResponse(
        naics=naics,
        naics_title=naics_title,
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        series=[IndustryYearPoint(**p) for p in series],
    )
    
    cache.set(cache_key, response.dict())
    return response
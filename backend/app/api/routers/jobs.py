from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Literal, List

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.api.crud.jobs_repo import JobsRepo
from app.models.job_models import (
    JobListResponse,
    JobItem,
    JobDetailMetrics,
    JobSummaryResponse,
    JobDashboardMetrics,
    JobTopResponse,
    JobCard,
    JobTopTrendsResponse,
    JobTopSalaryTrendsResponse,
    JobTrendSeries,
    JobSalaryTrendSeries,
    JobTopCombinedResponse,
    JobGroupsResponse,
    JobGroupItem,
    JobCompositionResponse,
    JobCompositionRow,
    JobSalaryDistribution,
    JobIndustryJobsResponse,
    JobIndustryJob,
    TopGrowingJob,
    JobYearPoint,
)
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    year: Optional[int] = Query(None, description="If omitted, uses latest year"),
    group: Optional[str] = Query(None, description="Filter by SOC group"),
    search: Optional[str] = Query(None, description="Search by job title"),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    only_with_details: bool = Query(True, description="Only show jobs with O*NET data"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobListResponse:
    """List all jobs/occupations - only those with O*NET data by default"""
    cache_key = f"jobs_list_{year}_{group}_{search}_{limit}_{offset}_{only_with_details}"
    cached = cache.get(cache_key)
    if cached:
        return JobListResponse(**cached)
    
    repo = JobsRepo(db)
    y, jobs = await repo.list_jobs(
        year=year, 
        group=group, 
        search=search,
        limit=limit, 
        offset=offset,
        only_with_details=only_with_details
    )
    
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found")
    
    response = JobListResponse(
        year=y,
        count=len(jobs),
        jobs=[JobItem(**j) for j in jobs]
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/search", response_model=List[JobItem])
async def search_jobs(
    q: str = Query(..., min_length=2, description="Search query"),
    year: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: "AgnosticDatabase" = Depends(get_db),
) -> List[JobItem]:
    """Quick search for job autocomplete - don't cache search results"""
    repo = JobsRepo(db)
    jobs = await repo.search_jobs(query=q, year=year, limit=limit)
    return [JobItem(**j) for j in jobs]


@router.get("/metrics/{year}", response_model=JobDashboardMetrics)
async def dashboard_metrics(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobDashboardMetrics:
    """Dashboard metrics for jobs overview"""
    cache_key = f"jobs_metrics_{year}"
    cached = cache.get(cache_key)
    if cached:
        return JobDashboardMetrics(**cached)
    
    repo = JobsRepo(db)
    data = await repo.dashboard_metrics(year)
    
    top = data.get("top_growing_job")
    top_obj = TopGrowingJob(**top) if top else None
    
    response = JobDashboardMetrics(
        year=data["year"],
        total_jobs=data["total_jobs"],
        total_employment=data["total_employment"],
        avg_job_growth_pct=data["avg_job_growth_pct"],
        top_growing_job=top_obj,
        a_median=data["a_median"],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/groups/{year}", response_model=JobGroupsResponse)
async def job_groups(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobGroupsResponse:
    """Get distinct occupation groups (SOC major groups)"""
    cache_key = f"jobs_groups_{year}"
    cached = cache.get(cache_key)
    if cached:
        return JobGroupsResponse(**cached)
    
    repo = JobsRepo(db)
    groups = await repo.job_groups(year)
    
    response = JobGroupsResponse(
        year=year,
        groups=[JobGroupItem(**g) for g in groups]
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top", response_model=JobTopResponse)
async def top_jobs(
    year: int = Query(...),
    limit: int = Query(10, ge=1, le=50),
    by: Literal["employment", "salary"] = Query("employment"),
    group: Optional[str] = Query(None, description="Filter by SOC group"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobTopResponse:
    """Top jobs by employment or salary"""
    cache_key = f"jobs_top_{year}_{limit}_{by}_{group}"
    cached = cache.get(cache_key)
    if cached:
        return JobTopResponse(**cached)
    
    repo = JobsRepo(db)
    
    if by == "salary":
        rows = await repo.top_jobs(year=year, limit=limit, by="salary", group=group)
        response = JobTopResponse(
            year=year, 
            by=by, 
            limit=limit, 
            group=group,
            jobs=[JobCard(**r) for r in rows]
        )
    else:
        rows = await repo.top_jobs_with_growth(year=year, limit=limit, group=group)
        response = JobTopResponse(
            year=year, 
            by=by, 
            limit=limit, 
            group=group,
            jobs=[JobCard(**r) for r in rows]
        )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top-trends", response_model=JobTopTrendsResponse)
async def top_jobs_trends(
    year_from: int = Query(2011, description="Start year"),
    year_to: int = Query(2024, description="End year"),
    limit: int = Query(10, ge=1, le=20),
    group: Optional[str] = Query(None),
    sort_by: Literal["employment", "salary"] = Query("employment", description="Sort top jobs by this criteria"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobTopTrendsResponse:
    """Employment trends for top jobs over time"""
    cache_key = f"jobs_trends_{year_from}_{year_to}_{limit}_{group}_{sort_by}"
    cached = cache.get(cache_key)
    if cached:
        return JobTopTrendsResponse(**cached)
    
    repo = JobsRepo(db)
    
    series = await repo.top_jobs_trends(
        year_from=year_from,
        year_to=year_to,
        limit=limit,
        group=group,
        sort_by=sort_by
    )
    
    response = JobTopTrendsResponse(
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        limit=limit,
        series=series
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top-salary-trends", response_model=JobTopSalaryTrendsResponse)
async def top_jobs_salary_trends(
    year_from: int = Query(2011, description="Start year"),
    year_to: int = Query(2024, description="End year"),
    limit: int = Query(10, ge=1, le=20),
    group: Optional[str] = Query(None),
    sort_by: Literal["employment", "salary"] = Query("employment", description="Sort top jobs by this criteria"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobTopSalaryTrendsResponse:
    """Salary trends for top jobs over time"""
    cache_key = f"jobs_salary_trends_{year_from}_{year_to}_{limit}_{group}_{sort_by}"
    cached = cache.get(cache_key)
    if cached:
        return JobTopSalaryTrendsResponse(**cached)
    
    repo = JobsRepo(db)
    
    series = await repo.top_jobs_salary_trends(
        year_from=year_from,
        year_to=year_to,
        limit=limit,
        group=group,
        sort_by=sort_by
    )
    
    response = JobTopSalaryTrendsResponse(
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        limit=limit,
        series=series
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top-combined", response_model=JobTopCombinedResponse)
async def top_jobs_combined(
    year: int = Query(...),
    limit: int = Query(10, ge=1, le=20),
    by: Literal["employment", "salary"] = Query("employment"),
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobTopCombinedResponse:
    """Get combined data for top jobs - employment and salary trends"""
    cache_key = f"jobs_combined_{year}_{limit}_{by}_{group}"
    cached = cache.get(cache_key)
    if cached:
        return JobTopCombinedResponse(**cached)
    
    repo = JobsRepo(db)
    
    # Get top jobs list
    top_jobs_list = await repo.top_jobs(
        year=year,
        limit=limit,
        by=by,
        group=group
    )
    
    # Get employment trends for these jobs
    employment_trends = await repo.top_jobs_trends(
        year_from=2011,
        year_to=year,
        limit=limit,
        group=group,
        sort_by=by
    )
    
    # Get salary trends for these jobs
    salary_trends = await repo.top_jobs_salary_trends(
        year_from=2011,
        year_to=year,
        limit=limit,
        group=group,
        sort_by=by
    )
    
    response = JobTopCombinedResponse(
        year=year,
        by=by,
        limit=limit,
        group=group,
        top_jobs=top_jobs_list,
        employment_trends=employment_trends,
        salary_trends=salary_trends
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/composition/{year}", response_model=JobCompositionResponse)
async def job_composition(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobCompositionResponse:
    """Job distribution by SOC major group - SIMPLIFIED"""
    cache_key = f"jobs_composition_{year}"
    cached = cache.get(cache_key)
    if cached:
        return JobCompositionResponse(**cached)
    
    repo = JobsRepo(db)
    rows = await repo.job_composition_by_group(year)
    
    response = JobCompositionResponse(
        year=year,
        rows=rows
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/salary-distribution/{year}", response_model=JobSalaryDistribution)
async def salary_distribution(
    year: int,
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobSalaryDistribution:
    """Salary quartiles for jobs - SIMPLIFIED"""
    cache_key = f"jobs_salary_dist_{year}_{group}"
    cached = cache.get(cache_key)
    if cached:
        return JobSalaryDistribution(**cached)
    
    repo = JobsRepo(db)
    data = await repo.salary_distribution(year, group)
    
    response = JobSalaryDistribution(**data)
    cache.set(cache_key, response.dict())
    return response


@router.get("/{occ_code}/metrics", response_model=JobDetailMetrics)
async def job_metrics(
    occ_code: str,
    year: int = Query(...),
    naics: Optional[str] = Query(None, description="Industry NAICS (default: cross-industry)"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobDetailMetrics:
    """Get metrics for a specific job/occupation"""
    cache_key = f"jobs_{occ_code}_metrics_{year}_{naics}"
    cached = cache.get(cache_key)
    if cached:
        return JobDetailMetrics(**cached)
    
    repo = JobsRepo(db)
    data = await repo.job_metrics(occ_code, year, naics)
    
    if data["total_employment"] == 0 and not naics:
        raise HTTPException(status_code=404, detail=f"No data for occ_code={occ_code} in {year}")
    
    response = JobDetailMetrics(**data)
    cache.set(cache_key, response.dict())
    return response


@router.get("/{occ_code}/summary", response_model=JobSummaryResponse)
async def job_summary(
    occ_code: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    naics: Optional[str] = Query(None, description="Industry NAICS (default: cross-industry)"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobSummaryResponse:
    """Time series summary for a job"""
    cache_key = f"jobs_{occ_code}_summary_{year_from}_{year_to}_{naics}"
    cached = cache.get(cache_key)
    if cached:
        return JobSummaryResponse(**cached)
    
    repo = JobsRepo(db)
    job_title, series = await repo.job_summary(occ_code, year_from, year_to, naics)
    
    # Get naics_title if naics provided
    naics_title = None
    if naics:
        doc = await db["bls_oews"].find_one(
            {"naics": naics, "year": year_to},
            {"naics_title": 1, "_id": 0}
        )
        naics_title = str(doc.get("naics_title", "")).strip() if doc else None
    
    response = JobSummaryResponse(
        occ_code=occ_code,
        occ_title=job_title,
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        naics=naics,
        naics_title=naics_title,
        series=[JobYearPoint(**p) for p in series]
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/industry/{naics}/jobs", response_model=JobIndustryJobsResponse)
async def jobs_in_industry(
    naics: str,
    year: int = Query(...),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobIndustryJobsResponse:
    """Get jobs within a specific industry"""
    cache_key = f"jobs_in_industry_{naics}_{year}_{limit}_{offset}"
    cached = cache.get(cache_key)
    if cached:
        return JobIndustryJobsResponse(**cached)
    
    repo = JobsRepo(db)
    naics_title, rows = await repo.jobs_in_industry(naics, year, limit, offset)
    
    response = JobIndustryJobsResponse(
        naics=naics,
        naics_title=naics_title,
        year=year,
        count=len(rows),
        jobs=[JobIndustryJob(**r) for r in rows]
    )
    
    cache.set(cache_key, response.dict())
    return response
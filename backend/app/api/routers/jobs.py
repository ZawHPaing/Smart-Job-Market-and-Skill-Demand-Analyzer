from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Literal, List, Dict, Any

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
    JobTrendSeries,
    JobTrendPoint,
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

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    year: Optional[int] = Query(None, description="If omitted, uses latest year"),
    group: Optional[str] = Query(None, description="Filter by SOC group (detail, major, total)"),
    search: Optional[str] = Query(None, description="Search by job title"),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobListResponse:
    """List all jobs/occupations with pagination and search"""
    repo = JobsRepo(db)
    y, jobs = await repo.list_jobs(
        year=year, 
        group=group, 
        search=search,
        limit=limit, 
        offset=offset
    )
    
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found")
    
    return JobListResponse(
        year=y,
        count=len(jobs),
        jobs=[JobItem(**j) for j in jobs]
    )


@router.get("/search", response_model=List[JobItem])
async def search_jobs(
    q: str = Query(..., min_length=2, description="Search query"),
    year: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: "AgnosticDatabase" = Depends(get_db),
) -> List[JobItem]:
    """Quick search for job autocomplete"""
    repo = JobsRepo(db)
    jobs = await repo.search_jobs(query=q, year=year, limit=limit)
    return [JobItem(**j) for j in jobs]


@router.get("/metrics/{year}", response_model=JobDashboardMetrics)
async def dashboard_metrics(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobDashboardMetrics:
    """Dashboard metrics for jobs overview"""
    repo = JobsRepo(db)
    data = await repo.dashboard_metrics(year)
    
    top = data.get("top_growing_job")
    top_obj = TopGrowingJob(**top) if top else None
    
    return JobDashboardMetrics(
        year=data["year"],
        total_jobs=data["total_jobs"],
        total_employment=data["total_employment"],
        avg_job_growth_pct=data["avg_job_growth_pct"],
        top_growing_job=top_obj,
        median_job_salary=data["median_job_salary"],
    )


@router.get("/groups/{year}", response_model=JobGroupsResponse)
async def job_groups(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobGroupsResponse:
    """Get distinct occupation groups (SOC major groups)"""
    repo = JobsRepo(db)
    groups = await repo.job_groups(year)
    
    return JobGroupsResponse(
        year=year,
        groups=[JobGroupItem(**g) for g in groups]
    )


@router.get("/top", response_model=JobTopResponse)
async def top_jobs(
    year: int = Query(...),
    limit: int = Query(10, ge=1, le=50),
    by: Literal["employment", "salary"] = Query("employment"),
    group: Optional[str] = Query(None, description="Filter by SOC group"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobTopResponse:
    """Top jobs by employment or salary"""
    repo = JobsRepo(db)
    
    if by == "salary":
        rows = await repo.top_jobs(year=year, limit=limit, by="salary", group=group)
        return JobTopResponse(
            year=year, 
            by=by, 
            limit=limit, 
            group=group,
            jobs=[JobCard(**r) for r in rows]
        )
    
    rows = await repo.top_jobs_with_growth(year=year, limit=limit, group=group)
    return JobTopResponse(
        year=year, 
        by=by, 
        limit=limit, 
        group=group,
        jobs=[JobCard(**r) for r in rows]
    )


@router.get("/top-trends", response_model=JobTopTrendsResponse)
async def top_jobs_trends(
    year_from: int = Query(2019),
    year_to: int = Query(2024),
    limit: int = Query(4, ge=1, le=10),
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobTopTrendsResponse:
    """Employment trends for top jobs over time - SIMPLIFIED to return empty response"""
    repo = JobsRepo(db)
    
    # Get top jobs at the end year
    top = await repo.top_jobs(year=year_to, limit=limit, by="employment", group=group)
    occ_codes = [t["occ_code"] for t in top if t.get("occ_code")]
    
    if not occ_codes:
        return JobTopTrendsResponse(
            year_from=min(year_from, year_to),
            year_to=max(year_from, year_to),
            limit=limit,
            series=[]
        )
    
    # SIMPLIFIED: Just return empty series for now to avoid errors
    return JobTopTrendsResponse(
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        limit=limit,
        series=[]
    )


@router.get("/composition/{year}", response_model=JobCompositionResponse)
async def job_composition(
    year: int,
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobCompositionResponse:
    """Job distribution by SOC major group - SIMPLIFIED"""
    repo = JobsRepo(db)
    rows = await repo.job_composition_by_group(year)
    
    return JobCompositionResponse(
        year=year,
        rows=rows  # Will be empty list from simplified repo
    )


@router.get("/salary-distribution/{year}", response_model=JobSalaryDistribution)
async def salary_distribution(
    year: int,
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobSalaryDistribution:
    """Salary quartiles for jobs - SIMPLIFIED"""
    repo = JobsRepo(db)
    data = await repo.salary_distribution(year, group)
    
    return JobSalaryDistribution(**data)


@router.get("/{occ_code}/metrics", response_model=JobDetailMetrics)
async def job_metrics(
    occ_code: str,
    year: int = Query(...),
    naics: Optional[str] = Query(None, description="Industry NAICS (default: cross-industry)"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobDetailMetrics:
    """Get metrics for a specific job/occupation"""
    repo = JobsRepo(db)
    data = await repo.job_metrics(occ_code, year, naics)
    
    if data["total_employment"] == 0 and not naics:
        raise HTTPException(status_code=404, detail=f"No data for occ_code={occ_code} in {year}")
    
    return JobDetailMetrics(**data)


@router.get("/{occ_code}/summary", response_model=JobSummaryResponse)
async def job_summary(
    occ_code: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    naics: Optional[str] = Query(None, description="Industry NAICS (default: cross-industry)"),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobSummaryResponse:
    """Time series summary for a job"""
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
    
    return JobSummaryResponse(
        occ_code=occ_code,
        occ_title=job_title,
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        naics=naics,
        naics_title=naics_title,
        series=[JobYearPoint(**p) for p in series]
    )


@router.get("/industry/{naics}/jobs", response_model=JobIndustryJobsResponse)
async def jobs_in_industry(
    naics: str,
    year: int = Query(...),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: "AgnosticDatabase" = Depends(get_db),
) -> JobIndustryJobsResponse:
    """Get jobs within a specific industry"""
    repo = JobsRepo(db)
    naics_title, rows = await repo.jobs_in_industry(naics, year, limit, offset)
    
    return JobIndustryJobsResponse(
        naics=naics,
        naics_title=naics_title,
        year=year,
        count=len(rows),
        jobs=[JobIndustryJob(**r) for r in rows]
    )
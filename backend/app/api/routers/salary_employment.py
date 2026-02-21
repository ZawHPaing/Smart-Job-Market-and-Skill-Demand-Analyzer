from __future__ import annotations

import math
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from motor.core import AgnosticDatabase

from app.api.dependencies import get_db
from app.api.crud.salary_repo import SalaryRepo
from app.models.salary_models import (
    MetricsResponse,
    MetricItem,
    Trend,
    IndustryBarResponse,
    BarPoint,
    PagedIndustries,
    PagedJobs,
    IndustrySalaryTimeSeriesResponse,
    MultiLineSeries,
    TimeSeriesPoint,
    TopCrossIndustryJobsResponse,
    JobEmploymentTimeSeriesResponse,
)
from app.services.cache import cache

router = APIRouter(prefix="/salary-employment", tags=["Salary & Employment"])


def _normalize_names(names: List[str]) -> List[str]:
    if not names:
        return []
    if len(names) == 1 and isinstance(names[0], str) and "," in names[0]:
        parts = [p.strip() for p in names[0].split(",")]
        return [p for p in parts if p]
    out: List[str] = []
    for n in names:
        if isinstance(n, str):
            s = n.strip()
            if s:
                out.append(s)
    return out


def _make_key(value: object) -> str:
    if value is None:
        s = "unknown"
    elif isinstance(value, float) and math.isnan(value):
        s = "unknown"
    else:
        s = str(value)

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:30] or "unknown"


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    year: Optional[int] = Query(None, description="If omitted, uses latest year"),
    db: AgnosticDatabase = Depends(get_db),
) -> MetricsResponse:
    cache_key = f"salary_metrics_{year}"
    cached = cache.get(cache_key)
    if cached:
        return MetricsResponse(**cached)
    
    repo = SalaryRepo(db)
    y = year or await repo.latest_year()
    data = await repo.dashboard_metrics(y)

    def direction(v: float) -> str:
        if v > 0:
            return "up"
        if v < 0:
            return "down"
        return "flat"

    metrics = [
        MetricItem(
            title="Total Employment",
            value=data["totalEmployment"],
            trend=Trend(value=abs(data["employmentTrendPct"]), direction=direction(data["employmentTrendPct"])),
            color="cyan",
        ),
        MetricItem(
            title="Median Salary",
            value=data["medianSalary"],
            prefix="$",
            trend=Trend(value=abs(data["salaryTrendPct"]), direction=direction(data["salaryTrendPct"])),
            color="purple",
        ),
        MetricItem(
            title="Employment Trend",
            value=f'{data["employmentTrendPct"]:+.2f}%',
            trend=Trend(value=abs(data["employmentTrendPct"]), direction=direction(data["employmentTrendPct"])),
            color="green",
        ),
        MetricItem(
            title="Salary Trend",
            value=f'{data["salaryTrendPct"]:+.2f}%',
            trend=Trend(value=abs(data["salaryTrendPct"]), direction=direction(data["salaryTrendPct"])),
            color="coral",
        ),
        MetricItem(
            title="Highest Paying Industry",
            value=data["topIndustry"],
            color="amber",
        ),
    ]
    
    response = MetricsResponse(year=y, metrics=metrics)
    cache.set(cache_key, response.dict())
    return response


@router.get("/industries/bar", response_model=IndustryBarResponse)
async def industries_bar(
    year: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
    db: AgnosticDatabase = Depends(get_db),
) -> IndustryBarResponse:
    cache_key = f"salary_industries_bar_{year}_{search}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryBarResponse(**cached)
    
    repo = SalaryRepo(db)
    y = year or await repo.latest_year()
    items = await repo.industry_bar(y, search, limit)
    
    response = IndustryBarResponse(year=y, items=[BarPoint(**it) for it in items])
    cache.set(cache_key, response.dict())
    return response


@router.get("/industries", response_model=PagedIndustries)
async def industries_table(
    year: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=5, le=100),
    sort_by: str = Query("employment", pattern="^(employment|salary|name)$"),
    sort_dir: int = Query(-1, description="-1 desc, 1 asc"),
    db: AgnosticDatabase = Depends(get_db),
) -> PagedIndustries:
    cache_key = f"salary_industries_table_{year}_{search}_{page}_{page_size}_{sort_by}_{sort_dir}"
    cached = cache.get(cache_key)
    if cached:
        return PagedIndustries(**cached)
    
    repo = SalaryRepo(db)
    y = year or await repo.latest_year()
    total, items = await repo.industries_paged(y, search, page, page_size, sort_by, sort_dir)
    
    response = PagedIndustries(year=y, page=page, page_size=page_size, total=total, items=items)
    cache.set(cache_key, response.dict())
    return response


@router.get("/jobs", response_model=PagedJobs)
async def jobs_table(
    year: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=5, le=100),
    sort_by: str = Query("salary", pattern="^(employment|salary|name)$"),
    sort_dir: int = Query(-1, description="-1 desc, 1 asc"),
    db: AgnosticDatabase = Depends(get_db),
) -> PagedJobs:
    cache_key = f"salary_jobs_table_{year}_{search}_{page}_{page_size}_{sort_by}_{sort_dir}"
    cached = cache.get(cache_key)
    if cached:
        return PagedJobs(**cached)
    
    repo = SalaryRepo(db)
    y = year or await repo.latest_year()
    total, items = await repo.jobs_paged(y, search, page, page_size, sort_by, sort_dir)
    
    response = PagedJobs(year=y, page=page, page_size=page_size, total=total, items=items)
    cache.set(cache_key, response.dict())
    return response


@router.get("/jobs/top-cross-industry", response_model=TopCrossIndustryJobsResponse)
async def top_cross_industry_jobs(
    year: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AgnosticDatabase = Depends(get_db),
) -> TopCrossIndustryJobsResponse:
    cache_key = f"salary_top_cross_jobs_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return TopCrossIndustryJobsResponse(**cached)
    
    repo = SalaryRepo(db)
    y = year or await repo.latest_year()
    items = await repo.top_cross_industry_jobs(y, limit)
    
    response = TopCrossIndustryJobsResponse(year=y, items=[BarPoint(**it) for it in items])
    cache.set(cache_key, response.dict())
    return response


@router.get("/industries/salary-timeseries", response_model=IndustrySalaryTimeSeriesResponse)
async def industry_salary_timeseries(
    names: List[str] = Query(..., description="Repeat ?names=A&names=B OR comma-separated ?names=A,B"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: AgnosticDatabase = Depends(get_db),
) -> IndustrySalaryTimeSeriesResponse:
    # Sort names for consistent cache key
    sorted_names = sorted(names) if names else []
    cache_key = f"salary_timeseries_{sorted_names}_{start_year}_{end_year}"
    cached = cache.get(cache_key)
    if cached:
        return IndustrySalaryTimeSeriesResponse(**cached)
    
    repo = SalaryRepo(db)
    names = _normalize_names(names)
    rows = await repo.industry_salary_timeseries(names, start_year, end_year)

    grouped: Dict[str, List[TimeSeriesPoint]] = {}
    for r in rows:
        nm = r.get("name")
        if not isinstance(nm, str) or not nm.strip():
            continue
        grouped.setdefault(nm, []).append(TimeSeriesPoint(year=r["year"], value=r["value"]))

    series: List[MultiLineSeries] = []
    for name, pts in grouped.items():
        series.append(MultiLineSeries(key=_make_key(name), name=name, points=pts))

    response = IndustrySalaryTimeSeriesResponse(series=series)
    cache.set(cache_key, response.dict())
    return response


@router.get("/jobs/employment-timeseries", response_model=JobEmploymentTimeSeriesResponse)
async def job_employment_timeseries(
    year: Optional[int] = Query(None, description="Anchor year for selecting top jobs"),
    limit: int = Query(6, ge=1, le=20, description="Top N job titles"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: AgnosticDatabase = Depends(get_db),
) -> JobEmploymentTimeSeriesResponse:
    cache_key = f"salary_job_timeseries_v4_{year}_{limit}_{start_year}_{end_year}"
    cached = cache.get(cache_key)
    if cached:
        return JobEmploymentTimeSeriesResponse(**cached)
    
    repo = SalaryRepo(db)
    y = year or await repo.latest_year()
    rows = await repo.job_employment_timeseries(y, limit, start_year, end_year)

    series: List[MultiLineSeries] = []
    for r in rows:
        name = str(r.get("name") or "").strip()
        code = str(r.get("occ_code") or "").strip()
        points = r.get("points") or []
        if not name or not points:
            continue

        ts_points = [
            TimeSeriesPoint(year=int(p["year"]), value=int(p["value"]))
            for p in points
            if "year" in p and "value" in p
        ]
        if not ts_points:
            continue

        series.append(
            MultiLineSeries(
                key=_make_key(f"{code}_{name}" if code else name),
                name=name,
                points=ts_points,
            )
        )

    response = JobEmploymentTimeSeriesResponse(series=series)
    cache.set(cache_key, response.dict())
    return response

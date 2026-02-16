from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_db
from app.api.crud.home_repo import HomeRepo
from app.models.home_models import (
    HomeOverviewResponse,
    OverviewMetric,
    Trend,
    IndustryDistributionResponse,
    IndustryDistributionItem,
    TopJobsResponse,
    TopJobItem,
    EmploymentTrendsResponse,
    TrendSeries,
    TrendPoint,
)

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/overview", response_model=HomeOverviewResponse)
async def home_overview(
    year: Optional[int] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> HomeOverviewResponse:
    repo = HomeRepo(db)
    y, data = await repo.overview(year)

    # build metrics in the exact format your frontend expects
    total_emp = data.get("total_employment", 0.0)
    unique_ind = data.get("unique_industries", 0)
    med_sal = data.get("median_salary", 0.0)
    trend_pct = data.get("employment_trend_pct", 0.0)

    metrics = [
        OverviewMetric(
            title="Total Employment",
            value=total_emp,
            trend=Trend(value=abs(trend_pct), direction="up" if trend_pct >= 0 else "down"),
            color="cyan",
        ),
        OverviewMetric(
            title="Unique Industries",
            value=unique_ind,
            trend=Trend(value=0.0, direction="up"),
            color="purple",
        ),
        OverviewMetric(
            title="Median Annual Salary",
            value=med_sal,
            prefix="$",
            trend=Trend(value=0.0, direction="up"),
            color="amber",
        ),
    ]

    return HomeOverviewResponse(year=y, metrics=metrics)


@router.get("/industry-distribution", response_model=IndustryDistributionResponse)
async def industry_distribution(
    year: int = Query(...),
    limit: int = Query(8, ge=1, le=50),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryDistributionResponse:
    repo = HomeRepo(db)
    items = await repo.industry_distribution(year=year, limit=limit)
    return IndustryDistributionResponse(
        year=year,
        limit=limit,
        items=[IndustryDistributionItem(**x) for x in items],
    )


@router.get("/top-jobs", response_model=TopJobsResponse)
async def top_jobs(
    year: int = Query(...),
    limit: int = Query(8, ge=1, le=50),
    db: "AgnosticDatabase" = Depends(get_db),
) -> TopJobsResponse:
    repo = HomeRepo(db)
    items = await repo.top_jobs(year=year, limit=limit)
    return TopJobsResponse(
        year=year,
        limit=limit,
        items=[TopJobItem(**x) for x in items],
    )


@router.get("/employment-trends", response_model=EmploymentTrendsResponse)
async def employment_trends(
    year_from: int = Query(2019),
    year_to: int = Query(2024),
    limit: int = Query(3, ge=1, le=10),
    db: "AgnosticDatabase" = Depends(get_db),
) -> EmploymentTrendsResponse:
    repo = HomeRepo(db)
    series = await repo.employment_trends(year_from=year_from, year_to=year_to, limit=limit)

    return EmploymentTrendsResponse(
        year_from=min(year_from, year_to),
        year_to=max(year_from, year_to),
        limit=limit,
        series=[
            TrendSeries(
                naics=s["naics"],
                name=s["name"],
                points=[TrendPoint(**p) for p in s["points"]],
            )
            for s in series
        ],
    )

@router.get("/overview", response_model=HomeOverviewResponse)
async def home_overview(
    year: int = Query(...),
    db: AgnosticDatabase = Depends(get_db),
):
    repo = HomeRepo(db)
    return await repo.overview(year)
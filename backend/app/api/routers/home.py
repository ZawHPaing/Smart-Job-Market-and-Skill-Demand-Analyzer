from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_db
from app.api.crud.home_repo import HomeRepo
from app.models.home_models import (
    HomeOverviewResponse,
    OverviewMetric,
    Trend,
    MarketTickerResponse,
    MarketTickerItem,
    IndustryDistributionResponse,
    IndustryDistributionItem,
    TopJobsResponse,
    TopJobItem,
    EmploymentTrendsResponse,
    TrendSeries,
    TrendPoint,
)
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/overview", response_model=HomeOverviewResponse)
async def home_overview(
    year: Optional[int] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> HomeOverviewResponse:
    # Check cache
    cache_key = f"home_overview_{year}"
    cached = cache.get(cache_key)
    if cached:
        return HomeOverviewResponse(**cached)
    
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

    response = HomeOverviewResponse(year=y, metrics=metrics)
    cache.set(cache_key, response.dict())
    return response


@router.get("/market-ticker", response_model=MarketTickerResponse)
async def market_ticker(
    year: Optional[int] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> MarketTickerResponse:
    cache_key = f"home_market_ticker_{year}"
    cached = cache.get(cache_key)
    if cached:
        return MarketTickerResponse(**cached)

    repo = HomeRepo(db)
    data = await repo.market_ticker(year)

    def trend_dir(v: float) -> str:
        if v > 0:
            return "up"
        if v < 0:
            return "down"
        return "neutral"

    items = []
    items.append(
        MarketTickerItem(
            name="Median Salary",
            value=f"${int(round(data['median_salary']))}",
            trend=trend_dir(data["salary_trend_pct"]),
        )
    )
    items.append(
        MarketTickerItem(
            name="Salary YoY",
            value=f"{data['salary_trend_pct']:+.1f}%",
            trend=trend_dir(data["salary_trend_pct"]),
        )
    )

    top_ind = data.get("top_growing_industry") or {}
    items.append(
        MarketTickerItem(
            name=top_ind.get("name", "Top Growing Industry"),
            value=f"{top_ind.get('trend_pct', 0):+.1f}%",
            trend=trend_dir(top_ind.get("trend_pct", 0)),
        )
    )

    top_occ = data.get("top_growing_occupation") or {}
    items.append(
        MarketTickerItem(
            name=top_occ.get("name", "Top Growing Occupation"),
            value=f"{top_occ.get('trend_pct', 0):+.1f}%",
            trend=trend_dir(top_occ.get("trend_pct", 0)),
        )
    )

    top_skill = data.get("top_tech_skill") or {}
    if top_skill:
        items.append(
            MarketTickerItem(
                name="Top Tech Skill",
                value=f"{top_skill.get('name', '')}",
                trend="neutral",
            )
        )
    else:
        items.append(MarketTickerItem(name="Top Tech Skill", value="N/A", trend="neutral"))

    large_occ = data.get("largest_occupation") or {}
    items.append(
        MarketTickerItem(
            name=large_occ.get("name", "Highest Employment Occupation"),
            value=str(int(round(large_occ.get("employment", 0)))),
            trend="neutral",
        )
    )

    items.append(
        MarketTickerItem(
            name="Hot Tech Count",
            value=str(int(data.get("hot_tech_count", 0))),
            trend="neutral",
        )
    )

    response = MarketTickerResponse(year=data["year"], items=items)
    cache.set(cache_key, response.dict())
    return response


@router.get("/industry-distribution", response_model=IndustryDistributionResponse)
async def industry_distribution(
    year: int = Query(...),
    limit: int = Query(8, ge=1, le=50),
    db: "AgnosticDatabase" = Depends(get_db),
) -> IndustryDistributionResponse:
    cache_key = f"home_industry_dist_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return IndustryDistributionResponse(**cached)
    
    repo = HomeRepo(db)
    items = await repo.industry_distribution(year=year, limit=limit)
    
    response = IndustryDistributionResponse(
        year=year,
        limit=limit,
        items=[IndustryDistributionItem(**x) for x in items],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/top-jobs", response_model=TopJobsResponse)
async def top_jobs(
    year: int = Query(...),
    limit: int = Query(8, ge=1, le=50),
    db: "AgnosticDatabase" = Depends(get_db),
) -> TopJobsResponse:
    cache_key = f"home_top_jobs_{year}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return TopJobsResponse(**cached)
    
    repo = HomeRepo(db)
    items = await repo.top_jobs(year=year, limit=limit)
    
    response = TopJobsResponse(
        year=year,
        limit=limit,
        items=[TopJobItem(**x) for x in items],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/employment-trends", response_model=EmploymentTrendsResponse)
async def employment_trends(
    year_from: int = Query(2019),
    year_to: int = Query(2024),
    limit: int = Query(3, ge=1, le=10),
    db: "AgnosticDatabase" = Depends(get_db),
) -> EmploymentTrendsResponse:
    cache_key = f"home_employment_trends_{year_from}_{year_to}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return EmploymentTrendsResponse(**cached)
    
    repo = HomeRepo(db)
    series = await repo.employment_trends(year_from=year_from, year_to=year_to, limit=limit)

    response = EmploymentTrendsResponse(
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
    
    cache.set(cache_key, response.dict())
    return response

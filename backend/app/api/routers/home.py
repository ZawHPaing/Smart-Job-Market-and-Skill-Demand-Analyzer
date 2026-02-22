# app/api/routers/home.py
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.api.crud.home_repo import HomeRepo
from app.models.home_models import (
    HomeOverviewResponse,
    MarketTickerResponse,
    MarketTickerItem,
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
    
    # If year is None, get the latest year
    if year is None:
        year = await repo.latest_year()
    
    data = await repo.overview(year)
    
    response = HomeOverviewResponse(**data)
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


# Remove or comment out endpoints that don't exist in HomeRepo
# The employment_trends endpoint doesn't exist in HomeRepo
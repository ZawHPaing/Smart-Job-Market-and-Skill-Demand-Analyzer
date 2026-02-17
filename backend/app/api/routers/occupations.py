from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.dependencies import get_db
from app.api.crud.occupations_repo import OccupationsRepo
from app.models.occupation_models import (
    OccupationMetricsYearResponse,
    OccupationMetric,
    OccupationSummaryResponse,
    OccupationYearPoint,
)
from app.services.cache import cache

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase

router = APIRouter(prefix="/occupations", tags=["occupations"])


# -----------------------------
# Cross-industry (naics=000000)
# -----------------------------
@router.get("/metrics/{year}", response_model=OccupationMetricsYearResponse)
async def metrics_year_cross(
    year: int,
    group: Optional[str] = Query(None, description="detail | major | total (optional)"),
    limit: int = Query(500, ge=1, le=20000),
    offset: int = Query(0, ge=0),
    db: "AgnosticDatabase" = Depends(get_db),
) -> OccupationMetricsYearResponse:
    cache_key = f"occupations_metrics_cross_{year}_{group}_{limit}_{offset}"
    cached = cache.get(cache_key)
    if cached:
        return OccupationMetricsYearResponse(**cached)
    
    repo = OccupationsRepo(db)
    rows = await repo.metrics_for_year_cross(year, group=group, limit=limit, offset=offset)
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"No occupations found for year={year}")
    
    response = OccupationMetricsYearResponse(
        year=year,
        count=len(rows),
        occupations=[OccupationMetric(**r) for r in rows],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/{occ_code}/summary", response_model=OccupationSummaryResponse)
async def occ_summary_cross(
    occ_code: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> OccupationSummaryResponse:
    cache_key = f"occupations_summary_cross_{occ_code}_{year_from}_{year_to}_{group}"
    cached = cache.get(cache_key)
    if cached:
        return OccupationSummaryResponse(**cached)
    
    repo = OccupationsRepo(db)
    data = await repo.summary_for_occ_cross(occ_code, year_from=year_from, year_to=year_to, group=group)
    
    if not data["series"]:
        raise HTTPException(status_code=404, detail=f"No data for occ_code={occ_code}")
    
    response = OccupationSummaryResponse(
        occ_code=data["occ_code"],
        occ_title=data["occ_title"],
        year_from=data["year_from"],
        year_to=data["year_to"],
        group=data["group"],
        series=[OccupationYearPoint(**p) for p in data["series"]],
    )
    
    cache.set(cache_key, response.dict())
    return response


# -----------------------------------------
# ✅ Industry-specific (naics = specific)
# -----------------------------------------
@router.get("/industry/{naics}/metrics/{year}", response_model=OccupationMetricsYearResponse)
async def metrics_year_in_industry(
    naics: str,
    year: int,
    group: Optional[str] = Query(None, description="detail | major | total (optional)"),
    limit: int = Query(500, ge=1, le=20000),
    offset: int = Query(0, ge=0),
    db: "AgnosticDatabase" = Depends(get_db),
) -> OccupationMetricsYearResponse:
    cache_key = f"occupations_metrics_industry_{naics}_{year}_{group}_{limit}_{offset}"
    cached = cache.get(cache_key)
    if cached:
        return OccupationMetricsYearResponse(**cached)
    
    repo = OccupationsRepo(db)
    rows = await repo.metrics_for_year_in_naics(naics=naics, year=year, group=group, limit=limit, offset=offset)
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"No occupations found for naics={naics} in year={year}")
    
    response = OccupationMetricsYearResponse(
        year=year,
        count=len(rows),
        occupations=[OccupationMetric(**r) for r in rows],
    )
    
    cache.set(cache_key, response.dict())
    return response


@router.get("/industry/{naics}/{occ_code}/summary", response_model=OccupationSummaryResponse)
async def occ_summary_in_industry(
    naics: str,
    occ_code: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> OccupationSummaryResponse:
    cache_key = f"occupations_summary_industry_{naics}_{occ_code}_{year_from}_{year_to}_{group}"
    cached = cache.get(cache_key)
    if cached:
        return OccupationSummaryResponse(**cached)
    
    repo = OccupationsRepo(db)
    data = await repo.summary_for_occ_in_naics(
        naics=naics, occ_code=occ_code, year_from=year_from, year_to=year_to, group=group
    )
    
    if not data["series"]:
        raise HTTPException(status_code=404, detail=f"No data for occ_code={occ_code} in naics={naics}")
    
    response = OccupationSummaryResponse(
        occ_code=data["occ_code"],
        occ_title=data["occ_title"],
        year_from=data["year_from"],
        year_to=data["year_to"],
        group=data["group"],
        series=[OccupationYearPoint(**p) for p in data["series"]],
    )
    
    cache.set(cache_key, response.dict())
    return response
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
    repo = OccupationsRepo(db)
    rows = await repo.metrics_for_year_cross(year, group=group, limit=limit, offset=offset)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No occupations found for year={year}")
    return OccupationMetricsYearResponse(
        year=year,
        count=len(rows),
        occupations=[OccupationMetric(**r) for r in rows],
    )


@router.get("/{occ_code}/summary", response_model=OccupationSummaryResponse)
async def occ_summary_cross(
    occ_code: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> OccupationSummaryResponse:
    repo = OccupationsRepo(db)
    data = await repo.summary_for_occ_cross(occ_code, year_from=year_from, year_to=year_to, group=group)
    if not data["series"]:
        raise HTTPException(status_code=404, detail=f"No data for occ_code={occ_code}")
    return OccupationSummaryResponse(
        occ_code=data["occ_code"],
        occ_title=data["occ_title"],
        year_from=data["year_from"],
        year_to=data["year_to"],
        group=data["group"],
        series=[OccupationYearPoint(**p) for p in data["series"]],
    )


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
    repo = OccupationsRepo(db)
    rows = await repo.metrics_for_year_in_naics(naics=naics, year=year, group=group, limit=limit, offset=offset)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No occupations found for naics={naics} in year={year}")
    return OccupationMetricsYearResponse(
        year=year,
        count=len(rows),
        occupations=[OccupationMetric(**r) for r in rows],
    )


@router.get("/industry/{naics}/{occ_code}/summary", response_model=OccupationSummaryResponse)
async def occ_summary_in_industry(
    naics: str,
    occ_code: str,
    year_from: int = Query(2011),
    year_to: int = Query(2024),
    group: Optional[str] = Query(None),
    db: "AgnosticDatabase" = Depends(get_db),
) -> OccupationSummaryResponse:
    repo = OccupationsRepo(db)
    data = await repo.summary_for_occ_in_naics(
        naics=naics, occ_code=occ_code, year_from=year_from, year_to=year_to, group=group
    )
    if not data["series"]:
        raise HTTPException(status_code=404, detail=f"No data for occ_code={occ_code} in naics={naics}")
    return OccupationSummaryResponse(
        occ_code=data["occ_code"],
        occ_title=data["occ_title"],
        year_from=data["year_from"],
        year_to=data["year_to"],
        group=data["group"],
        series=[OccupationYearPoint(**p) for p in data["series"]],
    )

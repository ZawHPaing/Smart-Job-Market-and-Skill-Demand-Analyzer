from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class OccupationMetric(BaseModel):
    occ_code: str
    occ_title: str
    total_employment: float
    median_salary: Optional[float] = None
    group: Optional[str] = None


class OccupationMetricsYearResponse(BaseModel):
    year: int
    count: int
    occupations: List[OccupationMetric]


class OccupationYearPoint(BaseModel):
    year: int
    total_employment: float
    median_salary: Optional[float] = None


class OccupationSummaryResponse(BaseModel):
    occ_code: str
    occ_title: str
    year_from: int
    year_to: int
    group: Optional[str] = None
    series: List[OccupationYearPoint]

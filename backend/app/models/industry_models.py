# app/models/industry_models.py
from __future__ import annotations

from typing import List, Optional
from typing import Any, Dict, List
from pydantic import BaseModel
import math


class IndustryItem(BaseModel):
    naics: str
    naics_title: str


class IndustryListResponse(BaseModel):
    year: int
    count: int
    industries: List[IndustryItem]


class JobDetail(BaseModel):
    occ_code: str
    occ_title: str
    employment: float
    median_salary: Optional[float] = None


class IndustryJobsResponse(BaseModel):
    naics: str
    naics_title: str
    year: int
    page: int
    page_size: int
    total: int
    jobs: List[JobDetail]
    
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.page_size) if self.total > 0 else 1


class IndustryTopJobsResponse(BaseModel):
    naics: str
    naics_title: str
    year: int
    limit: int
    jobs: List[JobDetail]


class IndustryTopJobResponse(BaseModel):
    naics: str
    naics_title: str
    year: int
    job: Optional[JobDetail] = None


class IndustryDetailMetrics(BaseModel):
    naics: str
    naics_title: str
    year: int
    total_employment: float
    median_salary: float


class IndustryYearPoint(BaseModel):
    year: int
    total_employment: float
    median_salary: float


class IndustrySummaryResponse(BaseModel):
    naics: str
    naics_title: str
    year_from: int
    year_to: int
    series: List[IndustryYearPoint]


class TopGrowingIndustry(BaseModel):
    naics: str
    naics_title: str
    growth_pct: float


class IndustryDashboardMetrics(BaseModel):
    year: int
    total_industries: int
    total_employment: float
    avg_industry_growth_pct: float
    top_growing_industry: Optional[TopGrowingIndustry] = None
    median_industry_salary: float

class IndustryCard(BaseModel):
    naics: str
    naics_title: str
    total_employment: float
    median_salary: float
    growth_pct: Optional[float] = None


class IndustryTopResponse(BaseModel):
    year: int
    by: str
    limit: int
    industries: List[IndustryCard]


class IndustryTrendPoint(BaseModel):
    year: int
    employment: float


class IndustryTrendSeries(BaseModel):
    naics: str
    naics_title: str
    points: List[IndustryTrendPoint]


class IndustryTopTrendsResponse(BaseModel):
    year_from: int
    year_to: int
    limit: int
    series: List[IndustryTrendSeries]


class IndustryCompositionRow(BaseModel):
    industry: str
    juniorRoles: float
    midRoles: float
    seniorRoles: float


class IndustryCompositionResponse(BaseModel):
    year: int
    limit: int
    rows: List[IndustryCompositionRow]

class IndustryTopOccRow(BaseModel):
    industry: str
    occ1_emp: float = 0
    occ2_emp: float = 0
    occ3_emp: float = 0

class IndustryTopOccLegendItem(BaseModel):
    key: str        # "occ1_emp" | "occ2_emp" | "occ3_emp"
    name: str       # occupation title shown in legend

class IndustryTopOccCompositionResponse(BaseModel):
    year: int
    industries_limit: int
    top_n_occ: int
    rows: List[IndustryTopOccRow]
    legend: List[IndustryTopOccLegendItem]

class IndustryTopOccLegendItem(BaseModel):
    key: str           # e.g. "occ1_emp"
    name: str          # e.g. "Registered Nurses"

class IndustryTopOccRow(BaseModel):
    industry: str
    occ1_emp: float = 0.0
    occ2_emp: float = 0.0
    occ3_emp: float = 0.0

class IndustryTopOccCompositionResponse(BaseModel):
    year: int
    industries_limit: int
    top_n_occ: int
    rows: List[Dict[str, Any]]   # ✅ allow any keys (occ*_emp, occ*_title)
    legend: List[Dict[str, Any]]

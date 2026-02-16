from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Trend(BaseModel):
    value: float = 0.0
    direction: Literal["up", "down", "flat"] = "flat"


class MetricItem(BaseModel):
    title: str
    value: float | int | str
    prefix: Optional[str] = None
    trend: Optional[Trend] = None
    color: Optional[str] = None


class IndustryRow(BaseModel):
    id: str = Field(..., description="naics code (or group key)")
    name: str = Field(..., description="naics_title")
    employment: int
    medianSalary: int
    trend: float = 0.0  # YoY %


class JobRow(BaseModel):
    occ_code: str
    occ_title: str
    employment: int
    medianSalary: int
    trend: float = 0.0  # YoY %


class PagedIndustries(BaseModel):
    year: int
    page: int
    page_size: int
    total: int
    items: List[IndustryRow]


class PagedJobs(BaseModel):
    year: int
    page: int
    page_size: int
    total: int
    items: List[JobRow]


class BarPoint(BaseModel):
    name: str
    value: int
    secondaryValue: int


class IndustryBarResponse(BaseModel):
    year: int
    items: List[BarPoint]


# ✅ NEW
class TopCrossIndustryJobsResponse(BaseModel):
    year: int
    items: List[BarPoint]


class TimeSeriesPoint(BaseModel):
    year: int
    value: int


class MultiLineSeries(BaseModel):
    key: str
    name: str
    points: List[TimeSeriesPoint]


class IndustrySalaryTimeSeriesResponse(BaseModel):
    series: List[MultiLineSeries]


class JobEmploymentTimeSeriesResponse(BaseModel):
    series: List[MultiLineSeries]


class MetricsResponse(BaseModel):
    year: int
    metrics: List[MetricItem]

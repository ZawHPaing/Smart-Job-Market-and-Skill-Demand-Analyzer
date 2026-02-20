from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class Trend(BaseModel):
    value: float
    direction: str  # "up" | "down"


class OverviewMetric(BaseModel):
    title: str
    value: float | str
    prefix: Optional[str] = None
    trend: Trend
    color: str  # "cyan" | "purple" | "coral" | "green" | "amber"


class HomeOverviewResponse(BaseModel):
    year: int
    metrics: List[OverviewMetric]


class IndustryDistributionItem(BaseModel):
    name: str
    value: float


class IndustryDistributionResponse(BaseModel):
    year: int
    limit: int
    items: List[IndustryDistributionItem]


class TopJobItem(BaseModel):
    name: str
    postings: float
    salary: Optional[float] = None


class TopJobsResponse(BaseModel):
    year: int
    limit: int
    items: List[TopJobItem]


class TrendPoint(BaseModel):
    year: int
    employment: float


class TrendSeries(BaseModel):
    naics: str
    name: str
    points: List[TrendPoint]


class EmploymentTrendsResponse(BaseModel):
    year_from: int
    year_to: int
    limit: int
    series: List[TrendSeries]

class MarketTickerItem(BaseModel):
    name: str
    value: str
    trend: str  # "up" | "down" | "neutral"


class MarketTickerResponse(BaseModel):
    year: int
    items: List[MarketTickerItem]

class HomeOverviewResponse(BaseModel):
    year: int
    total_employment: float
    unique_industries: int
    unique_job_titles: int
    industry_trend_pct: float  # YoY % change in total employment
    median_annual_salary: float

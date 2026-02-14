from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ForecastMetric(BaseModel):
    title: str
    value: float | str
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    trend: Optional[Dict[str, Any]] = None
    color: str


class ForecastPoint(BaseModel):
    year: int
    actual: Optional[float] = None
    forecast: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class IndustryForecast(BaseModel):
    industry: str
    naics: str
    historical: List[ForecastPoint]
    forecast: List[ForecastPoint]
    growth_rate: float
    confidence: float


class JobForecast(BaseModel):
    job_title: str
    occ_code: str
    historical: List[ForecastPoint]
    forecast: List[ForecastPoint]
    growth_rate: float
    confidence: float


class ForecastSummary(BaseModel):
    year: int
    total_employment: float
    median_salary: float
    top_growth_industries: List[Dict[str, Any]]
    top_growth_jobs: List[Dict[str, Any]]


class ForecastResponse(BaseModel):
    forecast_year: int
    metrics: List[ForecastMetric]
    industry_composition: List[Dict[str, Any]]
    employment_forecast: List[Dict[str, Any]]
    top_jobs_forecast: List[Dict[str, Any]]
    industry_details: List[Dict[str, Any]]
    confidence_level: str
    disclaimer: str
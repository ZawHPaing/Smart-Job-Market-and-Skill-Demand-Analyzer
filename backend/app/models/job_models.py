from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel


class JobItem(BaseModel):
    occ_code: str
    occ_title: str
    total_employment: float
    median_salary: Optional[float] = None
    group: Optional[str] = None
    jobs_percent: Optional[float] = None


class JobListResponse(BaseModel):
    year: int
    count: int
    jobs: List[JobItem]


class JobDetailMetrics(BaseModel):
    occ_code: str
    occ_title: str
    year: int
    total_employment: float
    median_salary: Optional[float] = None
    group: Optional[str] = None
    naics: Optional[str] = None
    naics_title: Optional[str] = None


class JobYearPoint(BaseModel):
    year: int
    total_employment: float
    median_salary: Optional[float] = None


class JobSummaryResponse(BaseModel):
    occ_code: str
    occ_title: str
    year_from: int
    year_to: int
    naics: Optional[str] = None
    naics_title: Optional[str] = None
    series: List[JobYearPoint]


class TopGrowingJob(BaseModel):
    occ_code: str
    occ_title: str
    growth_pct: float


class JobDashboardMetrics(BaseModel):
    year: int
    total_jobs: int
    total_employment: float
    avg_job_growth_pct: float
    top_growing_job: Optional[TopGrowingJob] = None
    median_job_salary: float


class JobCard(BaseModel):
    occ_code: str
    occ_title: str
    total_employment: float
    median_salary: Optional[float] = None
    growth_pct: Optional[float] = None
    group: Optional[str] = None


class JobTopResponse(BaseModel):
    year: int
    by: Literal["employment", "salary"]
    limit: int
    group: Optional[str] = None
    jobs: List[JobCard]


class JobTrendPoint(BaseModel):
    year: int
    employment: float


class JobTrendSeries(BaseModel):
    occ_code: str
    occ_title: str
    points: List[JobTrendPoint]


class JobTopTrendsResponse(BaseModel):
    year_from: int
    year_to: int
    limit: int
    series: List[JobTrendSeries]


class JobGroupItem(BaseModel):
    group: str


class JobGroupsResponse(BaseModel):
    year: int
    groups: List[JobGroupItem]


class JobCompositionRow(BaseModel):
    group: str
    employment: float
    avg_salary: float


class JobCompositionResponse(BaseModel):
    year: int
    rows: List[JobCompositionRow]


class JobSalaryDistribution(BaseModel):
    year: int
    group: Optional[str] = None
    total_jobs: int
    q1: float
    median: float
    q3: float
    min: float
    max: float


class JobIndustryJob(BaseModel):
    occ_code: str
    occ_title: str
    employment: float
    median_salary: Optional[float] = None


class JobIndustryJobsResponse(BaseModel):
    naics: str
    naics_title: str
    year: int
    count: int
    jobs: List[JobIndustryJob]
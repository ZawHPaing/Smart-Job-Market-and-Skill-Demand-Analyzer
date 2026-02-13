from __future__ import annotations

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel


class SkillMetric(BaseModel):
    title: str
    value: float | str
    suffix: Optional[str] = None
    prefix: Optional[str] = None
    trend: Optional[Dict[str, Any]] = None
    color: Literal["cyan", "purple", "coral", "green", "amber"]


class SkillBasicInfo(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: Literal["tech", "soft", "general", "ability", "knowledge", "work_activity", "tool"]
    classification: List[str]
    description: Optional[str] = None


class SkillUsageData(BaseModel):
    name: str
    value: float
    color: str


class CoOccurringSkill(BaseModel):
    id: str
    name: str
    type: str
    frequency: float
    demand_trend: Optional[float] = 0
    salary_association: Optional[float] = 0


class JobRequiringSkill(BaseModel):
    title: str
    soc_code: str
    importance: float
    level: Optional[float] = None
    median_salary: Optional[float] = None
    employment: Optional[float] = None


class SkillDetailResponse(BaseModel):
    basic_info: SkillBasicInfo
    metrics: List[SkillMetric]
    usage_data: List[SkillUsageData]
    usage_percentage: float
    co_occurring_skills: List[CoOccurringSkill]
    top_jobs: List[JobRequiringSkill]
    total_jobs_count: int
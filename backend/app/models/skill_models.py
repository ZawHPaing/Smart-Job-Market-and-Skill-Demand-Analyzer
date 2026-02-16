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
    skill_type: Literal["tech", "soft", "general", "ability", "knowledge", "work_activity", "tool", "skill"]
    classification: List[str]
    description: Optional[str] = None


class SkillUsageData(BaseModel):
    name: str
    value: float
    color: str


# UPDATED: Added all new fields
class CoOccurringSkill(BaseModel):
    id: str
    name: str
    type: str
    frequency: int
    co_occurrence_rate: Optional[float] = None
    demand_trend: Optional[float] = 0
    salary_association: Optional[float] = 0
    # NEW FIELDS - make sure these are included
    usage_count: Optional[int] = None
    avg_importance: Optional[float] = None
    avg_level: Optional[float] = None
    hot_technology: Optional[bool] = False
    in_demand: Optional[bool] = False


class JobRequiringSkill(BaseModel):
    title: str
    soc_code: str
    importance: float
    level: Optional[float] = None
    median_salary: Optional[float] = None
    employment: Optional[float] = None
    hot_technology: Optional[bool] = False
    in_demand: Optional[bool] = False


class NetworkNode(BaseModel):
    id: str
    name: str
    group: str
    value: float
    usage_count: Optional[int] = None
    co_occurrence_rate: Optional[float] = None
    avg_importance: Optional[float] = None
    avg_level: Optional[float] = None


class NetworkLink(BaseModel):
    source: str
    target: str
    value: float
    co_occurrence_rate: Optional[float] = None


class NetworkGraph(BaseModel):
    nodes: List[NetworkNode]
    links: List[NetworkLink]


class SkillDetailResponse(BaseModel):
    basic_info: SkillBasicInfo
    metrics: List[SkillMetric]
    usage_data: List[SkillUsageData]
    usage_percentage: float
    co_occurring_skills: List[CoOccurringSkill]
    top_jobs: List[JobRequiringSkill]
    total_jobs_count: int
    network_graph: Optional[NetworkGraph] = None
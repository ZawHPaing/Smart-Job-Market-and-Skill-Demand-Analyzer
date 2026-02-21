from __future__ import annotations

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel


class JobBasicInfo(BaseModel):
    occ_code: str
    occ_title: str
    description: Optional[str] = None
    soc_code: Optional[str] = None


# In job_detail_models.py, update the JobMetric class:

class JobMetric(BaseModel):
    title: str
    value: float | str
    trend: Optional[Dict[str, Any]] = None
    color: Optional[Literal["cyan", "coral", "purple", "green", "amber"]] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    format: Optional[Literal["fmtK", "fmtM", "fmtPercent", "industry"]] = None  # Add "industry" here


class JobSkill(BaseModel):
    name: str
    value: float
    type: Literal["tech", "soft", "general", "skill", "tool"]
    commodity_code: Optional[str] = None
    commodity_title: Optional[str] = None
    hot_technology: Optional[bool] = None
    in_demand: Optional[bool] = None


class JobActivity(BaseModel):
    name: str
    value: float
    element_id: Optional[str] = None


class JobAbility(BaseModel):
    name: str
    category: str
    value: float
    element_id: Optional[str] = None


class JobKnowledge(BaseModel):
    name: str
    level: Literal["Basic", "Intermediate", "Advanced", "Expert"]
    value: float


class JobEducation(BaseModel):
    category: int
    description: str
    required_level: str
    value: float


# Add to JobDetailResponse class

class JobDetailResponse(BaseModel):
    occ_code: str
    occ_title: str
    basic_info: JobBasicInfo
    metrics: List[JobMetric]
    skills: List[JobSkill]
    tech_skills: List[JobSkill]
    soft_skills: List[JobSkill]
    activities: List[JobActivity]
    abilities: List[JobAbility]
    knowledge: List[JobKnowledge]
    education: Optional[JobEducation] = None
    tools: List[JobSkill]
    work_activities: List[JobActivity]
    related_occupations: Optional[List[Dict[str, str]]] = None
    industry: Optional[Dict[str, Any]] = None  # Add this field

    
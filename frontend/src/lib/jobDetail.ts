import { apiGet } from "./http";

export type JobBasicInfo = {
  occ_code: string;
  occ_title: string;
  description?: string;
  soc_code?: string;
};

export type JobMetric = {
  title: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  trend?: { 
    value: number; 
    direction: "up" | "down" | "neutral";
  };
  color?: "cyan" | "coral" | "purple" | "green" | "amber";
  format?: "fmtK" | "fmtM" | "fmtPercent";
};

export type JobSkill = {
  name: string;
  value: number;
  type: "tech" | "soft" | "general" | "skill" | "tool";
  commodity_title?: string;
  hot_technology?: boolean;
  in_demand?: boolean;
};

export type JobActivity = {
  name: string;
  value: number;
  element_id?: string;
};

export type JobAbility = {
  name: string;
  category: string;
  value: number;
  element_id?: string;
};

export type JobKnowledge = {
  name: string;
  level: "Basic" | "Intermediate" | "Advanced" | "Expert";
  value: number;
};

export type JobEducation = {
  category: number;
  description: string;
  required_level: string;
  value: number;
};

export type JobDetailResponse = {
  occ_code: string;
  occ_title: string;
  basic_info: JobBasicInfo;
  metrics: JobMetric[];
  skills: JobSkill[];
  tech_skills: JobSkill[];
  soft_skills: JobSkill[];
  activities: JobActivity[];
  abilities: JobAbility[];
  knowledge: JobKnowledge[];
  education: JobEducation | null;
  tools: JobSkill[];
  work_activities: JobActivity[];
  related_occupations?: Array<{ soc_code: string; title: string }>;
};

export const JobDetailAPI = {
  get: (occ_code: string) =>
    apiGet<JobDetailResponse>(`/job-detail/${encodeURIComponent(occ_code)}`),

  getSkills: (occ_code: string, limit = 20) =>
    apiGet<JobSkill[]>(`/job-detail/${encodeURIComponent(occ_code)}/skills`, { limit }),

  getTechSkills: (occ_code: string) =>
    apiGet<JobSkill[]>(`/job-detail/${encodeURIComponent(occ_code)}/technology-skills`),

  getAbilities: (occ_code: string, limit = 10) =>
    apiGet<JobAbility[]>(`/job-detail/${encodeURIComponent(occ_code)}/abilities`, { limit }),

  getKnowledge: (occ_code: string, limit = 10) =>
    apiGet<JobKnowledge[]>(`/job-detail/${encodeURIComponent(occ_code)}/knowledge`, { limit }),
};
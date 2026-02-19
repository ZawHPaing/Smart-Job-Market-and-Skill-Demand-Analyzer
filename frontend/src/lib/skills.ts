import { apiGet } from "./http";

export type SkillMetric = {
  title: string;
  value: number | string;
  suffix?: string;
  prefix?: string;
  trend?: { value: number; direction: "up" | "down" | "neutral" };
  color: "cyan" | "purple" | "coral" | "green" | "amber";
  format?: string;
};

export type SkillBasicInfo = {
  skill_id: string;
  skill_name: string;
  skill_type: string;
  classification: string[];
  description?: string;
};

export type SkillUsageData = {
  name: string;
  value: number;
  color: string;
};

export type CoOccurringSkill = {
  id: string;
  name: string;
  type: string;
  frequency: number;
  co_occurrence_rate?: number;
  demand_trend?: number;
  salary_association?: number;
  // All fields properly defined
  usage_count?: number;
  avg_importance?: number;
  avg_level?: number;
  hot_technology?: boolean;
  in_demand?: boolean;
};

export type JobRequiringSkill = {
  title: string;
  soc_code: string;
  importance: number;
  level?: number;
  median_salary?: number;
  employment?: number;
  hot_technology?: boolean;
  in_demand?: boolean;
};

export type NetworkNode = {
  id: string;
  name: string;
  group: string;
  value: number;
  usage_count?: number;
  co_occurrence_rate?: number;
  avg_importance?: number;
  avg_level?: number;
};

export type NetworkLink = {
  source: string;
  target: string;
  value: number;
  co_occurrence_rate?: number;
};

export type NetworkGraph = {
  nodes: NetworkNode[];
  links: NetworkLink[];
};

export type SkillDetailResponse = {
  basic_info: SkillBasicInfo;
  metrics: SkillMetric[];
  usage_data: SkillUsageData[];
  usage_percentage: number;
  co_occurring_skills: CoOccurringSkill[];
  top_jobs: JobRequiringSkill[];
  total_jobs_count: number;
  network_graph?: NetworkGraph;
};

export type SkillSearchResult = {
  id: string;
  name: string;
  type: string;
  job_count: number;
};

export const SkillsAPI = {
  // Get complete skill details
  getDetail: (skillId: string) =>
    apiGet<SkillDetailResponse>(`/skills/${encodeURIComponent(skillId)}`),

  // Search skills
  search: (query: string, limit = 10) =>
    apiGet<SkillSearchResult[]>("/skills/search", { q: query, limit }),

  // Get top jobs for skill
  getJobs: (skillId: string, limit = 10) =>
    apiGet<JobRequiringSkill[]>(`/skills/${encodeURIComponent(skillId)}/jobs`, { limit }),

  // Get co-occurring skills
  getCoOccurring: (skillId: string, limit = 6) =>
    apiGet<CoOccurringSkill[]>(`/skills/${encodeURIComponent(skillId)}/co-occurring`, { limit }),
};
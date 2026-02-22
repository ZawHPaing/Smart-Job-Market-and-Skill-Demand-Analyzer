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
  usage_count?: number;
  avg_importance?: number;
  avg_level?: number;
  hot_technology?: boolean;
  in_demand?: boolean;
  // Lift and correlation fields
  lift?: number;              // Lift value (>1 = positive correlation)
  chi_square?: number;        // Chi-square statistic
  is_significant?: boolean;   // Whether correlation is statistically significant
  correlation_type?: string;   // 'strong_positive', 'moderate_positive', 'neutral', 'moderate_negative', 'strong_negative'
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
  lift?: number;              // Lift value for the node
  is_significant?: boolean;   // Significance flag for the node
};

export type NetworkLink = {
  source: string;
  target: string;
  value: number;
  co_occurrence_rate?: number;
  lift?: number;              // Lift value for the link
  is_significant?: boolean;   // Significance flag for the link
};

export type NetworkGraph = {
  nodes: NetworkNode[];
  links: NetworkLink[];
};

export type CorrelationSummary = {
  total_correlations: number;
  avg_lift: number;
  max_lift: number;
  min_lift: number;
  significant_count: number;
  correlation_types: {
    strong_positive: number;
    moderate_positive: number;
    neutral: number;
    moderate_negative: number;
    strong_negative: number;
  };
};

export type CorrelationAnalysis = {
  correlations: CoOccurringSkill[];
  summary: CorrelationSummary;
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
  correlation_analysis?: CorrelationAnalysis;
  year?: number;
};

export type SkillSearchResult = {
  id: string;
  name: string;
  type: string;
  job_count: number;
};

export const SkillsAPI = {
  // Get complete skill details with required year
  getDetail: (skillId: string, year: number) => {
    // The API might expect the skill name as a query parameter, not in the path
    // Try both formats - first as path parameter, if that fails, the API route will handle it
    return apiGet<SkillDetailResponse>(`/skills/${encodeURIComponent(skillId)}`, { year });
  },

  // Alternative: If the API expects skill name as query param
  // getDetail: (skillId: string, year: number) => {
  //   return apiGet<SkillDetailResponse>("/skills", { skill_name: skillId, year });
  // },

  // Search skills
  search: (query: string, limit = 10) =>
    apiGet<SkillSearchResult[]>("/skills/search", { q: query, limit }),

  // Get top jobs for skill with required year
  getJobs: (skillId: string, year: number, limit = 10) => {
    return apiGet<JobRequiringSkill[]>(`/skills/${encodeURIComponent(skillId)}/jobs`, { year, limit });
  },

  // Get co-occurring skills
  getCoOccurring: (skillId: string, limit = 6) =>
    apiGet<CoOccurringSkill[]>(`/skills/${encodeURIComponent(skillId)}/co-occurring`, { limit }),
};
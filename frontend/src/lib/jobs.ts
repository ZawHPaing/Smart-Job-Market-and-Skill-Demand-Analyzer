import { apiGet } from "./http";

/**
 * Backend response shapes matching Pydantic models
 */
export type JobItem = {
  occ_code: string;
  occ_title: string;
  total_employment: number;
  a_median: number | null;
  group: string | null;
  jobs_percent?: number | null;
};

export type JobListResponse = {
  year: number;
  count: number;
  jobs: JobItem[];
};

export type JobDetailMetrics = {
  occ_code: string;
  occ_title: string;
  year: number;
  total_employment: number;
  a_median: number | null;
  group: string | null;
  naics: string | null;
  naics_title: string | null;
};

export type JobYearPoint = {
  year: number;
  total_employment: number;
  a_median: number | null;
};

export type JobSummaryResponse = {
  occ_code: string;
  occ_title: string;
  year_from: number;
  year_to: number;
  naics: string | null;
  naics_title: string | null;
  series: JobYearPoint[];
};

export type TopGrowingJob = {
  occ_code: string;
  occ_title: string;
  growth_pct: number;
};

export type JobDashboardMetrics = {
  year: number;
  total_jobs: number;
  total_employment: number;
  avg_job_growth_pct: number;
  top_growing_job: TopGrowingJob | null;
  a_median: number;
};

export type JobCard = {
  occ_code: string;
  occ_title: string;
  total_employment: number;
  a_median: number | null;
  growth_pct?: number | null;
  group: string | null;
};

export type JobTopResponse = {
  year: number;
  by: "employment" | "salary";
  limit: number;
  group: string | null;
  jobs: JobCard[];
};

export type JobTrendPoint = {
  year: number;
  employment: number;
};

export type JobTrendSeries = {
  occ_code: string;
  occ_title: string;
  points: JobTrendPoint[];
};

export type JobSalaryTrendPoint = {
  year: number;
  salary: number;
};

export type JobSalaryTrendSeries = {
  occ_code: string;
  occ_title: string;
  points: JobSalaryTrendPoint[];
};

export type JobTopTrendsResponse = {
  year_from: number;
  year_to: number;
  limit: number;
  series: JobTrendSeries[];
};

export type JobTopCombinedResponse = {
  year: number;
  by: "employment" | "salary";
  limit: number;
  group: string | null;
  top_jobs: JobCard[];
  employment_trends: JobTrendSeries[];
  salary_trends: JobSalaryTrendSeries[];
};

export type JobGroupItem = {
  group: string;
};

export type JobGroupsResponse = {
  year: number;
  groups: JobGroupItem[];
};

export type JobCompositionRow = {
  group: string;
  employment: number;
  avg_salary: number;
};

export type JobCompositionResponse = {
  year: number;
  rows: JobCompositionRow[];
};

export type JobSalaryDistribution = {
  year: number;
  group: string | null;
  total_jobs: number;
  q1: number;
  median: number;
  q3: number;
  min: number;
  max: number;
};

export type JobIndustryJob = {
  occ_code: string;
  occ_title: string;
  employment: number;
  a_median: number | null;
};

export type JobIndustryJobsResponse = {
  naics: string;
  naics_title: string;
  year: number;
  count: number;
  jobs: JobIndustryJob[];
};

/**
 * Jobs API client - mirrors IndustriesAPI structure
 */
export const JobsAPI = {
  // List jobs with pagination and search
  list: (params?: {
    year?: number;
    group?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => apiGet<JobListResponse>("/jobs/", params),

  // Quick search for autocomplete
  search: (q: string, year?: number, limit = 20) =>
    apiGet<JobItem[]>("/jobs/search", { q, year, limit }),

  // Dashboard metrics
  dashboardMetrics: (year: number) =>
    apiGet<JobDashboardMetrics>(`/jobs/metrics/${year}`),

  // Job groups (SOC categories)
  groups: (year: number) =>
    apiGet<JobGroupsResponse>(`/jobs/groups/${year}`),

  // Top jobs
  top: (year: number, limit = 10, by: "employment" | "salary" = "employment", group?: string) =>
    apiGet<JobTopResponse>("/jobs/top", { year, limit, by, group }),

  // Top jobs employment trends over time
  topTrends: (year_from = 2011, year_to = 2024, limit = 10, group?: string, sort_by: "employment" | "salary" = "employment") =>
    apiGet<JobTopTrendsResponse>("/jobs/top-trends", { year_from, year_to, limit, group, sort_by }),

  // Top jobs salary trends over time
  topSalaryTrends: (year_from = 2011, year_to = 2024, limit = 10, group?: string, sort_by: "employment" | "salary" = "employment") =>
    apiGet<JobTopTrendsResponse>("/jobs/top-salary-trends", { year_from, year_to, limit, group, sort_by }),

  // Combined top jobs data with both trends
  topCombined: (year: number, limit = 10, by: "employment" | "salary" = "employment", group?: string) =>
    apiGet<JobTopCombinedResponse>("/jobs/top-combined", { year, limit, by, group }),

  // Job composition by SOC group
  composition: (year: number) =>
    apiGet<JobCompositionResponse>(`/jobs/composition/${year}`),

  // Salary distribution (quartiles)
  salaryDistribution: (year: number, group?: string) =>
    apiGet<JobSalaryDistribution>("/jobs/salary-distribution/" + year, group ? { group } : undefined),

  // Single job metrics
  metrics: (occ_code: string, year: number, naics?: string) =>
    apiGet<JobDetailMetrics>(`/jobs/${encodeURIComponent(occ_code)}/metrics`, { year, naics }),

  // Job time series summary
  summary: (occ_code: string, year_from = 2011, year_to = 2024, naics?: string) =>
    apiGet<JobSummaryResponse>(`/jobs/${encodeURIComponent(occ_code)}/summary`, {
      year_from,
      year_to,
      naics,
    }),

  // Jobs within a specific industry
  jobsInIndustry: (naics: string, year: number, limit = 200, offset = 0) =>
    apiGet<JobIndustryJobsResponse>(`/jobs/industry/${encodeURIComponent(naics)}/jobs`, {
      year,
      limit,
      offset,
    }),
};
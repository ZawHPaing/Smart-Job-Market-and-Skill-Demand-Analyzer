import { apiGet } from "./http";

/** Backend response shapes (match your Pydantic models) */
export type IndustryItem = { naics: string; naics_title: string };

export type IndustryListResponse = {
  year: number;
  count: number;
  industries: IndustryItem[];
};

export type IndustryDashboardMetrics = {
  year: number;
  total_industries: number;
  total_employment: number;
  avg_industry_growth_pct: number;
  top_growing_industry: null | { naics: string; naics_title: string; growth_pct: number };
  median_industry_salary: number;
};

export type JobDetail = {
  occ_code: string;
  occ_title: string;
  employment: number;
  median_salary: number | null;
};

export type IndustryTopJobsResponse = {
  naics: string;
  naics_title: string;
  year: number;
  limit: number;
  jobs: JobDetail[];
};

export type IndustryJobsResponse = {
  naics: string;
  naics_title: string;
  year: number;
  count: number;
  jobs: JobDetail[];
};

export type IndustryDetailMetrics = {
  naics: string;
  naics_title: string;
  year: number;
  total_employment: number;
  median_salary: number;
};

export type IndustrySummaryPoint = {
  year: number;
  total_employment: number;
  median_salary: number;
};

export type IndustrySummaryResponse = {
  naics: string;
  naics_title: string;
  year_from: number;
  year_to: number;
  series: IndustrySummaryPoint[];
};

/* ----------------- NEW (Top / Trends / Composition) ----------------- */

export type IndustryCard = {
  naics: string;
  naics_title: string;
  total_employment: number;
  median_salary: number;
  growth_pct?: number | null;
};

export type IndustryTopResponse = {
  year: number;
  by: "employment" | "salary";
  limit: number;
  industries: IndustryCard[];
};

export type IndustryTrendPoint = { year: number; employment: number };

export type IndustryTrendSeries = {
  naics: string;
  naics_title: string;
  points: IndustryTrendPoint[];
};

export type IndustryTopTrendsResponse = {
  year_from: number;
  year_to: number;
  limit: number;
  series: IndustryTrendSeries[];
};

export type IndustryCompositionRow = {
  industry: string;
  juniorRoles: number;
  midRoles: number;
  seniorRoles: number;
};

export type IndustryCompositionResponse = {
  year: number;
  limit: number;
  rows: IndustryCompositionRow[];
};

export type IndustryTopOccRow = {
  industry: string;
  occ1_emp: number;
  occ2_emp: number;
  occ3_emp: number;
};

export type IndustryTopOccLegendItem = {
  key: "occ1_emp" | "occ2_emp" | "occ3_emp";
  name: string;
};

export type IndustryTopOccCompositionResponse = {
  year: number;
  industries_limit: number;
  top_n_occ: number;
  rows: IndustryTopOccRow[];
  legend: IndustryTopOccLegendItem[];
};


/** Calls */
export const IndustriesAPI = {
  // existing
  list: (year?: number) =>
    apiGet<IndustryListResponse>("/industries/", year ? { year } : undefined),

  dashboardMetrics: (year: number) =>
    apiGet<IndustryDashboardMetrics>(`/industries/metrics/${year}`),

  industryMetrics: (naics: string, year: number) =>
    apiGet<IndustryDetailMetrics>(`/industries/${encodeURIComponent(naics)}/metrics`, { year }),

  topJobs: (naics: string, year: number, limit = 6) =>
    apiGet<IndustryTopJobsResponse>(`/industries/${encodeURIComponent(naics)}/top-jobs`, { year, limit }),

  jobs: (naics: string, year: number, limit = 200) =>
    apiGet<IndustryJobsResponse>(`/industries/${encodeURIComponent(naics)}/jobs`, { year, limit }),

  summary: (naics: string, year_from = 2011, year_to = 2024) =>
    apiGet<IndustrySummaryResponse>(`/industries/${encodeURIComponent(naics)}/summary`, { year_from, year_to }),

  // ✅ new endpoints (require backend routes)
  top: (year: number, limit = 6, by: "employment" | "salary" = "employment") =>
    apiGet<IndustryTopResponse>("/industries/top", { year, limit, by }),

  topTrends: (year_from = 2019, year_to = 2024, limit = 10) =>  // Changed from 3 to 10
  apiGet<IndustryTopTrendsResponse>("/industries/top-trends", { year_from, year_to, limit }),

  composition: (year: number, limit = 6) =>
    apiGet<IndustryCompositionResponse>("/industries/composition", { year, limit }),

  compositionTopOccupations: (year: number, industries_limit = 6, top_n_occ = 3) =>
  apiGet<IndustryTopOccCompositionResponse>("/industries/composition-top-occupations", {
    year,
    industries_limit,
    top_n_occ,
  }),
};

import { apiGet } from "./http";

export type HomeOverviewResponse = {
  year: number;
  totalJobs: number;
  uniqueIndustries: number;
  uniqueJobs: number;
  medianSalary: number;
};

export type DonutItem = { name: string; value: number };
export type HomeIndustryDistributionResponse = { year: number; items: DonutItem[] };

export type TopJobItem = { name: string; postings: number; salary: number };
export type HomeTopJobsResponse = { year: number; items: TopJobItem[] };

export type TrendLineMeta = { key: string; name: string };
export type HomeEmploymentTrendsResponse = {
  year_from: number;
  year_to: number;
  limit: number;
  lines: TrendLineMeta[];
  rows: Record<string, number>[];
};

export type MarketTickerItem = {
  name: string;
  value: string;
  trend: "up" | "down" | "neutral";
};

export type MarketTickerResponse = {
  year: number;
  items: MarketTickerItem[];
};

export const HomeAPI = {
  overview: (year = 2024) => apiGet<HomeOverviewResponse>("/home/overview", { year }),
  industryDistribution: (year = 2024, limit = 8) =>
    apiGet<HomeIndustryDistributionResponse>("/home/industry-distribution", { year, limit }),
  topJobs: (year = 2024, limit = 8) =>
    apiGet<HomeTopJobsResponse>("/home/top-jobs", { year, limit }),
  employmentTrends: (year_from = 2019, year_to = 2024, limit = 3) =>
    apiGet<HomeEmploymentTrendsResponse>("/home/employment-trends", { year_from, year_to, limit }),
  marketTicker: (year = 2024) =>
    apiGet<MarketTickerResponse>("/home/market-ticker", { year }),
};

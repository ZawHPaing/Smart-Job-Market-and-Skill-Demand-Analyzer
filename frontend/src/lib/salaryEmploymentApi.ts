import { apiGet } from "./http";

export type TrendDirection = "up" | "down" | "neutral";

export type MetricColor = "cyan" | "coral" | "purple" | "green" | "amber";

export type MetricItem = {
  title: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  trend?: { value: number; direction: TrendDirection };
  color?: MetricColor;
};

export type MetricsResponse = {
  year: number;
  metrics: MetricItem[];
};

export type BarPoint = {
  name: string;
  value: number;
  secondaryValue: number;
};

export type IndustryBarResponse = {
  year: number;
  items: BarPoint[];
};

export type IndustryRow = {
  id: string; // naics
  name: string; // naics_title
  employment: number;
  medianSalary: number;
  trend: number;
};

export type PagedIndustries = {
  year: number;
  page: number;
  page_size: number;
  total: number;
  items: IndustryRow[];
};

export type JobRow = {
  occ_code: string;
  occ_title: string;
  employment: number;
  medianSalary: number;
  trend: number;
};

export type PagedJobs = {
  year: number;
  page: number;
  page_size: number;
  total: number;
  items: JobRow[];
};

export type IndustrySalaryTimeSeriesResponse = {
  series: { key: string; name: string; points: { year: number; value: number }[] }[];
};

export type JobEmploymentTimeSeriesResponse = {
  series: { key: string; name: string; points: { year: number; value: number }[] }[];
};

// ✅ normalize backend "flat" -> UI "neutral"
function normalizeMetrics(metrics: any[]): MetricItem[] {
  return (metrics || []).map((m) => ({
    ...m,
    trend: m.trend
      ? {
          ...m.trend,
          direction: m.trend.direction === "flat" ? "neutral" : m.trend.direction,
        }
      : undefined,
  }));
}

export async function getSalaryEmploymentMetrics(year?: number) {
  const res = await apiGet<MetricsResponse>(
    "/salary-employment/metrics",
    year ? { year } : {}
  );
  return { ...res, metrics: normalizeMetrics((res as any).metrics ?? []) };
}

export async function getIndustriesBar(params: { year?: number; search?: string; limit?: number }) {
  return apiGet<IndustryBarResponse>("/salary-employment/industries/bar", params);
}

export async function getIndustriesTable(params: {
  year?: number;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: "employment" | "salary" | "name";
  sort_dir?: -1 | 1;
}) {
  return apiGet<PagedIndustries>("/salary-employment/industries", params);
}

export async function getJobsTable(params: {
  year?: number;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: "employment" | "salary" | "name";
  sort_dir?: -1 | 1;
}) {
  return apiGet<PagedJobs>("/salary-employment/jobs", params);
}

export async function getIndustrySalaryTimeSeries(params: {
  names: string[];
  start_year?: number;
  end_year?: number;
}) {
  return apiGet<IndustrySalaryTimeSeriesResponse>(
    "/salary-employment/industries/salary-timeseries",
    params
  );
}

export async function getJobEmploymentTimeSeries(params: {
  year?: number;
  limit?: number;
  start_year?: number;
  end_year?: number;
}) {
  return apiGet<JobEmploymentTimeSeriesResponse>(
    "/salary-employment/jobs/employment-timeseries",
    params
  );
}

export async function getTopCrossIndustryJobs(params: { year?: number; limit?: number }) {
  return apiGet<{ year: number; items: { name: string; value: number; secondaryValue: number }[] }>(
    "/salary-employment/jobs/top-cross-industry",
    params
  );
}

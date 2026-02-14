import { apiGet } from "./http";

export type ForecastMetric = {
  title: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  trend?: { value: number; direction: "up" | "down" | "neutral" };
  color: string;
};

export type IndustryCompositionItem = {
  industry: string;
  current: number;
  forecast: number;
};

export type EmploymentForecastItem = {
  year: number;
  [key: string]: number;
};

export type TopJobForecast = {
  name: string;
  value: number;
  growth: number;
};

export type IndustryDetail = {
  industry: string;
  current: number;
  forecast: number;
  change: number;
  confidence: string;
};

export type ForecastResponse = {
  forecast_year: number;
  metrics: ForecastMetric[];
  industry_composition: IndustryCompositionItem[];
  employment_forecast: EmploymentForecastItem[];
  top_jobs_forecast: TopJobForecast[];
  industry_details: IndustryDetail[];
  confidence_level: string;
  disclaimer: string;
};

export const ForecastAPI = {
  // Get complete forecast for a specific year
  get: (year: number = 2025) =>
    apiGet<ForecastResponse>("/forecast/", { year }),

  // Get forecasts for top industries
  getIndustryForecasts: (limit: number = 6, forecastYears: number = 4) =>
    apiGet("/forecast/industries", { limit, forecast_years: forecastYears }),

  // Get forecasts for top jobs
  getJobForecasts: (limit: number = 8, forecastYears: number = 4) =>
    apiGet("/forecast/jobs", { limit, forecast_years: forecastYears }),

  // Get forecast for a specific industry
  getIndustryForecast: (naics: string, industryTitle?: string, forecastYears: number = 4) =>
    apiGet(`/forecast/industry/${naics}`, { 
      industry_title: industryTitle, 
      forecast_years: forecastYears 
    }),

  // Get forecast for a specific job
  getJobForecast: (occCode: string, jobTitle?: string, forecastYears: number = 4) =>
    apiGet(`/forecast/job/${occCode}`, { 
      job_title: jobTitle, 
      forecast_years: forecastYears 
    }),
};
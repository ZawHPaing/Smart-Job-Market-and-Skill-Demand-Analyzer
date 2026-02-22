// frontend/src/lib/search.ts (new file)
import { apiGet } from "./http";

export type UnifiedJobResult = {
  occ_code: string;
  occ_title: string;
  total_employment?: number;
  a_median?: number;
  group?: string;
};

export type UnifiedIndustryResult = {
  naics: string;
  naics_title: string;
  total_employment?: number;
};

export type UnifiedSkillResult = {
  id: string;
  name: string;
  type: string;
  job_count: number;
};

export type UnifiedSearchResponse = {
  jobs: UnifiedJobResult[];
  industries: UnifiedIndustryResult[];
  skills: UnifiedSkillResult[];
};

export const SearchAPI = {
  // Unified search across all categories
  unified: (query: string, limit = 5, year = 2024) =>
    apiGet<UnifiedSearchResponse>("/search", { q: query, limit, year }),
  
  // Category-specific searches
  jobs: (query: string, limit = 10, year = 2024) =>
    apiGet<UnifiedJobResult[]>("/search/jobs", { q: query, limit, year }),
  
  industries: (query: string, limit = 10, year = 2024) =>
    apiGet<UnifiedIndustryResult[]>("/search/industries", { q: query, limit, year }),
  
  skills: (query: string, limit = 10) =>
    apiGet<UnifiedSkillResult[]>("/search/skills", { q: query, limit }),
};
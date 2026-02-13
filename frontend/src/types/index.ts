// Job Market Analytics Dashboard - Type Definitions

export interface MetricCard {
  id: string;
  title: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
  icon?: string;
  color?: 'cyan' | 'coral' | 'purple' | 'green' | 'amber';
}

export interface Industry {
  id: string;
  name: string;
  totalJobs: number;
  employment: number;
  trend: number;
  medianSalary: number;
  topJobs: JobTitle[];
  yearlyData: YearlyDataPoint[];
}

export interface JobTitle {
  id: string;
  title: string;
  postings: number;
  salary: number;
  industryId?: string;
  trend: number;
  experienceRequired: string;
  skillIntensity: number;
  skills: Skill[];
  activities: Activity[];
  knowledge: Knowledge[];
  abilities: Ability[];
}

export interface Skill {
  id: string;
  name: string;
  type: 'tech' | 'soft' | 'general';
  importance: number;
  proficiency: number;
  demandTrend: number;
  salaryAssociation: number;
  coOccurringSkills: string[];
  jobsRequiring: number;
}

export interface Activity {
  id: string;
  name: string;
  importance: number;
  frequency: number;
}

export interface Knowledge {
  id: string;
  name: string;
  importance: number;
  level: string;
}

export interface Ability {
  id: string;
  name: string;
  importance: number;
  category: string;
}

export interface YearlyDataPoint {
  year: number;
  employment: number;
  salary: number;
  postings: number;
}

export interface SalaryEmploymentData {
  industry: string;
  employment: number;
  salary: number;
}

export interface TrendForecast {
  year: number;
  metric: string;
  value: number;
  confidence: number;
}

export interface ChartDataPoint {
  name: string;
  value: number;
  secondaryValue?: number;
  color?: string;
}

export interface TimeSeriesData {
  date: string;
  series: {
    name: string;
    value: number;
  }[];
}

export interface NetworkNode {
  id: string;
  name: string;
  value: number;
  group: string;
}

export interface NetworkLink {
  source: string;
  target: string;
  value: number;
}

export interface NetworkGraphData {
  nodes: NetworkNode[];
  links: NetworkLink[];
}

export interface SearchResult {
  id: string;
  type: 'industry' | 'job' | 'skill';
  name: string;
  description?: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export interface FilterState {
  year: number;
  industry?: string;
  jobTitle?: string;
  skill?: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

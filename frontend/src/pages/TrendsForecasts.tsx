import { useEffect, useState, useMemo } from 'react';
import { Calendar, TrendingUp, AlertCircle, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ForecastAPI } from '@/lib/forecast';
import type { ForecastResponse } from '@/lib/forecast';

const PAGE_SIZE = 10;
const FORECAST_YEARS = [2025, 2026, 2027, 2028];

// Helper functions - only used for chart formatting, not for metrics
const fmtK = (n: number) => {
  if (n >= 1000) {
    return `${Math.round(n / 1000)}K`;
  }
  return n.toString();
};

const fmtM = (n: number) => {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1)}M`;
  } else if (n >= 1000) {
    return `${(n / 1000).toFixed(0)}K`;
  }
  return n.toString();
};

// Extended chart colors for 10 items
const CHART_COLORS = [
  'hsl(186 100% 50%)', // cyan
  'hsl(0 100% 71%)',   // coral
  'hsl(258 90% 76%)',  // purple
  'hsl(142 76% 45%)',  // green
  'hsl(38 92% 50%)',   // amber
  'hsl(330 85% 60%)',  // pink
  'hsl(215 90% 60%)',  // blue
  'hsl(55 92% 55%)',   // yellow
  'hsl(280 70% 65%)',  // lavender
  'hsl(190 90% 55%)',  // teal
];

const TrendsForecasts = () => {
  const [forecastYear, setForecastYear] = useState(2025);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);

  // Pagination states
  const [jobsPage, setJobsPage] = useState(1);
  const [industriesPage, setIndustriesPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadForecast() {
      setLoading(true);
      setError(null);

      try {
        console.log('🟡 Loading forecast for year:', forecastYear);
        const data = await ForecastAPI.get(forecastYear);
        if (cancelled) return;
        
        setForecastData(data);
        // Reset pagination when forecast year changes
        setJobsPage(1);
        setIndustriesPage(1);
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || 'Failed to load forecast data');
        console.error('🔴 Forecast error:', e);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    }

    loadForecast();
    return () => { cancelled = true; };
  }, [forecastYear]);

  // Transform metrics for MetricsGrid - PASS RAW NUMBERS
  const metrics = useMemo(() => {
    if (!forecastData?.metrics) return [];
    
    return forecastData.metrics.map(m => {
      return {
        title: m.title,
        value: m.value,
        prefix: m.prefix,
        suffix: m.suffix,
        trend: m.trend ? {
          value: Math.abs(m.trend.value),
          direction: m.trend.direction as "up" | "down" | "neutral"
        } : undefined,
        color: m.color as "cyan" | "purple" | "green" | "coral" | "amber"
      };
    });
  }, [forecastData]);

  // Transform employment forecast data for MultiLineChart
  const employmentChartData = useMemo(() => {
    if (!forecastData?.employment_forecast?.length) {
      return [];
    }
    
    const industries = forecastData.industry_details
      ?.slice(0, 10)
      .map(i => i.industry) || [];
    
    return forecastData.employment_forecast.map(item => ({
      year: item.year,
      ...industries.reduce((acc, industry) => {
        acc[industry] = item[industry] || 0;
        return acc;
      }, {} as Record<string, number>)
    }));
  }, [forecastData]);

  // Get top 10 industries for chart lines
  const lineColors = useMemo(() => {
    const industries = forecastData?.industry_details
      ?.slice(0, 10)
      .map(i => i.industry) || [];
    
    return industries.map((industry, index) => ({
      key: industry,
      name: industry.length > 25 ? industry.substring(0, 25) + '...' : industry,
      color: CHART_COLORS[index % CHART_COLORS.length]
    }));
  }, [forecastData]);

  // Filter and paginate jobs
  const filteredJobs = useMemo(() => {
    if (!forecastData?.top_jobs_forecast?.length) return [];
    
    let jobs = forecastData.top_jobs_forecast;
    
    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      jobs = jobs.filter(job => 
        job.name.toLowerCase().includes(query)
      );
    }
    
    return jobs;
  }, [forecastData, searchQuery]);

  const totalJobs = filteredJobs.length;
  const totalJobPages = Math.max(1, Math.ceil(totalJobs / PAGE_SIZE));
  
  // Get paginated jobs for current page
  const paginatedJobs = useMemo(() => {
    const start = (jobsPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    return filteredJobs.slice(start, end).map(job => ({
      ...job,
      valueDisplay: job.value >= 1_000_000 ? fmtM(job.value) : 
                    job.value >= 1000 ? fmtK(job.value) : 
                    job.value.toLocaleString()
    }));
  }, [filteredJobs, jobsPage]);

  // Filter and paginate industries
  const filteredIndustries = useMemo(() => {
    if (!forecastData?.industry_details?.length) return [];
    
    let industries = forecastData.industry_details;
    
    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      industries = industries.filter(ind => 
        ind.industry.toLowerCase().includes(query)
      );
    }
    
    return industries;
  }, [forecastData, searchQuery]);

  const totalIndustries = filteredIndustries.length;
  const totalIndustryPages = Math.max(1, Math.ceil(totalIndustries / PAGE_SIZE));
  
  // Get paginated industries for current page
  const paginatedIndustries = useMemo(() => {
    const start = (industriesPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    
    return filteredIndustries.slice(start, end).map(item => ({
      ...item,
      confidence_score: item.confidence_score,
      currentDisplay: item.current >= 1_000_000 ? fmtM(item.current) : 
                      item.current >= 1000 ? fmtK(item.current) : 
                      item.current.toLocaleString(),
      forecastDisplay: item.forecast >= 1_000_000 ? fmtM(item.forecast) : 
                       item.forecast >= 1000 ? fmtK(item.forecast) : 
                       item.forecast.toLocaleString(),
    }));
  }, [filteredIndustries, industriesPage]);

  // Reset to page 1 when search changes
  useEffect(() => {
    setJobsPage(1);
    setIndustriesPage(1);
  }, [searchQuery]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan"></div>
          <div className="text-muted-foreground">Loading forecast data...</div>
          <div className="text-xs text-muted-foreground">Using historical data from 2011-2024</div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !forecastData) {
    return (
      <DashboardLayout>
        <div className="space-y-4">
          <Card className="glass-card border-coral/30">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <AlertCircle className="h-5 w-5 text-coral shrink-0 mt-0.5" />
                <div>
                  <p className="text-coral font-semibold">Error Loading Forecast</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    {error || 'Unable to load forecast data. Please try again later.'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge className="bg-amber/20 text-amber border-amber/30">
                <Calendar className="h-3 w-3 mr-1" />
                Forecast {forecastYear}
              </Badge>
            </div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Trends & <span className="gradient-text">Forecasts</span>
            </h1>
            <p className="mt-1 text-muted-foreground">
              Forward-looking analytics based on 2011-2024 historical data
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => {
                const index = FORECAST_YEARS.indexOf(forecastYear);
                if (index > 0) setForecastYear(FORECAST_YEARS[index - 1]);
              }}
              disabled={forecastYear === 2025}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            
            {FORECAST_YEARS.map(year => (
              <Button
                key={year}
                variant={forecastYear === year ? 'default' : 'outline'}
                onClick={() => setForecastYear(year)}
                className={forecastYear === year ? 'bg-cyan text-background' : ''}
              >
                {year}
              </Button>
            ))}
            
            <Button
              variant="outline"
              size="icon"
              onClick={() => {
                const index = FORECAST_YEARS.indexOf(forecastYear);
                if (index < FORECAST_YEARS.length - 1) setForecastYear(FORECAST_YEARS[index + 1]);
              }}
              disabled={forecastYear === 2028}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search jobs or industries..."
            className="pl-10 bg-secondary/50"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Confidence Note */}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber/10 border border-amber/20">
          <AlertCircle className="h-5 w-5 text-amber shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium">Ensemble Forecast Model</p>
            <p className="text-sm text-muted-foreground">
              {forecastData.disclaimer} Confidence level: {forecastData.confidence_level}
            </p>
          </div>
        </div>

        {/* Key Metrics */}
        {metrics.length > 0 && <MetricsGrid metrics={metrics} />}

        {/* Full Width Employment Forecast Chart */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Est. Employment per Industry"
              subtitle={`Historical (2011-2024) with projections to ${forecastYear} (Top 10 industries)`}
            />
          </CardHeader>
          <CardContent>
            {employmentChartData.length > 0 && lineColors.length > 0 ? (
              <>
                <MultiLineChart
                  data={employmentChartData}
                  xAxisKey="year"
                  lines={lineColors}
                  height={450}
                  maxLines={10}
                />
                {/* Forecast indicator line */}
                <div className="flex items-center justify-center gap-2 mt-4 text-sm text-muted-foreground">
                  <div className="w-8 h-0.5 bg-muted-foreground/50" style={{ backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 4px, currentColor 4px, currentColor 8px)' }} />
                  <span>Projected values (2025-{forecastYear})</span>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-[450px] text-muted-foreground">
                No employment forecast data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Est. Top Jobs with Pagination */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title={`Est. Top Growing Jobs (${forecastYear})`}
              subtitle="Fastest growing job categories by projected demand"
            />
          </CardHeader>
          <CardContent>
            {paginatedJobs.length > 0 ? (
              <>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {paginatedJobs.map((job, index) => (
                    <div
                      key={job.name}
                      className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 transition-colors group"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <span className="text-xs text-muted-foreground">
                          #{(jobsPage - 1) * PAGE_SIZE + index + 1}
                        </span>
                        <div className="flex items-center gap-1 text-green-500 text-sm font-medium">
                          <TrendingUp className="h-3 w-3" />
                          +{job.growth}%
                        </div>
                      </div>
                      <h4 className="font-medium group-hover:text-cyan transition-colors">
                        {job.name}
                      </h4>
                      <p className="text-2xl font-bold text-cyan mt-2">
                        {job.valueDisplay}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Est. job postings in {forecastYear}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Pagination controls */}
                <div className="mt-6 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing {(jobsPage - 1) * PAGE_SIZE + 1} to {Math.min(jobsPage * PAGE_SIZE, totalJobs)} of {totalJobs} jobs
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={jobsPage <= 1}
                      onClick={() => setJobsPage(p => p - 1)}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Prev
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={jobsPage >= totalJobPages}
                      onClick={() => setJobsPage(p => p + 1)}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-32 text-muted-foreground">
                {searchQuery.trim() 
                  ? `No jobs found matching "${searchQuery.trim()}"`
                  : "No top jobs forecast data available"}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Industry Forecast Details with Pagination */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Industry Forecast Comparison"
              subtitle={`Industries sorted by projected job postings in ${forecastYear}`}
            />
          </CardHeader>
          <CardContent>
            {paginatedIndustries.length > 0 ? (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                          Industry
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          2024 (Actual)
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          {forecastYear} (Est.)
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Change
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Confidence Score
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Confidence Level
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedIndustries.map((row) => (
                        <tr
                          key={row.industry}
                          className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                        >
                          <td className="py-3 px-4 font-medium">{row.industry}</td>
                          <td className="py-3 px-4 text-right text-muted-foreground">
                            {row.currentDisplay}
                          </td>
                          <td className="py-3 px-4 text-right text-cyan font-medium">
                            {row.forecastDisplay}
                          </td>
                          <td
                            className={`py-3 px-4 text-right font-medium ${
                              row.change >= 0 ? 'text-green-500' : 'text-coral'
                            }`}
                          >
                            {row.change >= 0 ? '+' : ''}
                            {row.change}%
                          </td>
                          <td className={`py-3 px-4 text-right font-medium ${
                            row.confidence === 'High'
                              ? 'text-green-500'
                              : row.confidence === 'Medium'
                              ? 'text-amber'
                              : 'text-coral'
                          }`}>
                            {row.confidence_score}%
                          </td>
                          <td className="py-3 px-4 text-right">
                            <Badge
                              variant="outline"
                              className={
                                row.confidence === 'High'
                                  ? 'border-green-500/50 text-green-500'
                                  : row.confidence === 'Medium'
                                  ? 'border-amber/50 text-amber'
                                  : 'border-coral/50 text-coral'
                              }
                            >
                              {row.confidence}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination controls */}
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing {(industriesPage - 1) * PAGE_SIZE + 1} to {Math.min(industriesPage * PAGE_SIZE, totalIndustries)} of {totalIndustries} industries
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={industriesPage <= 1}
                      onClick={() => setIndustriesPage(p => p - 1)}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Prev
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={industriesPage >= totalIndustryPages}
                      onClick={() => setIndustriesPage(p => p + 1)}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-32 text-muted-foreground">
                {searchQuery.trim()
                  ? `No industries found matching "${searchQuery.trim()}"`
                  : "No industry details data available"}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default TrendsForecasts;
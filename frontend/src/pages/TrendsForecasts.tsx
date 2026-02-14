import { useEffect, useState, useMemo } from 'react';
import { Calendar, TrendingUp, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { StackedBarChart, MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ForecastAPI } from '@/lib/forecast';
import type { ForecastResponse } from '@/lib/forecast';

// Helper functions
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtM = (n: number) => `${(n / 1_000_000).toFixed(1)}M`;

const FORECAST_YEARS = [2025, 2026, 2027, 2028];

// Chart colors
const CHART_COLORS = {
  current: 'hsl(0 0% 40%)',
  forecast: 'hsl(186 100% 50%)',
  tech: 'hsl(186 100% 50%)',
  healthcare: 'hsl(0 100% 71%)',
  finance: 'hsl(258 90% 76%)',
  line1: 'hsl(186 100% 50%)',
  line2: 'hsl(0 100% 71%)',
  line3: 'hsl(258 90% 76%)'
};

const TrendsForecasts = () => {
  const [forecastYear, setForecastYear] = useState(2025);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);

  useEffect(() => {
  let cancelled = false;

  async function loadForecast() {
    setLoading(true);
    setError(null);

    try {
      console.log('🟡 Loading forecast for year:', forecastYear);
      const data = await ForecastAPI.get(forecastYear);
      if (cancelled) return;
      
      // 🔍 DEEP DEBUG: Log everything
      console.log('🔍 FULL FORECAST DATA:', JSON.stringify(data, null, 2));
      
      // Log specific sections
      console.log('🔍 industry_composition:', data.industry_composition);
      console.log('🔍 employment_forecast:', data.employment_forecast);
      console.log('🔍 top_jobs_forecast:', data.top_jobs_forecast);
      console.log('🔍 industry_details:', data.industry_details);
      
      // Check if arrays exist and have items
      console.log('🔍 industry_composition length:', data.industry_composition?.length);
      console.log('🔍 employment_forecast length:', data.employment_forecast?.length);
      console.log('🔍 top_jobs_forecast length:', data.top_jobs_forecast?.length);
      
      setForecastData(data);
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



  // Transform metrics for MetricsGrid
  const metrics = useMemo(() => {
    if (!forecastData?.metrics) return [];
    
    return forecastData.metrics.map(m => ({
      title: m.title,
      value: typeof m.value === 'number' 
        ? (m.title.includes('Total Employment') ? fmtM(m.value) : 
           m.title.includes('Salary') ? fmtK(m.value) : 
           m.value)
        : m.value,
      prefix: m.prefix,
      suffix: m.suffix,
      trend: m.trend ? {
        value: Math.abs(m.trend.value),
        direction: m.trend.direction as "up" | "down" | "neutral"
      } : undefined,
      color: m.color as "cyan" | "purple" | "green" | "coral" | "amber"
    }));
  }, [forecastData]);

  // Transform industry composition data for StackedBarChart
  const industryChartData = useMemo(() => {
    if (!forecastData?.industry_composition?.length) {
      // Return mock data if no real data
      return [
        { industry: 'Technology', current: 4200000, forecast: 4750000 },
        { industry: 'Healthcare', current: 5800000, forecast: 6350000 },
        { industry: 'Finance', current: 2900000, forecast: 3120000 },
        { industry: 'Retail', current: 2100000, forecast: 2420000 },
        { industry: 'Manufacturing', current: 1450000, forecast: 1320000 },
        { industry: 'Education', current: 1250000, forecast: 1400000 },
      ];
    }
    
    return forecastData.industry_composition.map(item => ({
      industry: item.industry,
      current: item.current || 0,
      forecast: item.forecast || 0
    }));
  }, [forecastData]);

  // Transform employment forecast data for MultiLineChart
  const employmentChartData = useMemo(() => {
    if (!forecastData?.employment_forecast?.length) {
      // Return mock data if no real data
      return [
        { year: 2022, tech: 3900000, healthcare: 5400000, finance: 2750000 },
        { year: 2023, tech: 4050000, healthcare: 5600000, finance: 2850000 },
        { year: 2024, tech: 4200000, healthcare: 5800000, finance: 2900000 },
        { year: 2025, tech: 4450000, healthcare: 6050000, finance: 3000000 },
        { year: 2026, tech: 4750000, healthcare: 6350000, finance: 3120000 },
      ];
    }
    
    // Get industry names from the data
    const industries = forecastData.industry_composition.map(i => i.industry);
    
    return forecastData.employment_forecast.map(item => ({
      year: item.year,
      [industries[0] || 'Technology']: item[industries[0]] || 0,
      [industries[1] || 'Healthcare']: item[industries[1]] || 0,
      [industries[2] || 'Finance']: item[industries[2]] || 0,
    }));
  }, [forecastData]);

  // Get line colors based on industries
  const lineColors = useMemo(() => {
    const industries = forecastData?.industry_composition.map(i => i.industry) || 
      ['Technology', 'Healthcare', 'Finance'];
    
    return industries.map((_, index) => ({
      key: industries[index],
      name: industries[index],
      color: index === 0 ? CHART_COLORS.line1 : 
             index === 1 ? CHART_COLORS.line2 : 
             CHART_COLORS.line3
    }));
  }, [forecastData]);

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

        {/* Confidence Note */}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber/10 border border-amber/20">
          <AlertCircle className="h-5 w-5 text-amber shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium">Prophet Forecast Model</p>
            <p className="text-sm text-muted-foreground">
              {forecastData.disclaimer} Confidence level: {forecastData.confidence_level}
            </p>
          </div>
        </div>

        {/* Key Metrics */}
        {metrics.length > 0 && <MetricsGrid metrics={metrics} />}

        {/* Charts */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Est. Job Composition by Industry */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title={`Est. Job Composition (${forecastYear})`}
                subtitle="Projected job postings by industry"
              />
            </CardHeader>
            <CardContent>
              {industryChartData.length > 0 ? (
                <StackedBarChart
                  data={industryChartData}
                  xAxisKey="industry"
                  bars={[
                    { key: 'current', name: '2024 (Actual)', color: CHART_COLORS.current },
                    { key: 'forecast', name: `${forecastYear} (Est.)`, color: CHART_COLORS.forecast },
                  ]}
                  height={350}
                />
              ) : (
                <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                  No industry composition data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Est. Employment Over Time */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Est. Employment per Industry"
                subtitle="Historical (2011-2024) with future projections"
              />
            </CardHeader>
            <CardContent>
              {employmentChartData.length > 0 ? (
                <>
                  <MultiLineChart
                    data={employmentChartData}
                    xAxisKey="year"
                    lines={lineColors}
                    height={350}
                  />
                  {/* Forecast indicator line */}
                  <div className="flex items-center justify-center gap-2 mt-4 text-sm text-muted-foreground">
                    <div className="w-8 h-0.5 bg-muted-foreground/50" style={{ backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 4px, currentColor 4px, currentColor 8px)' }} />
                    <span>Projected values (2025-{forecastYear})</span>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                  No employment forecast data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Est. Top Jobs */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title={`Est. Top Growing Jobs (${forecastYear})`}
              subtitle="Fastest growing job categories by projected demand"
            />
          </CardHeader>
          <CardContent>
            {forecastData.top_jobs_forecast?.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {forecastData.top_jobs_forecast.map((job, index) => (
                  <div
                    key={job.name}
                    className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 transition-colors group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-xs text-muted-foreground">#{index + 1}</span>
                      <div className="flex items-center gap-1 text-green-500 text-sm font-medium">
                        <TrendingUp className="h-3 w-3" />
                        +{job.growth}%
                      </div>
                    </div>
                    <h4 className="font-medium group-hover:text-cyan transition-colors">
                      {job.name}
                    </h4>
                    <p className="text-2xl font-bold text-cyan mt-2">
                      {job.value >= 1000 ? `${(job.value / 1000).toFixed(0)}K` : job.value}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Est. job postings in {forecastYear}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-muted-foreground">
                No top jobs forecast data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Industry Forecast Details */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Industry Forecast Comparison"
              subtitle="Current vs projected job postings"
            />
          </CardHeader>
          <CardContent>
            {forecastData.industry_details?.length > 0 ? (
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
                        Confidence
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecastData.industry_details.map((row) => (
                      <tr
                        key={row.industry}
                        className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                      >
                        <td className="py-3 px-4 font-medium">{row.industry}</td>
                        <td className="py-3 px-4 text-right text-muted-foreground">
                          {row.current.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right text-cyan font-medium">
                          {row.forecast.toLocaleString()}
                        </td>
                        <td
                          className={`py-3 px-4 text-right font-medium ${
                            row.change >= 0 ? 'text-green-500' : 'text-coral'
                          }`}
                        >
                          {row.change >= 0 ? '+' : ''}
                          {row.change}%
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
            ) : (
              <div className="flex items-center justify-center h-32 text-muted-foreground">
                No industry details data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};



export default TrendsForecasts;
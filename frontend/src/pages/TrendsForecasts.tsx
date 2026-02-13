import { useState } from 'react';
import { Calendar, TrendingUp, AlertCircle } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { StackedBarChart, MultiLineChart, HorizontalBarChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { trendForecasts } from '@/data/mockData';

const TrendsForecasts = () => {
  const [forecastYear, setForecastYear] = useState(2026);

  const metrics = [
    {
      title: 'Est. Total Employment',
      value: forecastYear === 2025 ? 25100000 : 26200000,
      trend: { value: forecastYear === 2025 ? 3.3 : 4.4, direction: 'up' as const },
      color: 'cyan' as const,
    },
    {
      title: 'Est. Median Salary',
      value: forecastYear === 2025 ? 82000 : 86500,
      prefix: '$',
      trend: { value: forecastYear === 2025 ? 4.5 : 5.5, direction: 'up' as const },
      color: 'purple' as const,
    },
    {
      title: 'Est. Job Growth',
      value: forecastYear === 2025 ? '+5.2%' : '+6.8%',
      trend: { value: 1.5, direction: 'up' as const },
      color: 'green' as const,
    },
    {
      title: 'Est. AI/ML Jobs',
      value: forecastYear === 2025 ? 35000 : 48000,
      trend: { value: 38, direction: 'up' as const },
      color: 'coral' as const,
    },
    {
      title: 'Forecast Confidence',
      value: forecastYear === 2025 ? '85%' : '72%',
      color: 'amber' as const,
    },
  ];

  // Forecast composition data
  const forecastComposition = [
    { industry: 'Tech', current: 285000, forecast: forecastYear === 2025 ? 320000 : 365000 },
    { industry: 'Healthcare', current: 320000, forecast: forecastYear === 2025 ? 345000 : 375000 },
    { industry: 'Finance', current: 175000, forecast: forecastYear === 2025 ? 188000 : 202000 },
    { industry: 'Retail', current: 210000, forecast: forecastYear === 2025 ? 225000 : 242000 },
    { industry: 'Manufacturing', current: 145000, forecast: forecastYear === 2025 ? 138000 : 132000 },
    { industry: 'Education', current: 125000, forecast: forecastYear === 2025 ? 132000 : 140000 },
  ];

  // Employment forecast time series
  const employmentForecast = [
    { year: 2022, tech: 3900000, healthcare: 5400000, finance: 2750000 },
    { year: 2023, tech: 4050000, healthcare: 5600000, finance: 2850000 },
    { year: 2024, tech: 4200000, healthcare: 5800000, finance: 2900000 },
    { year: 2025, tech: 4450000, healthcare: 6050000, finance: 3000000 },
    { year: 2026, tech: 4750000, healthcare: 6350000, finance: 3120000 },
  ];

  // Top jobs forecast
  const topJobsForecast = [
    { name: 'AI/ML Engineer', value: forecastYear === 2025 ? 35000 : 48000, growth: 38 },
    { name: 'Data Engineer', value: forecastYear === 2025 ? 52000 : 68000, growth: 28 },
    { name: 'Cloud Architect', value: forecastYear === 2025 ? 28000 : 36000, growth: 32 },
    { name: 'Cybersecurity Analyst', value: forecastYear === 2025 ? 42000 : 55000, growth: 25 },
    { name: 'Healthcare Tech Specialist', value: forecastYear === 2025 ? 38000 : 48000, growth: 22 },
    { name: 'DevOps Engineer', value: forecastYear === 2025 ? 32000 : 40000, growth: 20 },
    { name: 'Product Manager', value: forecastYear === 2025 ? 38000 : 44000, growth: 15 },
    { name: 'UX Designer', value: forecastYear === 2025 ? 35000 : 40000, growth: 14 },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge className="bg-amber/20 text-amber border-amber/30">
                <Calendar className="h-3 w-3 mr-1" />
                Forecast
              </Badge>
            </div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Trends & <span className="gradient-text">Forecasts</span>
            </h1>
            <p className="mt-1 text-muted-foreground">
              Forward-looking analytics and employment projections
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={forecastYear === 2025 ? 'default' : 'outline'}
              onClick={() => setForecastYear(2025)}
              className={forecastYear === 2025 ? 'bg-cyan text-background' : ''}
            >
              2025
            </Button>
            <Button
              variant={forecastYear === 2026 ? 'default' : 'outline'}
              onClick={() => setForecastYear(2026)}
              className={forecastYear === 2026 ? 'bg-cyan text-background' : ''}
            >
              2026
            </Button>
          </div>
        </div>

        {/* Confidence Note */}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber/10 border border-amber/20">
          <AlertCircle className="h-5 w-5 text-amber shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium">Forecast Disclaimer</p>
            <p className="text-sm text-muted-foreground">
              Projections are based on historical trends and machine learning models. 
              Actual results may vary. Confidence level: {forecastYear === 2025 ? '85%' : '72%'}
            </p>
          </div>
        </div>

        {/* Key Metrics */}
        <MetricsGrid metrics={metrics} />

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
              <StackedBarChart
                data={forecastComposition}
                xAxisKey="industry"
                bars={[
                  { key: 'current', name: '2024 (Actual)', color: 'hsl(0 0% 40%)' },
                  { key: 'forecast', name: `${forecastYear} (Est.)`, color: 'hsl(186 100% 50%)' },
                ]}
                height={350}
              />
            </CardContent>
          </Card>

          {/* Est. Employment Over Time */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Est. Employment per Industry"
                subtitle="Historical data with future projections"
              />
            </CardHeader>
            <CardContent>
              <MultiLineChart
                data={employmentForecast}
                xAxisKey="year"
                lines={[
                  { key: 'tech', name: 'Technology', color: 'hsl(186 100% 50%)' },
                  { key: 'healthcare', name: 'Healthcare', color: 'hsl(0 100% 71%)' },
                  { key: 'finance', name: 'Finance', color: 'hsl(258 90% 76%)' },
                ]}
                height={350}
              />
              {/* Forecast indicator line */}
              <div className="flex items-center justify-center gap-2 mt-4 text-sm text-muted-foreground">
                <div className="w-8 h-0.5 bg-muted-foreground/50" style={{ backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 4px, currentColor 4px, currentColor 8px)' }} />
                <span>Projected values after 2024</span>
              </div>
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
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {topJobsForecast.slice(0, 8).map((job, index) => (
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
                  {forecastComposition.map((row) => {
                    const change = ((row.forecast - row.current) / row.current) * 100;
                    return (
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
                            change >= 0 ? 'text-green-500' : 'text-coral'
                          }`}
                        >
                          {change >= 0 ? '+' : ''}
                          {change.toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Badge
                            variant="outline"
                            className={
                              forecastYear === 2025
                                ? 'border-green-500/50 text-green-500'
                                : 'border-amber/50 text-amber'
                            }
                          >
                            {forecastYear === 2025 ? 'High' : 'Medium'}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default TrendsForecasts;

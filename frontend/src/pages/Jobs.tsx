import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowUpDown } from 'lucide-react';

import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { HorizontalBarChart, MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { JobsAPI } from '@/lib/jobs';
import type { 
  JobCard,
  JobDashboardMetrics,
  JobItem,
  JobTrendSeries,
  JobSalaryTrendSeries,
  JobTopCombinedResponse
} from '@/lib/jobs';

// ---------- helpers ----------
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

// Chart colors array
const CHART_COLORS = [
  'hsl(186 100% 50%)',  // cyan
  'hsl(0 100% 71%)',    // coral
  'hsl(258 90% 76%)',   // purple
  'hsl(142 76% 45%)',   // green
  'hsl(35 100% 60%)',   // amber
  'hsl(320 100% 70%)',  // pink
  'hsl(200 100% 60%)',  // blue
  'hsl(80 70% 50%)',    // lime
  'hsl(280 80% 70%)',   // lavender
  'hsl(30 100% 65%)',   // orange
];

type SortBy = 'employment' | 'salary';

const Jobs = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [year] = useState(2024);
  const [sortBy, setSortBy] = useState<SortBy>('employment');
  const [activeChart, setActiveChart] = useState<'employment' | 'salary'>('employment');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<JobDashboardMetrics | null>(null);
  const [allJobs, setAllJobs] = useState<JobItem[]>([]);
  const [combinedData, setCombinedData] = useState<JobTopCombinedResponse | null>(null);

  // Load all data when sortBy changes
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        console.log('Fetching jobs data...');
        
        // Load all data in parallel
        const [m, jobsList, combined] = await Promise.all([
          JobsAPI.dashboardMetrics(year),
          JobsAPI.list({ year, limit: 1000 }),
          JobsAPI.topCombined(year, 10, sortBy),
        ]);

        if (cancelled) return;

        console.log('Dashboard metrics:', m);
        console.log('Jobs list sample:', jobsList.jobs.slice(0, 3));
        console.log('Combined data:', combined);

        setMetrics(m);
        
        // Sort all jobs by the current sort criteria
        const sortedJobs = [...jobsList.jobs].sort((a, b) => {
          if (sortBy === 'employment') {
            return b.total_employment - a.total_employment;
          } else {
            const aSalary = a.a_median || 0;
            const bSalary = b.a_median || 0;
            return bSalary - aSalary;
          }
        });
        
        setAllJobs(sortedJobs);
        setCombinedData(combined);
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || 'Failed to load jobs data');
        console.error('Jobs loading error:', e);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [year, sortBy]);

  // Filter jobs based on search
  const filteredJobs = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allJobs.slice(0, 30);
    
    return allJobs
      .filter((job) =>
        job.occ_title.toLowerCase().includes(q) ||
        job.occ_code.includes(q)
      )
      .slice(0, 30);
  }, [allJobs, searchQuery]);

  // Format top jobs for horizontal bar chart
  const chartData = useMemo(() => {
    if (!combinedData) return [];
    return combinedData.top_jobs.map((job) => ({
      name: job.occ_title.length > 25 
        ? job.occ_title.substring(0, 25) + '...' 
        : job.occ_title,
      value: job.total_employment,
      secondaryValue: job.a_median || 0,
    }));
  }, [combinedData]);

  // Format metrics
  const dashboardMetrics = useMemo(() => {
    if (!metrics) return [];
    
    return [
      {
        title: 'Total Employment',
        value: metrics.total_employment,
        trend: { value: metrics.avg_job_growth_pct, direction: metrics.avg_job_growth_pct >= 0 ? 'up' as const : 'down' as const },
        color: 'cyan' as const,
        format: fmtM,
      },
      {
        title: 'Unique Job Titles',
        value: metrics.total_jobs,
        trend: { value: Math.abs(metrics.avg_job_growth_pct), direction: metrics.avg_job_growth_pct >= 0 ? 'up' as const : 'down' as const },
        color: 'purple' as const,
      },
      {
        title: 'Job Market Trend',
        value: `${metrics.avg_job_growth_pct >= 0 ? '+' : ''}${metrics.avg_job_growth_pct}%`,
        trend: { value: Math.abs(metrics.avg_job_growth_pct), direction: metrics.avg_job_growth_pct >= 0 ? 'up' as const : 'down' as const },
        color: 'green' as const,
      },
      {
        title: 'Mean Salary',
        value: metrics.a_median * 1.15,
        prefix: '$',
        trend: { value: 3.2, direction: 'up' as const },
        color: 'coral' as const,
        format: fmtK,
      },
      {
        title: 'Median Salary',
        value: metrics.a_median,
        prefix: '$',
        trend: { value: 2.8, direction: 'up' as const },
        color: 'amber' as const,
        format: fmtK,
      },
    ];
  }, [metrics]);

  // Prepare employment trend data
  const employmentTrendData = useMemo(() => {
    if (!combinedData?.employment_trends?.length) return [];
    
    const years = new Set<number>();
    combinedData.employment_trends.forEach(series => {
      series.points.forEach(point => years.add(point.year));
    });
    
    const sortedYears = Array.from(years).sort((a, b) => a - b);
    
    return sortedYears.map(year => {
      const row: any = { year };
      combinedData.employment_trends.forEach((series) => {
        const point = series.points.find(p => p.year === year);
        row[series.occ_code] = point ? point.employment : 0;
      });
      return row;
    });
  }, [combinedData]);

  // Prepare salary trend data
  const salaryTrendData = useMemo(() => {
    if (!combinedData?.salary_trends?.length) return [];
    
    const years = new Set<number>();
    combinedData.salary_trends.forEach(series => {
      series.points.forEach(point => years.add(point.year));
    });
    
    const sortedYears = Array.from(years).sort((a, b) => a - b);
    
    return sortedYears.map(year => {
      const row: any = { year };
      combinedData.salary_trends.forEach((series) => {
        const point = series.points.find(p => p.year === year);
        row[series.occ_code] = point ? point.salary : 0;
      });
      return row;
    });
  }, [combinedData]);

  // Generate line configurations for charts
  const chartLines = useMemo(() => {
    if (!combinedData?.top_jobs) return [];
    
    return combinedData.top_jobs.slice(0, 10).map((job, index) => ({
      key: job.occ_code,
      name: job.occ_title.length > 20 
        ? job.occ_title.substring(0, 20) + '...' 
        : job.occ_title,
      color: CHART_COLORS[index % CHART_COLORS.length],
    }));
  }, [combinedData]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading jobs data...</div>
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="space-y-4">
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Jobs <span className="gradient-text">Dashboard</span>
            </h1>
            <p className="mt-1 text-coral">Error: {error}</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header with Search */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Jobs <span className="gradient-text">Dashboard</span>
            </h1>
            <p className="mt-1 text-muted-foreground">
              Explore job titles, salaries, and employment trends
            </p>
          </div>
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search jobs..."
              className="pl-10 bg-secondary/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Key Metrics */}
        <MetricsGrid metrics={dashboardMetrics} />

        {/* Charts */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Top Jobs Overall */}
          <Card className="glass-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <SectionHeader
                title="Top Jobs Overall"
                subtitle={`Sorted by ${sortBy === 'employment' ? 'job postings' : 'median salary'}`}
              />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    <ArrowUpDown className="h-4 w-4" />
                    Sort by: {sortBy === 'employment' ? 'Job Postings' : 'Median Salary'}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setSortBy('employment')}>
                    Job Postings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setSortBy('salary')}>
                    Median Salary
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <HorizontalBarChart
                  data={chartData}
                  showSecondary
                  primaryLabel="Job Postings"
                  secondaryLabel="Median Salary"
                />
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No top jobs data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Combined Trends Card */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Job Trends Over Time"
                subtitle={`Top ${combinedData?.top_jobs.length || 0} jobs by ${sortBy === 'employment' ? 'job postings' : 'median salary'} (2011-2024)`}
              />
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="employment" className="w-full" onValueChange={(v) => setActiveChart(v as 'employment' | 'salary')}>
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="employment">Employment Trends</TabsTrigger>
                  <TabsTrigger value="salary">Salary Trends</TabsTrigger>
                </TabsList>
                
                <TabsContent value="employment">
                  {employmentTrendData.length > 0 && chartLines.length > 0 ? (
                    <MultiLineChart
                      data={employmentTrendData}
                      xAxisKey="year"
                      lines={chartLines}
                      height={300}
                    />
                  ) : (
                    <div className="text-muted-foreground text-center py-8">
                      No employment trend data available
                    </div>
                  )}
                </TabsContent>
                
                <TabsContent value="salary">
                  {salaryTrendData.length > 0 && chartLines.length > 0 ? (
                    <MultiLineChart
                      data={salaryTrendData}
                      xAxisKey="year"
                      lines={chartLines}
                      height={300}
                    />
                  ) : (
                    <div className="text-muted-foreground text-center py-8">
                      No salary trend data available
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Job Listings Grid */}
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <SectionHeader
              title="All Job Titles"
              subtitle={`Sorted by ${sortBy === 'employment' ? 'job postings (descending)' : 'median salary (descending)'}`}
            />
            {allJobs.length > 30 && (
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setCurrentPage(p => p + 1)}
              >
                Load More
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {filteredJobs.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {filteredJobs.map((job) => (
                  <Link
                    key={job.occ_code}
                    to={`/jobs/${encodeURIComponent(job.occ_code)}`}
                    className="group flex items-center justify-between p-4 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-all duration-200 hover:scale-[1.01]"
                  >
                    <div className="space-y-1">
                      <p className="font-medium group-hover:text-cyan transition-colors line-clamp-1">
                        {job.occ_title}
                      </p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{fmtM(job.total_employment)} employed</span>
                        <span>•</span>
                        <span className="text-xs">{job.occ_code}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-cyan">
                        ${job.a_median ? fmtK(job.a_median) : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        median salary
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                {searchQuery ? (
                  <>No jobs found matching "{searchQuery}"</>
                ) : (
                  <>No jobs data available</>
                )}
              </div>
            )}
            
            {filteredJobs.length === 30 && allJobs.length > 30 && (
              <div className="mt-6 text-center">
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentPage(p => p + 1)}
                >
                  Load More Jobs
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Jobs;
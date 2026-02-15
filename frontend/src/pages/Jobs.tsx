import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';

import { DashboardLayout, useYear } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { HorizontalBarChart, MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

import { JobsAPI } from '@/lib/jobs';
import type { 
  JobCard,
  JobDashboardMetrics,
  JobItem
} from '@/lib/jobs';

// ---------- helpers ----------
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtM = (n: number) => `${(n / 1_000_000).toFixed(1)}M`;

// Chart colors matching original UI
const CHART_COLORS = {
  cyan: 'hsl(186 100% 50%)',
  coral: 'hsl(0 100% 71%)',
  purple: 'hsl(258 90% 76%)',
  green: 'hsl(142 76% 45%)',
};

const Jobs = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const { year } = useYear();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<JobDashboardMetrics | null>(null);
  const [allJobs, setAllJobs] = useState<JobItem[]>([]);
  const [topJobs, setTopJobs] = useState<JobCard[]>([]);
  const [jobTrends, setJobTrends] = useState<any[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const yearFrom = Math.max(2019, year - 5);
        
        const [m, jobsList, top, trends] = await Promise.all([
          JobsAPI.dashboardMetrics(year),
          JobsAPI.list({ year, limit: 1000 }),
          JobsAPI.top(year, 10, 'employment'),
          JobsAPI.topTrends(yearFrom, year, 4),
        ]);

        if (cancelled) return;

        setMetrics(m);
        setAllJobs(jobsList.jobs);
        setTopJobs(top.jobs);

        // Process trend data to match original UI format
        const series = trends.series || [];
        const years = new Set<number>();
        for (const s of series) for (const p of s.points) years.add(p.year);
        
        const sortedYears = Array.from(years).sort((a, b) => a - b);
        
        // Map to original job trend format
        const trendRows = sortedYears.map((y) => {
          const row: any = { year: y };
          series.forEach((s, index) => {
            const key = index === 0 ? 'softwareEng' : 
                       index === 1 ? 'dataSci' : 
                       index === 2 ? 'nurse' : 'pm';
            const point = s.points.find((p) => p.year === y);
            row[key] = point ? point.employment : 0;
          });
          return row;
        });

        setJobTrends(trendRows);
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
  }, [year]);

  // Filter jobs based on search
  const filteredJobs = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allJobs.slice(0, 30); // Show first 30 by default
    
    return allJobs
      .filter((job) =>
        job.occ_title.toLowerCase().includes(q) ||
        job.occ_code.includes(q)
      )
      .slice(0, 30);
  }, [allJobs, searchQuery]);

  // Format top jobs for horizontal bar chart
  const chartData = useMemo(() => {
    return topJobs.slice(0, 5).map((job) => ({
      name: job.occ_title.length > 25 
        ? job.occ_title.substring(0, 25) + '...' 
        : job.occ_title,
      value: job.total_employment,
      secondaryValue: job.median_salary || 0,
    }));
  }, [topJobs]);

  // Format metrics to match original UI structure
  const dashboardMetrics = useMemo(() => {
    if (!metrics) return [];
    
    return [
      {
        title: 'Total Job Postings',
        value: metrics.total_employment,
        trend: { value: metrics.avg_job_growth_pct, direction: metrics.avg_job_growth_pct >= 0 ? 'up' as const : 'down' as const },
        color: 'cyan' as const,
        format: fmtM,
      },
      {
        title: 'Unique Job Titles',
        value: metrics.total_jobs,
        trend: { value: 2.5, direction: 'up' as const }, // Placeholder - calculate from year-over-year
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
        value: metrics.median_job_salary * 1.15, // Approximate mean from median
        prefix: '$',
        trend: { value: 3.2, direction: 'up' as const }, // Placeholder
        color: 'coral' as const,
        format: fmtK,
      },
      {
        title: 'Median Salary',
        value: metrics.median_job_salary,
        prefix: '$',
        trend: { value: 2.8, direction: 'up' as const }, // Placeholder
        color: 'amber' as const,
        format: fmtK,
      },
    ];
  }, [metrics]);

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
            <CardHeader>
              <SectionHeader
                title="Top Jobs Overall"
                subtitle="Postings count with median salary overlay"
              />
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

          {/* Employment Over Time */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Employment per Job Over Time"
                subtitle="Historical employment trends for top roles"
              />
            </CardHeader>
            <CardContent>
              {jobTrends.length > 0 ? (
                <MultiLineChart
                  data={jobTrends}
                  xAxisKey="year"
                  lines={[
                    { 
                      key: 'softwareEng', 
                      name: topJobs[0]?.occ_title || 'Software Engineer', 
                      color: CHART_COLORS.cyan 
                    },
                    { 
                      key: 'dataSci', 
                      name: topJobs[1]?.occ_title || 'Data Scientist', 
                      color: CHART_COLORS.coral 
                    },
                    { 
                      key: 'nurse', 
                      name: topJobs[2]?.occ_title || 'Registered Nurse', 
                      color: CHART_COLORS.purple 
                    },
                    { 
                      key: 'pm', 
                      name: topJobs[3]?.occ_title || 'Product Manager', 
                      color: CHART_COLORS.green 
                    },
                  ]}
                  height={350}
                />
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No trend data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Job Listings Grid */}
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <SectionHeader
              title="All Job Titles"
              subtitle="Click a job to view skills, requirements, and trends"
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
                        ${fmtK(job.median_salary || 0)}
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

import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';

import { DashboardLayout, useYear } from '@/components/layout';
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

const fmtMoney = (n: number) => {
  if (n >= 1000) {
    return `$${Math.round(n / 1000)}K`;
  }
  return `$${n}`;
};

const fmtMSafe = (n: any) => (Number.isFinite(Number(n)) ? fmtM(Number(n)) : "0M");
const fmtMoneySafe = (n: any) => (Number.isFinite(Number(n)) ? fmtMoney(Number(n)) : "$0");

// Chart colors array (extended for 10+ items)
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
  'hsl(190 90% 55%)',   // teal
  'hsl(120 60% 50%)',   // forest green
];
const pickColor = (i: number) => CHART_COLORS[i % CHART_COLORS.length];

type SortBy = 'employment' | 'salary';

// Debounce hook for search
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

const Jobs = () => {
  const { year } = useYear();
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 300);
  const [sortBy, setSortBy] = useState<SortBy>('employment');
  const [activeChart, setActiveChart] = useState<'employment' | 'salary'>('employment');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 24;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<JobDashboardMetrics | null>(null);
  const [allJobs, setAllJobs] = useState<JobItem[]>([]);
  const [topJobs, setTopJobs] = useState<JobCard[]>([]);
  const [employmentTrendData, setEmploymentTrendData] = useState<any[]>([]);
  const [salaryTrendData, setSalaryTrendData] = useState<any[]>([]);
  const [employmentChartLines, setEmploymentChartLines] = useState<{ key: string; name: string; color: string; }[]>([]);
  const [salaryChartLines, setSalaryChartLines] = useState<{ key: string; name: string; color: string; }[]>([]);
  
  // Cache for API responses
  const apiCache = useRef<Map<string, any>>(new Map());

  // Reset to page 1 when search or sort changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchInput, sortBy]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        console.log('Fetching jobs data for year:', year, 'sortBy:', sortBy);
        
        const cacheKey = `jobs-${year}-${sortBy}`;
        
        // Check cache first
        if (apiCache.current.has(cacheKey)) {
          console.log('Using cached data for', cacheKey);
          const cached = apiCache.current.get(cacheKey);
          if (!cancelled) {
            setMetrics(cached.metrics);
            setTopJobs(cached.topJobs);
            setEmploymentTrendData(cached.employmentTrendData);
            setSalaryTrendData(cached.salaryTrendData);
            setEmploymentChartLines(cached.employmentChartLines);
            setSalaryChartLines(cached.salaryChartLines);
            setAllJobs(cached.allJobs);
            setLoading(false);
          }
          return;
        }
        
        // Load data in parallel - always start from 2011 for complete history
        const yearFrom = 2011;
        
        const [m, topJobsData, employmentTrends, salaryTrends, jobsList] = await Promise.all([
          JobsAPI.dashboardMetrics(year),
          JobsAPI.top(year, 10, sortBy),
          JobsAPI.topTrends(yearFrom, year, 10, undefined, 'employment'),
          JobsAPI.topSalaryTrends(yearFrom, year, 10, undefined, 'salary'),
          JobsAPI.list({ year, limit: 1000 }),
        ]);

        if (cancelled) return;

        console.log('Data loaded for year:', year, 'sortBy:', sortBy);
        console.log('Employment trends years:', employmentTrends?.series?.[0]?.points?.map((p: any) => p.year));
        console.log('Salary trends years:', salaryTrends?.series?.[0]?.points?.map((p: any) => p.year));

        setMetrics(m);
        setTopJobs(topJobsData.jobs);

        // Process employment trends - align with top jobs
        const sortedEmploymentSeries = [...(employmentTrends?.series || [])]
          .sort((a: any, b: any) => {
            const aLatest = a?.points?.[a.points.length - 1]?.employment ?? 0;
            const bLatest = b?.points?.[b.points.length - 1]?.employment ?? 0;
            return bLatest - aLatest;
          })
          .slice(0, 10);

        const employmentTopCodes = sortedEmploymentSeries.map((s: any) => s.occ_code);
        const employmentLines = sortedEmploymentSeries.map((s: any, index: number) => ({
          key: s.occ_code,
          name: s.occ_title.length > 20
            ? s.occ_title.substring(0, 20) + '...'
            : s.occ_title,
          color: pickColor(index),
        }));
        setEmploymentChartLines(employmentLines);
        
        let employmentRows: any[] = [];
        if (employmentTrends?.series?.length) {
          // Build map of series by occ_code
          const seriesByCode = new Map(
            employmentTrends.series.map((s: any) => [s.occ_code, s])
          );
          
          // Collect all years
          const years = new Set<number>();
          employmentTrends.series.forEach((s: any) => {
            s.points.forEach((p: any) => years.add(p.year));
          });
          
          const sortedYears = Array.from(years).sort((a, b) => a - b);
          console.log(`Employment trends: ${sortedYears.length} years (${sortedYears[0]}-${sortedYears[sortedYears.length-1]})`);
          
          employmentRows = sortedYears.map(year => {
            const row: any = { year };
            employmentTopCodes.forEach(code => {
              const series = seriesByCode.get(code);
              const point = series?.points?.find((p: any) => p.year === year);
              row[code] = point ? point.employment : 0;
            });
            return row;
          });
          setEmploymentTrendData(employmentRows);
        } else {
          setEmploymentTrendData([]);
        }

        // Process salary trends - align with top jobs
        const sortedSalarySeries = [...(salaryTrends?.series || [])]
          .sort((a: any, b: any) => {
            const aLatest = a?.points?.[a.points.length - 1]?.salary ?? 0;
            const bLatest = b?.points?.[b.points.length - 1]?.salary ?? 0;
            return bLatest - aLatest;
          })
          .slice(0, 10);

        const salaryTopCodes = sortedSalarySeries.map((s: any) => s.occ_code);
        const salaryLines = sortedSalarySeries.map((s: any, index: number) => ({
          key: s.occ_code,
          name: s.occ_title.length > 20
            ? s.occ_title.substring(0, 20) + '...'
            : s.occ_title,
          color: pickColor(index),
        }));
        setSalaryChartLines(salaryLines);

        let salaryRows: any[] = [];
        if (salaryTrends?.series?.length) {
          // Build map of series by occ_code
          const seriesByCode = new Map(
            salaryTrends.series.map((s: any) => [s.occ_code, s])
          );
          
          // Collect all years
          const years = new Set<number>();
          salaryTrends.series.forEach((s: any) => {
            s.points.forEach((p: any) => years.add(p.year));
          });
          
          const sortedYears = Array.from(years).sort((a, b) => a - b);
          console.log(`Salary trends: ${sortedYears.length} years (${sortedYears[0]}-${sortedYears[sortedYears.length-1]})`);
          
          salaryRows = sortedYears.map(year => {
            const row: any = { year };
            salaryTopCodes.forEach(code => {
              const series = seriesByCode.get(code);
              const point = series?.points?.find((p: any) => p.year === year);
              row[code] = point ? point.salary : 0;
            });
            return row;
          });
          setSalaryTrendData(salaryRows);
        } else {
          setSalaryTrendData([]);
        }

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
        
        // Cache the results
        apiCache.current.set(cacheKey, {
          metrics: m,
          topJobs: topJobsData.jobs,
          employmentTrendData: employmentRows,
          salaryTrendData: salaryRows,
          employmentChartLines: employmentLines,
          salaryChartLines: salaryLines,
          allJobs: sortedJobs
        });

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

  // Filter jobs based on debounced search - memoized
  const filteredJobs = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    if (!q) return allJobs;
    
    return allJobs
      .filter((job) =>
        job.occ_title.toLowerCase().includes(q) ||
        job.occ_code.includes(q)
      );
  }, [allJobs, debouncedSearch]);

  // Separate top jobs from the rest
  const topJobsSet = useMemo(() => {
    return new Set((topJobs || []).map(j => j.occ_code));
  }, [topJobs]);

  const filteredTopJobs = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    if (!q) return topJobs;
    return topJobs.filter((job) =>
      job.occ_title.toLowerCase().includes(q) ||
      job.occ_code.includes(q)
    );
  }, [topJobs, debouncedSearch]);

  const filteredJobsNoTop = useMemo(() => {
    return filteredJobs.filter(job => !topJobsSet.has(job.occ_code));
  }, [filteredJobs, topJobsSet]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(filteredJobsNoTop.length / PAGE_SIZE)),
    [filteredJobsNoTop.length]
  );

  const pagedJobs = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredJobsNoTop.slice(start, start + PAGE_SIZE);
  }, [filteredJobsNoTop, currentPage]);

  // Format top jobs for horizontal bar chart - memoized
  const chartData = useMemo(() => {
    if (!topJobs.length) return [];
    return topJobs.map((job) => ({
      name: job.occ_title.length > 25 
        ? job.occ_title.substring(0, 25) + '...' 
        : job.occ_title,
      value: job.total_employment,
      secondaryValue: job.a_median || 0,
    }));
  }, [topJobs]);

  // Format metrics - memoized
  const dashboardMetrics = useMemo(() => {
    if (!metrics) return [];
    
    return [
      {
        title: 'Total Employment',
        value: metrics.total_employment,
        color: 'cyan' as const,
      },
      {
        title: 'Unique Job Titles',
        value: metrics.total_jobs,
        color: 'purple' as const,
      },
      {
        title: 'Avg Job Growth',
        value: metrics.avg_job_growth_pct,
        suffix: '%',
        color: 'green' as const,
      },
      {
        title: 'Mean Salary',
        value: metrics.mean_salary,
        prefix: '$',
        color: 'coral' as const,
      },
      {
        title: 'Median Salary',
        value: metrics.a_median,
        prefix: '$',
        color: 'amber' as const,
      },
    ];
  }, [metrics]);

  // Handle sort change
  const handleSortChange = useCallback((newSort: SortBy) => {
    setSortBy(newSort);
  }, []);

  // Handle page change
  const goToPrevPage = useCallback(() => {
    setCurrentPage((p) => Math.max(1, p - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage((p) => Math.min(totalPages, p + 1));
  }, [totalPages]);

  // Show loading state
  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading jobs data for {year}...</div>
        </div>
      </DashboardLayout>
    );
  }

  // Show error state
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
              Explore job titles, salaries, and employment trends (Year: {year})
            </p>
            {error && <p className="mt-2 text-sm text-coral">{error}</p>}
          </div>
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search jobs..."
              className="pl-10 bg-secondary/50"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
        </div>

        {/* Key Metrics */}
        <MetricsGrid metrics={dashboardMetrics} showTrend={false} />

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
                  <DropdownMenuItem onClick={() => handleSortChange('employment')}>
                    Job Postings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleSortChange('salary')}>
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
                subtitle={`Employment tab: top jobs by job postings, Salary tab: top jobs by median salary (2011-${year})`}
              />
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="employment" className="w-full" onValueChange={(v) => setActiveChart(v as 'employment' | 'salary')}>
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="employment">Employment Trends</TabsTrigger>
                  <TabsTrigger value="salary">Salary Trends</TabsTrigger>
                </TabsList>
                
                <TabsContent value="employment">
                  {employmentTrendData.length > 0 && employmentChartLines.length > 0 ? (
                    <>
                      <div className="mb-2 text-xs text-muted-foreground text-center">
                        Showing {employmentTrendData.length} years of historical data 
                        ({employmentTrendData[0]?.year} - {employmentTrendData[employmentTrendData.length-1]?.year})
                      </div>
                      <MultiLineChart
                        data={employmentTrendData}
                        xAxisKey="year"
                        lines={employmentChartLines}
                        height={300}
                        maxLines={10}
                      />
                    </>
                  ) : (
                    <div className="text-muted-foreground text-center py-8">
                      No employment trend data available
                    </div>
                  )}
                </TabsContent>
                
                <TabsContent value="salary">
                  {salaryTrendData.length > 0 && salaryChartLines.length > 0 ? (
                    <>
                      <div className="mb-2 text-xs text-muted-foreground text-center">
                        Showing {salaryTrendData.length} years of historical data 
                        ({salaryTrendData[0]?.year} - {salaryTrendData[salaryTrendData.length-1]?.year})
                      </div>
                      <MultiLineChart
                        data={salaryTrendData}
                        xAxisKey="year"
                        lines={salaryChartLines}
                        height={300}
                        maxLines={10}
                      />
                    </>
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
          <CardHeader>
            <SectionHeader
              title="All Job Titles"
              subtitle={`Showing ${filteredJobs.length.toLocaleString()} of ${allJobs.length.toLocaleString()} jobs`}
            />
          </CardHeader>
          <CardContent>
            {/* Top Jobs Section (always visible) */}
            {filteredTopJobs.length > 0 && (
              <>
                <h3 className="text-sm font-medium text-muted-foreground mb-3">Top Jobs</h3>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mb-8">
                  {filteredTopJobs.map((job) => (
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
              </>
            )}

            {/* All Jobs Section with Pagination */}
            {filteredJobsNoTop.length > 0 ? (
              <>
                <h3 className="text-sm font-medium text-muted-foreground mb-3">All Jobs</h3>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {pagedJobs.map((job) => (
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
                          <span>{fmtMSafe(job.total_employment)} employed</span>
                          <span>•</span>
                          <span className="text-xs">{job.occ_code}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-cyan">
                          {fmtMoneySafe(job.a_median)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          median salary
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="mt-6 flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages} 
                      {filteredJobsNoTop.length > 0 && (
                        <> (showing {(currentPage - 1) * PAGE_SIZE + 1} - {Math.min(currentPage * PAGE_SIZE, filteredJobsNoTop.length)} of {filteredJobsNoTop.length})</>
                      )}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={goToPrevPage}
                        disabled={currentPage <= 1}
                      >
                        <ChevronLeft className="h-4 w-4 mr-1" />
                        Prev
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={goToNextPage}
                        disabled={currentPage >= totalPages}
                      >
                        Next
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* No Results Message */
              <div className="text-center py-12 text-muted-foreground">
                {searchInput ? (
                  <>No jobs found matching "{searchInput}"</>
                ) : (
                  <>No additional jobs data available</>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Jobs;
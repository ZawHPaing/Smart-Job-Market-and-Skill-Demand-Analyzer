// Update the imports at the top
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

import { DashboardLayout, useYear } from "@/components/layout";
import { MetricsGrid, SectionHeader } from "@/components/dashboard";
import { HorizontalBarChart, MultiLineChart } from "@/components/charts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { IndustriesAPI, JobDetail } from "@/lib/industries";

const DEFAULT_PAGE_SIZE = 18;

const IndustryDetail = () => {
  const { id } = useParams<{ id: string }>();
  const naics = id ? decodeURIComponent(id) : "";

  const { year } = useYear();

  const [naicsTitle, setNaicsTitle] = useState("");
  const [metrics, setMetrics] = useState<any[]>([]);
  const [topJobs, setTopJobs] = useState<JobDetail[]>([]);
  const [summary, setSummary] = useState<{ year: number; employment: number; salary: number }[]>([]);
  const [allJobs, setAllJobs] = useState<JobDetail[]>([]);
  const [allJobsTotal, setAllJobsTotal] = useState(0);
  const [jobsPage, setJobsPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const pageSize = DEFAULT_PAGE_SIZE;
  const totalJobsPages = useMemo(
    () => Math.max(1, Math.ceil(allJobsTotal / pageSize)),
    [allJobsTotal, pageSize]
  );

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setLoading(true);
        setError("");

        // Load initial data (excluding paginated jobs)
        const [m, tj, s] = await Promise.all([
          IndustriesAPI.industryMetrics(naics, year),
          IndustriesAPI.topJobs(naics, year, 8),
          IndustriesAPI.summary(naics, 2011, 2024),
        ]);

        if (!alive) return;

        setNaicsTitle(m.naics_title);
        setTopJobs(tj.jobs);

        setSummary(
          s.series.map((p) => ({
            year: p.year,
            employment: p.total_employment,
            salary: p.median_salary,
          }))
        );

        const metricsUI = [
          {
            title: "Total Employment",
            value: m.total_employment,
            color: "purple" as const,
          },
          {
            title: "Median Salary",
            value: m.median_salary,
            prefix: "$",
            color: "amber" as const,
          },
          {
            title: "Top Job Title",
            value: tj.jobs[0]?.occ_title ?? "N/A",
            color: "coral" as const,
          },
        ];
        setMetrics(metricsUI);
      } catch (e: any) {
        if (!alive) return;
        setError(e?.message ?? "Failed to load industry detail");
      } finally {
        if (alive) setLoading(false);
      }
    }

    if (naics) load();
    return () => {
      alive = false;
    };
  }, [naics, year]);

  // Load jobs with pagination
  useEffect(() => {
    let alive = true;

    async function loadJobsPage() {
      if (!naics) return;
      
      setJobsLoading(true);
      try {
        const jobs = await IndustriesAPI.jobs(naics, year, jobsPage, pageSize);
        if (!alive) return;
        setAllJobs(jobs.jobs);
        setAllJobsTotal(jobs.total);
      } catch (e) {
        console.error("Failed to load jobs page:", e);
      } finally {
        if (alive) setJobsLoading(false);
      }
    }

    loadJobsPage();
    return () => {
      alive = false;
    };
  }, [naics, year, jobsPage, pageSize]);

  const jobChartData = useMemo(
    () =>
      topJobs.map((job) => ({
        name: job.occ_title,
        value: job.employment,
        secondaryValue: job.median_salary ?? 0,
        occ_code: job.occ_code,
      })),
    [topJobs]
  );

  // Helper function to format job code for URL
  const formatJobCode = (code: string) => {
    return encodeURIComponent(code);
  };

  // Format salary for display
  const formatSalary = (salary: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(salary);
  };

  // Format employment numbers for Y axis
  const formatEmployment = (value: number) => {
    if (value >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(1)}M`;
    }
    if (value >= 1_000) {
      return `${(value / 1_000).toFixed(0)}K`;
    }
    return value.toString();
  };

  // Handle page changes
  const handlePrevPage = () => {
    if (jobsPage > 1) {
      setJobsPage(p => p - 1);
    }
  };

  const handleNextPage = () => {
    if (jobsPage < totalJobsPages) {
      setJobsPage(p => p + 1);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <Link
            to="/industries"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Industries
          </Link>

          <h1 className="font-display text-3xl font-bold tracking-tight">
            {naicsTitle || naics} <span className="gradient-text">Industry</span>
          </h1>
          <p className="mt-1 text-muted-foreground">
            NAICS: {naics} • Year: {year}
          </p>
          {error ? <p className="mt-2 text-sm text-red-500">{error}</p> : null}
        </div>

        <MetricsGrid metrics={metrics} showTrend={false} />

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title={`Top Jobs in ${naicsTitle || naics}`}
                subtitle="Employment with salary overlay"
              />
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-muted-foreground">Loading...</div>
              ) : jobChartData.length > 0 ? (
                <div className="space-y-2">
                  {jobChartData.map((job) => (
                    <Link
                      key={job.occ_code}
                      to={`/jobs/${formatJobCode(job.occ_code)}`}
                      className="block group"
                    >
                      <div className="p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium group-hover:text-cyan transition-colors">
                            {job.name}
                          </span>
                          <span className="text-cyan font-medium">
                            ${Math.round(job.secondaryValue / 1000)}K
                          </span>
                        </div>
                        <div className="relative h-8 w-full bg-secondary/50 rounded overflow-hidden">
                          <div 
                            className="absolute left-0 top-0 h-full bg-cyan/30"
                            style={{ width: `${Math.min(100, (job.value / jobChartData[0].value) * 100)}%` }}
                          />
                          <div className="absolute left-2 top-1/2 -translate-y-1/2 text-xs font-medium text-foreground">
                            {job.value.toLocaleString()} employed
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                  No job data available for this industry
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="glass-card">
              <CardHeader>
                <SectionHeader
                  title="Employment Over Time"
                  subtitle="Total employment trend from 2011 to 2024"
                />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-muted-foreground">Loading...</div>
                ) : summary.length > 0 ? (
                  <MultiLineChart
                    data={summary}
                    xAxisKey="year"
                    lines={[
                      { key: "employment", name: "Employment", color: "hsl(186 100% 50%)" },
                    ]}
                    height={200}
                    formatYAxis={formatEmployment}
                  />
                ) : (
                  <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                    No employment data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <SectionHeader
                  title="Salary Over Time"
                  subtitle="Median salary trend from 2011 to 2024"
                />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-muted-foreground">Loading...</div>
                ) : summary.length > 0 ? (
                  <MultiLineChart
                    data={summary}
                    xAxisKey="year"
                    lines={[
                      { key: "salary", name: "Median Salary", color: "hsl(0 100% 71%)" },
                    ]}
                    height={200}
                    formatYAxis={(value) => `$${Math.round(value / 1000)}K`}
                  />
                ) : (
                  <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                    No salary data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        <Card className="glass-card">
          <CardHeader>
            <SectionHeader 
              title="All Jobs in This Industry" 
              subtitle={`Occupations in this NAICS for the selected year (${allJobsTotal.toLocaleString()} total)`} 
            />
          </CardHeader>
          <CardContent>
            {jobsLoading && allJobs.length === 0 ? (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                Loading jobs data...
              </div>
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {allJobs.map((job) => (
                    <Link
                      key={`${job.occ_code}-${job.occ_title}`}
                      to={`/jobs/${formatJobCode(job.occ_code)}`}
                      className="group flex items-center justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium group-hover:text-cyan transition-colors">
                          {job.occ_title}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {job.employment.toLocaleString()} employed
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-cyan">
                          ${((job.median_salary ?? 0) / 1000).toFixed(0)}K
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>

                {allJobs.length === 0 && (
                  <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                    No jobs found for this industry
                  </div>
                )}

                {/* Pagination Controls */}
                <div className="mt-6 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {jobsPage} of {totalJobsPages} (showing {allJobs.length} of {allJobsTotal.toLocaleString()} jobs)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      disabled={jobsLoading || jobsPage <= 1}
                      onClick={handlePrevPage}
                    >
                      Prev
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={jobsLoading || jobsPage >= totalJobsPages}
                      onClick={handleNextPage}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default IndustryDetail;
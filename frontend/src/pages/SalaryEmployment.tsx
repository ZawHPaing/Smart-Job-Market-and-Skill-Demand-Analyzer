import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { DashboardLayout, useYear } from "@/components/layout";
import { MetricsGrid, SectionHeader } from "@/components/dashboard";
import { HorizontalBarChart, MultiLineChart } from "@/components/charts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";

import {
  getSalaryEmploymentMetrics,
  getIndustriesBar,
  getIndustriesTable,
  getJobsTable,
  getIndustrySalaryTimeSeries,
  getTopCrossIndustryJobs,
  getJobEmploymentTimeSeries,
  type MetricItem,
  type IndustryRow,
  type JobRow,
} from "@/lib/salaryEmploymentApi";

const DEFAULT_PAGE_SIZE = 10;
const TOP_N = 6;
const LINE_PALETTE = [
  "hsl(186 100% 50%)",
  "hsl(0 100% 71%)",
  "hsl(258 90% 76%)",
  "hsl(142 71% 45%)",
  "hsl(45 93% 47%)",
  "hsl(210 100% 70%)",
];

function fmtK(n: number) {
  if (!Number.isFinite(n)) return "0K";
  return `${Math.round(n / 1000).toLocaleString()}K`;
}

function pickTopUniqueNames(items: { name: string }[], n = TOP_N) {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const it of items || []) {
    const nm = (it?.name || "").trim();
    const key = nm.toLowerCase();
    if (!nm || seen.has(key)) continue;
    seen.add(key);
    out.push(nm);
    if (out.length >= n) break;
  }
  return out;
}

function dedupeIndustriesByName(items: IndustryRow[]) {
  const map = new Map<string, IndustryRow>();
  for (const it of items || []) {
    const name = (it?.name || "").trim();
    if (!name) continue;
    const key = name.toLowerCase();
    const prev = map.get(key);
    if (!prev) {
      map.set(key, it);
      continue;
    }
    const better =
      (it.medianSalary ?? 0) > (prev.medianSalary ?? 0) ||
      ((it.medianSalary ?? 0) === (prev.medianSalary ?? 0) &&
        (it.employment ?? 0) > (prev.employment ?? 0));
    if (better) map.set(key, it);
  }
  return Array.from(map.values()).sort(
    (a, b) => (b.medianSalary ?? 0) - (a.medianSalary ?? 0)
  );
}

function buildMultiLineRows(series: { key: string; points: { year: number; value: number }[] }[]) {
  if (!series?.length) return [];
  const yearMap = new Map<number, Record<string, number>>();
  for (const s of series) {
    for (const p of s.points || []) {
      if (!yearMap.has(p.year)) yearMap.set(p.year, { year: p.year } as Record<string, number>);
      (yearMap.get(p.year) as Record<string, number>)[s.key] = p.value;
    }
  }
  return Array.from(yearMap.values()).sort((a, b) => (a.year as number) - (b.year as number));
}

// In SalaryEmployment.tsx, update the normalizeEmploymentTrendMetric function

function normalizeEmploymentTrendMetric(items: MetricItem[]): MetricItem[] {
  return (items || []).map((m) => {
    if (m.title === "Employment Trend") {
      const raw = m.value;
      const num =
        typeof raw === "number"
          ? raw
          : Number.parseFloat(String(raw ?? "").replace(/[^0-9.-]/g, ""));
      return {
        ...m,
        value: Number.isFinite(num) ? num : raw,
        suffix: "%",
      };
    }
    if (m.title === "Salary Trend") {
      const raw = m.value;
      const num =
        typeof raw === "number"
          ? raw
          : Number.parseFloat(String(raw ?? "").replace(/[^0-9.-]/g, ""));
      return {
        ...m,
        value: Number.isFinite(num) ? num : raw,
        suffix: "%",
      };
    }
    return m;
  });
}

export default function SalaryEmployment() {
  const { year } = useYear();
  const [tab, setTab] = useState<"industries" | "jobs">("industries");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const [metrics, setMetrics] = useState<MetricItem[]>([]);

  const [industryBar, setIndustryBar] = useState<
    { name: string; value: number; secondaryValue: number }[]
  >([]);
  const [industriesTable, setIndustriesTable] = useState<IndustryRow[]>([]);
  const [industriesTotal, setIndustriesTotal] = useState(0);
  const [industryPage, setIndustryPage] = useState(1);
  const [industrySeries, setIndustrySeries] = useState<
    { key: string; name: string; points: { year: number; value: number }[] }[]
  >([]);

  const [jobsTable, setJobsTable] = useState<JobRow[]>([]);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobPage, setJobPage] = useState(1);
  const [crossIndustryTopJobs, setCrossIndustryTopJobs] = useState<
    { name: string; value: number; secondaryValue: number }[]
  >([]);
  const [jobSeries, setJobSeries] = useState<
    { key: string; name: string; points: { year: number; value: number }[] }[]
  >([]);

  const pageSize = DEFAULT_PAGE_SIZE;

  const totalIndustryPages = useMemo(
    () => Math.max(1, Math.ceil(industriesTotal / pageSize)),
    [industriesTotal, pageSize]
  );
  const totalJobPages = useMemo(
    () => Math.max(1, Math.ceil(jobsTotal / pageSize)),
    [jobsTotal, pageSize]
  );

  const topIndustryNames = useMemo(
    () => pickTopUniqueNames(industryBar, TOP_N),
    [industryBar]
  );

  const industryDataForBar = useMemo(() => {
    const set = new Set(topIndustryNames.map((n) => n.toLowerCase()));
    return (industryBar || [])
      .filter((d) => set.has((d.name || "").trim().toLowerCase()))
      .slice(0, TOP_N)
      .map((d) => ({ name: d.name, value: d.value, secondaryValue: d.secondaryValue }));
  }, [industryBar, topIndustryNames]);

  const industryMultiLineData = useMemo(
    () => buildMultiLineRows(industrySeries),
    [industrySeries]
  );
  const industryLines = useMemo(
    () =>
      (industrySeries || []).map((s, idx) => ({
        key: s.key,
        name: s.name,
        color: LINE_PALETTE[idx % LINE_PALETTE.length],
      })),
    [industrySeries]
  );

  const jobMultiLineData = useMemo(() => buildMultiLineRows(jobSeries), [jobSeries]);
  const jobLines = useMemo(
    () =>
      (jobSeries || []).map((s, idx) => ({
        key: s.key,
        name: s.name,
        color: LINE_PALETTE[idx % LINE_PALETTE.length],
      })),
    [jobSeries]
  );

  async function loadIndustryTimeSeriesFromTop6Names(names: string[]) {
    if (!names.length) {
      setIndustrySeries([]);
      return;
    }

    const ts = await getIndustrySalaryTimeSeries({ names });
    const order = new Map(names.map((n, i) => [n.toLowerCase(), i]));
    const ordered = (ts.series || [])
      .filter((s) => order.has((s.name || "").toLowerCase()))
      .sort(
        (a, b) =>
          (order.get((a.name || "").toLowerCase()) ?? 999) -
          (order.get((b.name || "").toLowerCase()) ?? 999)
      )
      .slice(0, TOP_N);

    setIndustrySeries(ordered);
  }

  async function loadIndustries() {
    setLoading(true);
    try {
      const [m, bar, table] = await Promise.all([
        getSalaryEmploymentMetrics(year),
        getIndustriesBar({ year, search: searchQuery || undefined, limit: TOP_N }),
        getIndustriesTable({
          year,
          search: searchQuery || undefined,
          page: industryPage,
          page_size: pageSize,
          sort_by: "salary",
          sort_dir: -1,
        }),
      ]);

      setMetrics(normalizeEmploymentTrendMetric(m.metrics));
      setIndustryBar(bar.items);
      setIndustriesTable(dedupeIndustriesByName(table.items || []));
      setIndustriesTotal(table.total);

      const names = pickTopUniqueNames(bar.items, TOP_N);
      try {
        await loadIndustryTimeSeriesFromTop6Names(names);
      } catch (e) {
        console.error("Failed to load industry time series:", e);
        setIndustrySeries([]);
      }
    } catch (e) {
      console.error("Failed to load industries tab:", e);
    } finally {
      setLoading(false);
    }
  }

  async function loadJobs() {
    setLoading(true);
    try {
      const [m, table] = await Promise.all([
        getSalaryEmploymentMetrics(year),
        getJobsTable({
          year,
          search: searchQuery || undefined,
          page: jobPage,
          page_size: pageSize,
          sort_by: "salary",
          sort_dir: -1,
        }),
      ]);

      const [topCross, ts] = await Promise.all([
        getTopCrossIndustryJobs({ year, limit: TOP_N }).catch(() => ({ year: m.year, items: [] })),
        getJobEmploymentTimeSeries({ year, limit: TOP_N }).catch(() => ({ series: [] })),
      ]);

      setMetrics(normalizeEmploymentTrendMetric(m.metrics));
      setJobsTable(table.items);
      setJobsTotal(table.total);
      setCrossIndustryTopJobs(topCross.items || []);
      setJobSeries((ts.series || []).slice(0, TOP_N));
    } catch (e) {
      console.error("Failed to load jobs tab:", e);
    } finally {
      setLoading(false);
    }
  }

  async function loadIndustriesSearch() {
    setLoading(true);
    try {
      const table = await getIndustriesTable({
        year,
        search: searchQuery || undefined,
        page: industryPage,
        page_size: pageSize,
        sort_by: "salary",
        sort_dir: -1,
      });
      setIndustriesTable(dedupeIndustriesByName(table.items || []));
      setIndustriesTotal(table.total);
    } catch (e) {
      console.error("Failed to search industries:", e);
    } finally {
      setLoading(false);
    }
  }

  async function loadJobsSearch() {
    setLoading(true);
    try {
      const table = await getJobsTable({
        year,
        search: searchQuery || undefined,
        page: jobPage,
        page_size: pageSize,
        sort_by: "salary",
        sort_dir: -1,
      });
      setJobsTable(table.items);
      setJobsTotal(table.total);
    } catch (e) {
      console.error("Failed to search jobs:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (tab === "industries") loadIndustries();
    else loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, industryPage, jobPage]);

  useEffect(() => {
    const t = setTimeout(() => {
      if (tab === "industries") {
        if (industryPage !== 1) setIndustryPage(1);
        else loadIndustriesSearch();
      } else {
        if (jobPage !== 1) setJobPage(1);
        else loadJobsSearch();
      }
    }, 180);

    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, tab]);

  const jobSalaryData = useMemo(() => {
    return (crossIndustryTopJobs || []).slice(0, TOP_N).map((j) => ({
      name: j.name,
      value: j.value,
      secondaryValue: j.secondaryValue,
    }));
  }, [crossIndustryTopJobs]);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Salary & <span className="gradient-text">Employment</span>
            </h1>
            <p className="mt-1 text-muted-foreground">
              Compare compensation and employment across industries and roles
              {year ? ` - Year: ${year}` : ""}
            </p>
          </div>

          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search by industry or job..."
              className="pl-10 bg-secondary/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <MetricsGrid metrics={metrics} showTrend={false} />

        <Tabs value={tab} onValueChange={(v) => setTab(v as "industries" | "jobs")} className="space-y-6">
          <TabsList className="bg-secondary/50">
            <TabsTrigger value="industries">By Industry</TabsTrigger>
            <TabsTrigger value="jobs">By Job Title</TabsTrigger>
          </TabsList>

          <TabsContent value="industries" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Salary & Employment by Industry"
                    subtitle="Top 6 industries by median salary (employment overlay)"
                  />
                </CardHeader>
                <CardContent>
                  <HorizontalBarChart
                    data={industryDataForBar}
                    showSecondary
                    primaryLabel="Employment"
                    secondaryLabel="Median Salary"
                    formatValue={(v) => fmtK(v)}
                  />
                </CardContent>
              </Card>

              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Salary Distribution Over Time"
                    subtitle="Historical salary trends (same top 6 max-salary industries)"
                  />
                </CardHeader>
                <CardContent>
                  <MultiLineChart
                    data={industryMultiLineData}
                    xAxisKey="year"
                    lines={industryLines}
                    height={350}
                    formatYAxis={(v) => `$${Math.round(v / 1000)}K`}
                    maxLines={TOP_N}
                  />
                </CardContent>
              </Card>
            </div>

            <Card className="glass-card">
              <CardHeader>
                <SectionHeader
                  title="Detailed Comparison"
                  subtitle={`Industries (${industriesTotal.toLocaleString()}) - Sorted by salary (desc)`}
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
                          Employment
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Median Salary
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Trend (YoY)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {industriesTable.length > 0 ? (
                        industriesTable.map((ind) => (
                          <tr
                            key={ind.id}
                            className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                          >
                            <td className="py-3 px-4 font-medium">{ind.name}</td>
                            <td className="py-3 px-4 text-right text-muted-foreground">
                              {fmtK(ind.employment)}
                            </td>
                            <td className="py-3 px-4 text-right text-cyan">
                              ${ind.medianSalary.toLocaleString()}
                            </td>
                            <td
                              className={`py-3 px-4 text-right font-medium ${
                                ind.trend >= 0 ? "text-green-500" : "text-coral"
                              }`}
                            >
                              {ind.trend >= 0 ? "+" : ""}
                              {ind.trend.toFixed(2)}%
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td
                            colSpan={4}
                            className="py-8 px-4 text-center text-sm text-muted-foreground"
                          >
                            {searchQuery.trim()
                              ? `No industries found for "${searchQuery.trim()}".`
                              : "No industries found."}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {industryPage} of {totalIndustryPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      disabled={loading || industryPage <= 1}
                      onClick={() => setIndustryPage((p) => Math.max(1, p - 1))}
                    >
                      Prev
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={loading || industryPage >= totalIndustryPages}
                      onClick={() => setIndustryPage((p) => Math.min(totalIndustryPages, p + 1))}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="jobs" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Salary & Employment by Job"
                    subtitle="Top 6 Cross-industry job titles by median salary (employment overlay)"
                  />
                </CardHeader>
                <CardContent>
                  <HorizontalBarChart
                    data={jobSalaryData}
                    showSecondary
                    primaryLabel="Employment"
                    secondaryLabel="Median Salary"
                    formatValue={(v) => fmtK(v)}
                  />
                </CardContent>
              </Card>

              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Employment per Job Over Time"
                    subtitle="Top 6 cross-industry job titles by employment (historical)"
                  />
                </CardHeader>
                <CardContent>
                  <MultiLineChart
                    data={jobMultiLineData}
                    xAxisKey="year"
                    lines={jobLines}
                    height={350}
                    maxLines={TOP_N}
                    formatYAxis={(v) => fmtK(v)}
                  />
                </CardContent>
              </Card>
            </div>

            <Card className="glass-card">
              <CardHeader>
                <SectionHeader
                  title="Detailed Comparison"
                  subtitle={`Jobs (${jobsTotal.toLocaleString()})`}
                />
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                          Job Title
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Employment
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Median Salary
                        </th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                          Trend (YoY)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobsTable.length > 0 ? (
                        jobsTable.map((j) => (
                          <tr
                            key={`${j.occ_code}-${j.occ_title}`}
                            className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                          >
                            <td className="py-3 px-4 font-medium">{j.occ_title}</td>
                            <td className="py-3 px-4 text-right text-muted-foreground">
                              {fmtK(j.employment)}
                            </td>
                            <td className="py-3 px-4 text-right text-cyan">
                              ${j.medianSalary.toLocaleString()}
                            </td>
                            <td
                              className={`py-3 px-4 text-right font-medium ${
                                j.trend >= 0 ? "text-green-500" : "text-coral"
                              }`}
                            >
                              {j.trend >= 0 ? "+" : ""}
                              {j.trend.toFixed(2)}%
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td
                            colSpan={4}
                            className="py-8 px-4 text-center text-sm text-muted-foreground"
                          >
                            {searchQuery.trim()
                              ? `No jobs found for "${searchQuery.trim()}".`
                              : "No jobs found."}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {jobPage} of {totalJobPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      disabled={loading || jobPage <= 1}
                      onClick={() => setJobPage((p) => Math.max(1, p - 1))}
                    >
                      Prev
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={loading || jobPage >= totalJobPages}
                      onClick={() => setJobPage((p) => Math.min(totalJobPages, p + 1))}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}


import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";

import { DashboardLayout } from "@/components/layout";
import { MetricsGrid, SectionHeader } from "@/components/dashboard";
import { StackedBarChart, MultiLineChart } from "@/components/charts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import { IndustriesAPI } from "@/lib/industries";

// ---------- helpers ----------
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtM = (n: number) => `${(n / 1_000_000).toFixed(1)}M`;

function pctBadgeClass(pct?: number | null) {
  if (pct == null) return "text-muted-foreground";
  return pct >= 0 ? "text-green-500" : "text-coral";
}

// ✅ chart colors (required by your chart component prop types)
const CHART_COLORS = [
  "hsl(186 100% 50%)", // cyan
  "hsl(258 90% 76%)",  // purple
  "hsl(0 100% 71%)",   // coral/red
  "hsl(45 100% 55%)",  // amber
  "hsl(142 71% 45%)",  // green
  "hsl(210 100% 60%)", // blue
];
const pickColor = (i: number) => CHART_COLORS[i % CHART_COLORS.length];

export default function Industries() {
  const [searchQuery, setSearchQuery] = useState("");
  const [year, setYear] = useState(2024); // replace with your global year if you have one

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<any>(null);

  const [allIndustries, setAllIndustries] = useState<{ naics: string; naics_title: string }[]>([]);
  const [topIndustries, setTopIndustries] = useState<any[]>([]);

  // ✅ Top 3 occupations per industry chart
  const [topOccRows, setTopOccRows] = useState<any[]>([]);
  const [topOccLegend, setTopOccLegend] = useState<{ key: string; name: string }[]>([]);

  // ✅ trends chart data
  const [trendRows, setTrendRows] = useState<any[]>([]);
  const [trendSeries, setTrendSeries] = useState<{ key: string; name: string }[]>([]);

  const [showMore, setShowMore] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const yearFrom = Math.max(2019, year - 5);

        const [m, list, top, topOcc, trends] = await Promise.all([
          IndustriesAPI.dashboardMetrics(year),
          IndustriesAPI.list(year),
          IndustriesAPI.top(year, 6, "employment"),
          IndustriesAPI.compositionTopOccupations(year, 6, 3),
          IndustriesAPI.topTrends(yearFrom, year, 3),
        ]);

        if (cancelled) return;

        setMetrics(m);
        setAllIndustries(list.industries);
        setTopIndustries(top.industries);

        setTopOccRows(topOcc.rows || []);
        setTopOccLegend(topOcc.legend || []);

        // ---- convert trends -> [{year, <naics>: employment, ...}] ----
        const series = trends.series || [];
        const years = new Set<number>();
        for (const s of series) for (const p of s.points) years.add(p.year);

        const sortedYears = Array.from(years).sort((a, b) => a - b);
        const rows = sortedYears.map((y) => {
          const row: any = { year: y };
          for (const s of series) {
            const key = s.naics; // stable key
            const found = s.points.find((p: any) => p.year === y);
            row[key] = found ? found.employment : 0;
          }
          return row;
        });

        setTrendRows(rows);
        setTrendSeries(
          series.map((s: any) => ({
            key: s.naics,
            name: s.naics_title,
          }))
        );
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || "Failed to load industries");
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

  const filteredAll = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allIndustries;
    return allIndustries.filter((i) => i.naics_title.toLowerCase().includes(q) || i.naics.includes(q));
  }, [allIndustries, searchQuery]);

  const topCards = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return topIndustries;
    return topIndustries.filter((i) => i.naics_title.toLowerCase().includes(q) || i.naics.includes(q));
  }, [topIndustries, searchQuery]);

  const metricsGrid = useMemo(() => {
    if (!metrics) return [];
    return [
      {
        title: "Total Industries",
        value: metrics.total_industries,
        trend: { value: 0, direction: "up" as const },
        color: "cyan" as const,
      },
      {
        title: "Total Employment",
        value: metrics.total_employment,
        trend: { value: 0, direction: "up" as const },
        color: "purple" as const,
      },
      {
        title: "Avg Industry Growth",
        value: metrics.avg_industry_growth_pct,
        trend: { value: 0, direction: "up" as const },
        color: "green" as const,
      },
      {
        title: "Top Growing Industry",
        value: metrics.top_growing_industry?.naics_title || "—",
        color: "coral" as const,
      },
      {
        title: "Median Industry Salary",
        value: metrics.median_industry_salary,
        prefix: "$",
        trend: { value: 0, direction: "up" as const },
        color: "amber" as const,
      },
    ];
  }, [metrics]);

  // chart configs (typed: must include color)
  const stackedBars = useMemo(
    () =>
      topOccLegend.map((l, i) => ({
        key: l.key,
        name: l.name,
        color: pickColor(i),
      })),
    [topOccLegend]
  );

  const trendLines = useMemo(
    () =>
      trendSeries.map((s, i) => ({
        key: s.key,
        name: s.name,
        color: pickColor(i),
      })),
    [trendSeries]
  );

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header with Search */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Industries <span className="gradient-text">Dashboard</span>
            </h1>
            <p className="mt-1 text-muted-foreground">
              Explore employment trends and job distributions across industries (Year: {year})
            </p>
            {error && <p className="mt-2 text-sm text-coral">{error}</p>}
          </div>

          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search industries..."
              className="pl-10 bg-secondary/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Metrics */}
        <MetricsGrid metrics={metricsGrid} />

        {/* Top 6 Industries */}
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <SectionHeader title="Top Industries" subtitle="Top 6 industries by total employment" />
            <Button variant="secondary" onClick={() => setShowMore((v) => !v)}>
              {showMore ? "Hide" : "See more"}
            </Button>
          </CardHeader>

          <CardContent>
            {loading ? (
              <div className="text-muted-foreground">Loading...</div>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {topCards.map((ind) => (
                    <Link
                      key={ind.naics}
                      to={`/industries/${encodeURIComponent(ind.naics)}`}
                      className="group glass-card p-4 transition-all duration-300 hover:border-cyan/50 hover:scale-[1.02]"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-medium group-hover:text-cyan transition-colors">{ind.naics_title}</h3>
                          <p className="text-sm text-muted-foreground">NAICS: {ind.naics}</p>
                        </div>

                        <span className={`text-sm font-medium ${pctBadgeClass(ind.growth_pct)}`}>
                          {ind.growth_pct == null ? "—" : `${ind.growth_pct >= 0 ? "+" : ""}${ind.growth_pct}%`}
                        </span>
                      </div>

                      <div className="mt-3 flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{fmtM(ind.total_employment)} employed</span>
                        <span className="text-cyan">${fmtK(ind.median_salary)} median</span>
                      </div>
                    </Link>
                  ))}
                </div>

                {/* See more list */}
                {showMore && (
                  <div className="mt-6">
                    <p className="text-sm text-muted-foreground mb-3">All industries (filtered): {filteredAll.length}</p>

                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {filteredAll.slice(0, 60).map((ind) => (
                        <Link
                          key={ind.naics}
                          to={`/industries/${encodeURIComponent(ind.naics)}`}
                          className="group glass-card p-4 transition-all duration-300 hover:border-cyan/50 hover:scale-[1.02]"
                        >
                          <h3 className="font-medium group-hover:text-cyan transition-colors">{ind.naics_title}</h3>
                          <p className="text-sm text-muted-foreground">NAICS: {ind.naics}</p>
                          <p className="mt-2 text-xs text-muted-foreground">
                            Click to view jobs, employment & salary trends
                          </p>
                        </Link>
                      ))}
                    </div>

                    {filteredAll.length > 60 && (
                      <p className="mt-3 text-xs text-muted-foreground">Showing first 60. Add pagination if you want.</p>
                    )}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Charts */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Job Composition */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Job Composition by Industry"
                subtitle="Top 3 occupations (by employment) inside each top industry"
              />
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-muted-foreground">Loading...</div>
              ) : (
                <StackedBarChart data={topOccRows} xAxisKey="industry" bars={stackedBars} height={350} />
              )}
            </CardContent>
          </Card>

          {/* Employment Over Time */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader title="Employment per Industry Over Time" subtitle="Top industries by employment (time series)" />
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-muted-foreground">Loading...</div>
              ) : (
                <MultiLineChart data={trendRows} xAxisKey="year" lines={trendLines} height={350} />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}

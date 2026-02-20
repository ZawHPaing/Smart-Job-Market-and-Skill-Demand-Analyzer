import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search } from "lucide-react";

import { DashboardLayout, useYear } from "@/components/layout";
import { MetricsGrid, SectionHeader } from "@/components/dashboard";
import { MultiLineChart } from "@/components/charts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

import { IndustriesAPI } from "@/lib/industries";

// ---------- helpers ----------
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtM = (n: number) => `${(n / 1_000_000).toFixed(1)}M`;
const fmtKSafe = (n: any) => (Number.isFinite(Number(n)) ? fmtK(Number(n)) : "0K");
const fmtMSafe = (n: any) => (Number.isFinite(Number(n)) ? fmtM(Number(n)) : "0M");
const fmtMoneyKSafe = (n: any) => (Number.isFinite(Number(n)) ? `$${fmtK(Number(n))}` : "$0K");

function pctBadgeClass(pct?: number | null) {
  if (pct == null) return "text-muted-foreground";
  return pct >= 0 ? "text-green-500" : "text-coral";
}

// ✅ Extended chart colors for 10 items
const CHART_COLORS = [
  "hsl(186 100% 50%)", // cyan
  "hsl(258 90% 76%)", // purple
  "hsl(0 100% 71%)", // coral/red
  "hsl(45 100% 55%)", // amber
  "hsl(142 71% 45%)", // green
  "hsl(210 100% 60%)", // blue
  "hsl(330 85% 60%)", // pink
  "hsl(280 70% 65%)", // lavender
  "hsl(190 90% 55%)", // teal
  "hsl(120 60% 50%)", // forest green
];
const pickColor = (i: number) => CHART_COLORS[i % CHART_COLORS.length];

// ---- normalize top-occupations legend so bar.name becomes the REAL job title ----
function normalizeOccLegend(legend: any[]): { key: string; name: string }[] {
  if (!Array.isArray(legend)) return [];

  return legend
    .map((l: any, idx: number) => {
      const key = l?.key || l?.field || l?.dataKey || `occ_${idx + 1}`;
      const name = String(l?.name || l?.occ_title || l?.title || l || `Top Occupation #${idx + 1}`).trim();
      return { key, name };
    })
    .filter((x) => x.key && x.name);
}

// ---- Trends: exclude Cross-industry and dedupe by title ----
function normalizeTrendSeries(rawSeries: any[], takeN = 10) {  // Changed from 6 to 10
  const series = Array.isArray(rawSeries) ? rawSeries : [];

  const isCross = (s: any) => String(s?.naics_title || "").toLowerCase().includes("cross-industry");
  const others = series.filter((s) => !isCross(s));

  // dedupe industries by naics_title (case-insensitive)
  const seenTitle = new Set<string>();
  const uniqueOthers: any[] = [];
  for (const s of others) {
    const title = String(s?.naics_title || "").trim();
    if (!title) continue;
    const k = title.toLowerCase();
    if (seenTitle.has(k)) continue;
    seenTitle.add(k);
    uniqueOthers.push(s);
  }

  return uniqueOthers.slice(0, takeN);
}

export default function Industries() {
  const [searchQuery, setSearchQuery] = useState("");
  const { year } = useYear();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<any>(null);

  const [allIndustries, setAllIndustries] = useState<any[]>([]);
  const [topIndustries, setTopIndustries] = useState<any[]>([]);

  // trends chart
  const [trendRows, setTrendRows] = useState<any[]>([]);
  const [trendSeries, setTrendSeries] = useState<{ key: string; name: string }[]>([]);

  const [showMore, setShowMore] = useState(false);
  const [allPage, setAllPage] = useState(1);
  const ALL_PAGE_SIZE = 24;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const yearFrom = Math.max(2019, year - 5);

        const [m, list, top, trends] = await Promise.all([
          IndustriesAPI.dashboardMetrics(year),
          IndustriesAPI.top(year, 1000, "employment"),
          IndustriesAPI.top(year, 10, "employment"),  // Changed from 6 to 10

          // ✅ Request 10 trends
          IndustriesAPI.topTrends(yearFrom, year, 10),  // Changed from 3/6 to 10
        ]);

        if (cancelled) return;

        setMetrics(m);
        setAllIndustries(list.industries || []);
        setTopIndustries(top.industries);

        // ✅ Align trends to the same Top 10 industries shown in cards
        const topList = top.industries || [];
        const topNaics = topList.map((i: any) => String(i.naics || "").trim()).filter(Boolean);
        const topTitleByNaics = new Map(
          topList.map((i: any) => [String(i.naics || "").trim(), String(i.naics_title || "").trim()])
        );

        const rawSeries = trends?.series || [];
        const seriesByNaics = new Map<string, any>();
        const seriesByTitle = new Map<string, any>();
        
        for (const s of rawSeries) {
          const naics = String(s?.naics || "").trim();
          const title = String(s?.naics_title || "").trim();
          if (!naics || !title) continue;
          if (String(s?.naics_title || "").toLowerCase().includes("cross-industry")) continue;
          seriesByNaics.set(naics, s);
          const tkey = title.toLowerCase();
          if (!seriesByTitle.has(tkey)) seriesByTitle.set(tkey, s);
        }

        const missingNaics = topNaics.filter((naics) => {
          const titleKey = (topTitleByNaics.get(naics) || "").toLowerCase();
          return !seriesByNaics.has(naics) && (!titleKey || !seriesByTitle.has(titleKey));
        });

        if (missingNaics.length) {
          const summaries = await Promise.all(
            missingNaics.map((naics) => IndustriesAPI.summary(naics, yearFrom, year))
          );
          for (const s of summaries) {
            const naics = String(s?.naics || "").trim();
            if (!naics) continue;
            const points =
              (s?.series || []).map((p: any) => ({
                year: Number(p.year),
                employment: Number(p.total_employment) || 0,
              })) || [];
            seriesByNaics.set(naics, {
              naics,
              naics_title: String(s?.naics_title || "").trim(),
              points,
            });
          }
        }

        // build rows: [{year, <naics>: employment, ...}] aligned to topNaics
        const years = new Set<number>();
        for (const naics of topNaics) {
          const titleKey = (topTitleByNaics.get(naics) || "").toLowerCase();
          const s = seriesByNaics.get(naics) || (titleKey ? seriesByTitle.get(titleKey) : undefined);
          if (s?.points) {
            for (const p of s.points) years.add(Number(p.year));
          }
        }

        const sortedYears = Array.from(years).sort((a, b) => a - b);
        const rows = sortedYears.map((y) => {
          const row: any = { year: y };
          for (const naics of topNaics) {
            const titleKey = (topTitleByNaics.get(naics) || "").toLowerCase();
            const s = seriesByNaics.get(naics) || (titleKey ? seriesByTitle.get(titleKey) : undefined);
            const found = (s?.points || []).find((p: any) => Number(p.year) === y);
            row[naics] = found ? Number(found.employment) || 0 : 0;
          }
          return row;
        });

        setTrendRows(rows);
        setTrendSeries(
          topNaics.map((naics) => ({
            key: naics,
            name: topTitleByNaics.get(naics) || naics,
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
    return allIndustries.filter((i) => i.naics_title?.toLowerCase().includes(q) || i.naics?.includes(q));
  }, [allIndustries, searchQuery]);

  const filteredAllNoCross = useMemo(() => {
    const topSet = new Set(
      (topIndustries || []).map((i) => String(i?.naics || "").trim()).filter(Boolean)
    );
    return filteredAll.filter((i) => {
      const title = String(i?.naics_title || "").toLowerCase();
      const naics = String(i?.naics || "").trim();
      if (title.includes("cross-industry")) return false;
      if (topSet.has(naics)) return false;
      return true;
    });
  }, [filteredAll, topIndustries]);

  const totalAllPages = useMemo(
    () => Math.max(1, Math.ceil(filteredAllNoCross.length / ALL_PAGE_SIZE)),
    [filteredAllNoCross.length]
  );

  const pagedAll = useMemo(() => {
    const start = (allPage - 1) * ALL_PAGE_SIZE;
    return filteredAllNoCross.slice(start, start + ALL_PAGE_SIZE);
  }, [filteredAllNoCross, allPage]);

  const topCards = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return topIndustries;
    return topIndustries.filter((i) => i.naics_title.toLowerCase().includes(q) || i.naics.includes(q));
  }, [topIndustries, searchQuery]);

  useEffect(() => {
    setAllPage(1);
  }, [searchQuery, showMore]);

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

        {/* Top 10 Industries */}
        <Card className="glass-card">
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <SectionHeader 
              title="Top Industries" 
              subtitle="Top 10 industries by total employment"  // Updated subtitle
            />
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

                {showMore && (
                  <div className="mt-6">
                    <p className="text-sm text-muted-foreground mb-3">All industries</p>

                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {pagedAll.map((ind) => (
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
                            <span className="text-muted-foreground">{fmtMSafe(ind.total_employment)} employed</span>
                            <span className="text-cyan">{fmtMoneyKSafe(ind.median_salary)} median</span>
                          </div>
                        </Link>
                      ))}
                    </div>

                    <div className="mt-4 flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        Page {allPage} of {totalAllPages}
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="secondary"
                          disabled={allPage <= 1}
                          onClick={() => setAllPage((p) => Math.max(1, p - 1))}
                        >
                          Prev
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={allPage >= totalAllPages}
                          onClick={() => setAllPage((p) => Math.min(totalAllPages, p + 1))}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Employment Over Time - Full Width */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader 
              title="Employment per Industry Over Time" 
              subtitle="Top 10 industries by employment (time series)"  // Updated subtitle
            />
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-muted-foreground">Loading...</div>
            ) : (
              <MultiLineChart data={trendRows} xAxisKey="year" lines={trendLines} height={400}  maxLines={10} />
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

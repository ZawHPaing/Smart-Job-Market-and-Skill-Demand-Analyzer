// src/pages/Home.tsx
import { useEffect, useMemo, useState } from "react";
import { DashboardLayout, useYear } from "@/components/layout";
import { MetricsGrid, SectionHeader } from "@/components/dashboard";
import { HorizontalBarChart, MultiLineChart } from "@/components/charts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DonutChart } from "@/components/charts/DonutChart";

const API_BASE = "http://127.0.0.1:8000/api";

// ---------- helpers ----------
const toNumber = (v: any): number => {
  if (v === null || v === undefined) return 0;
  if (typeof v === "number") return v;
  const n = parseFloat(String(v).replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
};

const safeKey = (naics: string) => `i_${String(naics).replace(/[^a-zA-Z0-9]/g, "_")}`;

// Deduplicate by industry id (naics or id), keep first occurrence
const dedupeByNaics = (arr: any[]) => {
  const seen = new Set<string>();
  const out: any[] = [];
  for (const it of arr || []) {
    const k = String(it?.naics ?? it?.id ?? "");
    if (!k) continue;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(it);
  }
  return out;
};

// Keep ONE Cross-industry total (even if backend sends multiple variants)
const mergeCrossIndustry = (series: any[]) => {
  const isCross = (s: any) => String(s?.naics_title || "").toLowerCase().includes("cross-industry");

  const cross = (series || []).filter(isCross);
  const others = (series || []).filter((s) => !isCross(s));

  let mergedCross: any | null = null;

  if (cross.length) {
    // If multiple cross series come back, merge by summing employment per year
    const yearMap = new Map<number, number>();
    for (const s of cross) {
      for (const p of s?.points || []) {
        const y = Number(p?.year);
        if (!Number.isFinite(y)) continue;
        const emp = toNumber(p?.employment);
        yearMap.set(y, (yearMap.get(y) || 0) + emp);
      }
    }

    const points = Array.from(yearMap.entries())
      .map(([year, employment]) => ({ year, employment }))
      .sort((a, b) => a.year - b.year);

    mergedCross = {
      naics: "CROSS_INDUSTRY",
      naics_title: "Cross-industry",
      points,
    };
  }

  return {
    mergedCross,
    others,
  };
};

async function buildTrendAligned(
  topItems: any[],
  seriesInput: any[],
  yearFrom: number,
  yearTo: number
): Promise<{ data: Record<string, any>[]; lines: { key: string; name: string; color: string }[] }> {
  // Take top 10 industries
  const top = dedupeByNaics(topItems).slice(0, 10);
  const topNaics = top.map((i: any) => String(i.naics || "").trim()).filter(Boolean);
  const topTitleByNaics = new Map(
    top.map((i: any) => [String(i.naics || "").trim(), String(i.naics_title || "").trim()])
  );

  const raw = Array.isArray(seriesInput) ? seriesInput : [];
  const { others } = mergeCrossIndustry(raw);

  const seriesByNaics = new Map<string, any>();
  for (const s of others) {
    const naics = String(s?.naics || "").trim();
    if (!naics) continue;
    seriesByNaics.set(naics, s);
  }

  const missing = topNaics.filter((naics) => !seriesByNaics.has(naics));
  if (missing.length) {
    const summaries = await Promise.all(
      missing.map((naics) =>
        fetch(
          `${API_BASE}/industries/${encodeURIComponent(naics)}/summary?year_from=${yearFrom}&year_to=${yearTo}`
        ).then((r) => r.json())
      )
    );
    for (const s of summaries) {
      const naics = String(s?.naics || "").trim();
      if (!naics) continue;
      const points =
        (s?.series || []).map((p: any) => ({
          year: Number(p.year),
          employment: Number(p.total_employment) || 0,
        })) || [];
      seriesByNaics.set(naics, { naics, naics_title: s?.naics_title, points });
    }
  }

  const years = new Set<number>();
  for (const naics of topNaics) {
    const s = seriesByNaics.get(naics);
    if (s?.points) {
      for (const p of s.points) years.add(Number(p.year));
    }
  }
  const sortedYears = Array.from(years).filter((y) => Number.isFinite(y)).sort((a, b) => a - b);

  const data = sortedYears.map((y) => {
    const row: Record<string, any> = { year: y };
    for (const naics of topNaics) {
      const s = seriesByNaics.get(naics);
      const p = s?.points?.find((pt: any) => Number(pt?.year) === y);
      row[safeKey(naics)] = p ? toNumber(p?.employment) : null;
    }
    return row;
  });

  // Extended color palette for 10 items
  const palette = [
    "hsl(186 100% 50%)", // cyan
    "hsl(0 100% 71%)",   // coral/red
    "hsl(258 90% 76%)",  // purple
    "hsl(142 76% 45%)",  // green
    "hsl(43 96% 56%)",   // amber
    "hsl(330 100% 65%)", // pink
    "hsl(215 100% 65%)", // blue
    "hsl(30 100% 65%)",  // orange
    "hsl(280 70% 65%)",  // lavender
    "hsl(190 90% 55%)",  // teal
  ];

  const used = new Map<string, number>();
  const lines = topNaics.map((naics, idx) => {
    const base = String(topTitleByNaics.get(naics) || naics).trim();
    const count = used.get(base) ?? 0;
    used.set(base, count + 1);
    const displayName = count === 0 ? base : `${base} (${naics})`;
    return { key: safeKey(naics), name: displayName, color: palette[idx % palette.length] };
  });

  return { data, lines };
}

export default function Home() {
  const { year } = useYear();

  const [metrics, setMetrics] = useState<any>(null);
  const [industryList, setIndustryList] = useState<any[]>([]);
  const [topIndustries, setTopIndustries] = useState<any[]>([]);
  const [topJobs, setTopJobs] = useState<any[]>([]);
  const [topTrends, setTopTrends] = useState<any[]>([]);
  const [trendData, setTrendData] = useState<Record<string, any>[]>([]);
  const [trendLines, setTrendLines] = useState<{ key: string; name: string; color: string }[]>([]);
  const [uniqueJobTitles, setUniqueJobTitles] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);

        // Always start from 2011 for complete historical data
        const yearFrom = 2011;

        // Fetch all data in parallel
        const [mRes, listRes, topRes, trendsRes, topJobsRes, jobsMetricsRes] = await Promise.all([
          fetch(`${API_BASE}/industries/metrics/${year}`),
          fetch(`${API_BASE}/industries/?year=${year}&limit=1000`),
          fetch(`${API_BASE}/industries/top?year=${year}&limit=20&by=employment`),
          // Request trends from 2011 to current year
          fetch(`${API_BASE}/industries/top-trends?year_from=${yearFrom}&year_to=${year}&limit=10`),
          fetch(`${API_BASE}/jobs/top?year=${year}&limit=10&by=employment`),
          fetch(`${API_BASE}/jobs/metrics/${year}`),
        ]);

        // If any response isn't ok, throw so we don't silently build empty charts
        if (!mRes.ok) throw new Error(`metrics failed: ${mRes.status}`);
        if (!listRes.ok) throw new Error(`industries list failed: ${listRes.status}`);
        if (!topRes.ok) throw new Error(`top industries failed: ${topRes.status}`);
        if (!trendsRes.ok) throw new Error(`top trends failed: ${trendsRes.status}`);
        if (!topJobsRes.ok) throw new Error(`top jobs failed: ${topJobsRes.status}`);
        if (!jobsMetricsRes.ok) throw new Error(`jobs metrics failed: ${jobsMetricsRes.status}`);

        const mJson = await mRes.json();
        const listJson = await listRes.json();
        const topJson = await topRes.json();
        const trendsJson = await trendsRes.json();
        const topJobsJson = await topJobsRes.json();
        const jobsMetricsJson = await jobsMetricsRes.json();

        if (cancelled) return;

        setMetrics(mJson || null);

        const listItems = Array.isArray(listJson)
          ? listJson
          : listJson.items || listJson.industries || [];
        setIndustryList(listItems);

        const topItems = Array.isArray(topJson)
          ? topJson
          : topJson.items || topJson.industries || topJson.top || [];
        setTopIndustries(topItems);

        // Handle trends data - ensure we get the series array
        const series = Array.isArray(trendsJson) 
          ? trendsJson 
          : trendsJson.series || trendsJson.items || trendsJson.trends || [];
        setTopTrends(series);

        const topJobItems = Array.isArray(topJobsJson)
          ? topJobsJson
          : topJobsJson.jobs || topJobsJson.items || [];
        setTopJobs(topJobItems);
        setUniqueJobTitles(Number(jobsMetricsJson?.total_jobs || 0));

        // ---- trends aligned to top 10 industries ----
        const aligned = await buildTrendAligned(topItems, series, yearFrom, year);
        if (!cancelled) {
          setTrendData(aligned.data);
          setTrendLines(aligned.lines);
          console.log(`📊 Home trends loaded from ${yearFrom} to ${year} (${aligned.data.length} years)`);
        }

        // unique job titles now sourced from /jobs/metrics for consistency
      } catch (e) {
        console.error("Home fetch error:", e);
        if (!cancelled) {
          setMetrics(null);
          setIndustryList([]);
          setTopIndustries([]);
          setTopJobs([]);
          setTopTrends([]);
          setUniqueJobTitles(0);
          setTrendData([]);
          setTrendLines([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [year]);

  // ✅ TOP 10 donut with "Others" category
  const donutData = useMemo(() => {
    const srcRaw = topIndustries.length ? topIndustries : industryList;
    const src = dedupeByNaics(srcRaw);
    
    if (src.length === 0) return [];
    const totalEmploymentBase = toNumber(metrics?.total_employment ?? metrics?.totalEmployment);
    
    // Sort by employment value descending
    const sorted = [...src].sort((a, b) => {
      const valA = toNumber(a.total_employment ?? a.employment ?? a.tot_emp ?? a.value);
      const valB = toNumber(b.total_employment ?? b.employment ?? b.tot_emp ?? b.value);
      return valB - valA;
    });
    
    // Take top 10 for individual display
    const top10 = sorted.slice(0, 10);
    
    const top10Sum = top10.reduce(
      (sum, it) => sum + toNumber(it.total_employment ?? it.employment ?? it.tot_emp ?? it.value),
      0
    );

    // Calculate "Others" from the cross-industry total baseline when available.
    // This keeps donut total aligned with the dashboard's cross-industry total.
    const remaining = sorted.slice(10);
    const remainingSum = remaining.reduce((sum, it) => 
      sum + toNumber(it.total_employment ?? it.employment ?? it.tot_emp ?? it.value), 0
    );
    const othersSum =
      totalEmploymentBase > 0 ? Math.max(totalEmploymentBase - top10Sum, 0) : remainingSum;
    
    // Build chart data with top 10 + Others
    const chartData = top10
      .map((it: any) => ({
        name: it.naics_title || it.name || "Unknown",
        value: toNumber(it.total_employment ?? it.employment ?? it.tot_emp ?? it.value),
      }))
      .filter((x) => x.value > 0);
    
    // Add a single Others slice whenever baseline total implies remaining share.
    if (othersSum > 0) {
      chartData.push({
        name: "Others",
        value: othersSum,
      });
    }
    
    return chartData;
  }, [metrics, topIndustries, industryList]);

  // ✅ TOP 10 job titles by employment (cross-industry), with median salary
  const topJobChartData = useMemo(() => {
    const src = (topJobs || []).slice(0, 10);
    return src.map((it: any) => ({
      name: it.occ_title || it.name || "Unknown",
      value: toNumber(it.total_employment ?? it.employment ?? it.tot_emp),
      secondaryValue: toNumber(it.median_salary ?? it.median_annual_wage ?? it.a_median ?? it.salary),
      fullName: it.occ_title || it.name || "Unknown",
    }));
  }, [topJobs]);

  // ✅ TOP 10 trend lines aligned to Top 10 industries
  const trend = useMemo(() => ({ 
    data: trendData, 
    lines: trendLines 
  }), [trendData, trendLines]);

  // ---------- Metrics cards ----------
  const cards = useMemo(() => {
    const totalEmployment = toNumber(metrics?.total_employment ?? metrics?.totalEmployment);
    const uniqueIndustries = toNumber(metrics?.total_industries ?? metrics?.unique_industries ?? metrics?.uniqueIndustries);

    const medianSalary = toNumber(
      metrics?.median_industry_salary ?? metrics?.median_salary ?? metrics?.medianSalary ?? metrics?.median_industry_wage
    );

    const growthPct = toNumber(metrics?.avg_industry_growth_pct ?? metrics?.industry_trend_pct ?? 0);
    const growthDir = growthPct >= 0 ? ("up" as const) : ("down" as const);

    return [
      {
        title: "Total Employment",
        value: totalEmployment,
        trend: { value: Math.abs(growthPct), direction: growthDir },
        color: "cyan" as const,
      },
      {
        title: "Unique Industries",
        value: uniqueIndustries,
        trend: { value: 0, direction: "neutral" as const },
        color: "purple" as const,
      },
      {
        title: "Unique Job Titles",
        value: uniqueJobTitles,
        trend: { value: 0, direction: "neutral" as const },
        color: "coral" as const,
      },
      {
        title: "Overall Industry Trend",
        value: growthPct,
        suffix: "%",
        trend: { value: Math.abs(growthPct), direction: growthDir },
        color: "green" as const,
      },
      {
        title: "Median Annual Salary",
        value: medianSalary,
        prefix: "$",
        trend: { value: 0, direction: "neutral" as const },
        color: "amber" as const,
      },
    ];
  }, [metrics, uniqueJobTitles]);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">
            Job Market <span className="gradient-text">Overview</span>
          </h1>
          <p className="mt-1 text-muted-foreground">Real-time analytics across industries, jobs, and skills</p>
        </div>

        {loading && <p className="text-muted-foreground">Loading dashboard...</p>}
        {!loading && <MetricsGrid metrics={cards} showTrend={false} />}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Job Distributions by Industry"
                subtitle={`${year} employment breakdown (Top 10 + Others)`}
                action={{ label: "See More", href: "/industries" }}
              />
            </CardHeader>
            <CardContent className="min-h-[500px]">
              {donutData.length === 0 ? (
                <div className="text-muted-foreground">No industry data available</div>
              ) : (
                <DonutChart 
                  data={donutData} 
                  height={450} 
                  topListCount={10}
                  context="industry"
                  totalOverride={toNumber(metrics?.total_employment ?? metrics?.totalEmployment)}
                />
              )}
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Job Titles & Salary"
                subtitle="Cross-industry job titles by employment (Top 10)"
                action={{ label: "See More", href: "/industries" }}
              />
            </CardHeader>
            <CardContent className="min-h-[500px]">
              {topJobChartData.length === 0 ? (
                <div className="text-muted-foreground">No job data available</div>
              ) : (
                <HorizontalBarChart
                  data={topJobChartData}
                  showSecondary
                  primaryLabel="Employment"
                  secondaryLabel="Median Salary"
                />
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Employment per Industry Over Time"
              subtitle={`Top 10 industries by employment (2011-${year} time series)`}
              action={{ label: "View Trends", href: "/industries" }}
            />
          </CardHeader>
          <CardContent>
            {trend.data.length === 0 || trend.lines.length === 0 ? (
              <div className="text-muted-foreground">No trend data available</div>
            ) : (
              <>
                <div className="mb-2 text-xs text-muted-foreground text-center">
                  Showing {trend.data.length} years of historical data ({trend.data[0]?.year} - {trend.data[trend.data.length-1]?.year})
                </div>
                <MultiLineChart 
                  data={trend.data} 
                  xAxisKey="year" 
                  lines={trend.lines} 
                  height={400}
                  maxLines={10}
                />
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

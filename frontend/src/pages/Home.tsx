// src/pages/Home.tsx
import { useEffect, useMemo, useState } from "react";
import { DashboardLayout, useYear } from "@/components/layout";
import { MetricsGrid, SectionHeader } from "@/components/dashboard";
import { DonutChart, HorizontalBarChart, MultiLineChart } from "@/components/charts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const API_BASE = "http://127.0.0.1:8000/api";

// ---------- helpers ----------
const toNumber = (v: any): number => {
  if (v === null || v === undefined) return 0;
  if (typeof v === "number") return v;
  const n = parseFloat(String(v).replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
};

const safeKey = (naics: string) => `i_${String(naics).replace(/[^a-zA-Z0-9]/g, "_")}`;

// Deduplicate by NAICS code, keep first occurrence
const dedupeByNaics = (arr: any[]) => {
  const seen = new Set<string>();
  const out: any[] = [];
  for (const it of arr || []) {
    const k = String(it?.naics ?? "");
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
  const top = dedupeByNaics(topItems).slice(0, 6);
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
    for (const p of s?.points || []) years.add(Number(p.year));
  }
  const sortedYears = Array.from(years).filter((y) => Number.isFinite(y)).sort((a, b) => a - b);

  const data = sortedYears.map((y) => {
    const row: Record<string, any> = { year: y };
    for (const naics of topNaics) {
      const s = seriesByNaics.get(naics);
      const p = (s?.points || []).find((pt: any) => Number(pt?.year) === y);
      row[safeKey(naics)] = p ? toNumber(p?.employment) : null;
    }
    return row;
  });

  const palette = [
    "hsl(186 100% 50%)",
    "hsl(0 100% 71%)",
    "hsl(258 90% 76%)",
    "hsl(142 76% 45%)",
    "hsl(43 96% 56%)",
    "hsl(330 100% 65%)",
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

        // IMPORTANT:
        // /industries/ is your list endpoint (trailing slash avoids 307 redirect)
        const [mRes, listRes, topRes, trendsRes, topJobsRes] = await Promise.all([
          fetch(`${API_BASE}/industries/metrics/${year}`),
          fetch(`${API_BASE}/industries/?year=${year}`),
          fetch(`${API_BASE}/industries/top?year=${year}&limit=20&by=employment`), // grab more, then we dedupe+take 6
          fetch(`${API_BASE}/industries/top-trends?year_from=2019&year_to=${year}&limit=10`),
          fetch(`${API_BASE}/jobs/top?year=${year}&limit=6&by=employment`),
        ]);

        // If any response isn't ok, throw so we don't silently build empty charts
        if (!mRes.ok) throw new Error(`metrics failed: ${mRes.status}`);
        if (!listRes.ok) throw new Error(`industries list failed: ${listRes.status}`);
        if (!topRes.ok) throw new Error(`top industries failed: ${topRes.status}`);
        if (!trendsRes.ok) throw new Error(`top trends failed: ${trendsRes.status}`);
        if (!topJobsRes.ok) throw new Error(`top jobs failed: ${topJobsRes.status}`);

        const mJson = await mRes.json();
        const listJson = await listRes.json();
        const topJson = await topRes.json();
        const trendsJson = await trendsRes.json();
        const topJobsJson = await topJobsRes.json();

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

        const series = Array.isArray(trendsJson) ? trendsJson : trendsJson.series || [];
        setTopTrends(series);

        const topJobItems = Array.isArray(topJobsJson)
          ? topJobsJson
          : topJobsJson.jobs || topJobsJson.items || [];
        setTopJobs(topJobItems);

        // ---- trends aligned to top 6 industries ----
        const aligned = await buildTrendAligned(topItems, series, 2019, year);
        if (!cancelled) {
          setTrendData(aligned.data);
          setTrendLines(aligned.lines);
        }

        // ---- unique job titles (based on top industries, deduped) ----
        (async () => {
          try {
            const dedupTop = dedupeByNaics(topItems).slice(0, 8);
            if (!dedupTop.length) {
              if (!cancelled) setUniqueJobTitles(0);
              return;
            }

            const payloads = await Promise.all(
              dedupTop.map((it: any) =>
                fetch(`${API_BASE}/industries/${it.naics}/jobs?year=${year}&limit=5000`).then((r) => r.json())
              )
            );

            const titles = new Set<string>();
            for (const payload of payloads) {
              const jobs = payload?.jobs || [];
              for (const j of jobs) {
                const t = j?.occ_title;
                if (t) titles.add(String(t).trim());
              }
            }

            if (!cancelled) setUniqueJobTitles(titles.size);
          } catch (e) {
            console.error("unique job titles calc error:", e);
            if (!cancelled) setUniqueJobTitles(0);
          }
        })();
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

  // ✅ TOP 6 donut (dedupe by naics, then slice 6)
  const donutData = useMemo(() => {
    const srcRaw = topIndustries.length ? topIndustries : industryList;
    const src = dedupeByNaics(srcRaw).slice(0, 6);

    return src
      .map((it: any) => ({
        name: it.naics_title || it.name || "Unknown",
        value: toNumber(it.total_employment ?? it.employment ?? it.tot_emp ?? it.value),
      }))
      .filter((x) => x.value > 0);
  }, [topIndustries, industryList]);

  // ✅ TOP 6 job titles by employment (cross-industry), with median salary
  const topJobChartData = useMemo(() => {
    const src = (topJobs || []).slice(0, 6);
    return src.map((it: any) => ({
      name: it.occ_title || it.name || "Unknown",
      value: toNumber(it.total_employment ?? it.employment ?? it.tot_emp),
      secondaryValue: toNumber(it.median_salary ?? it.median_annual_wage ?? it.a_median ?? it.salary),
      fullName: it.occ_title || it.name || "Unknown",
    }));
  }, [topJobs]);

  // ✅ TOP 6 trend lines aligned to Top 6 industries
  const trend = useMemo(() => ({ data: trendData, lines: trendLines }), [trendData, trendLines]);

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
        value: `${growthPct.toFixed(1)}%`,
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
        {!loading && <MetricsGrid metrics={cards} />}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Job Distributions by Industry"
                subtitle={`${year} employment breakdown (Top 6)`}
                action={{ label: "See More", href: "/industries" }}
              />
            </CardHeader>
            <CardContent>
              <DonutChart data={donutData} />
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Job Titles & Salary"
                subtitle="Cross-industry job titles by employment (Top 6)"
                action={{ label: "See More", href: "/industries" }}
              />
            </CardHeader>
            <CardContent>
              <HorizontalBarChart
                data={topJobChartData}
                showSecondary
                primaryLabel="Employment"
                secondaryLabel="Median Salary"
              />
            </CardContent>
          </Card>
        </div>

        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Employment per Industry Over Time"
              subtitle="Top 6 industries by employment (time series)"
              action={{ label: "View Trends", href: "/industries" }}
            />
          </CardHeader>
          <CardContent>
            {trend.data.length === 0 || trend.lines.length === 0 ? (
              <div className="text-muted-foreground">No trend data</div>
            ) : (
              <MultiLineChart data={trend.data} xAxisKey="year" lines={trend.lines} height={300} />
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

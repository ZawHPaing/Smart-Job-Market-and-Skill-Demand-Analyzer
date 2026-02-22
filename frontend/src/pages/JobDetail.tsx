import { useEffect, useState, useMemo } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { ChevronLeft, Briefcase } from 'lucide-react';
import { DashboardLayout, useYear } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { JobDetailAPI } from '@/lib/jobDetail';
import { JobsAPI } from '@/lib/jobs';
import type { JobDetailResponse, JobMetric, JobSkill, JobAbility, JobKnowledge } from '@/lib/jobDetail';

// Helper functions
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtPercent = (n: number) => `${Math.round(n)}%`;

// Helper function to generate skill ID for routing
const getSkillId = (skillName: string): string => {
  return skillName
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '') // Remove special characters
    .replace(/\s+/g, '_') // Replace spaces with underscores
    .replace(/_+/g, '_') // Replace multiple underscores with single
    .replace(/^_|_$/g, ''); // Remove leading/trailing underscores
};

function RankedLineBars({
  data,
  maxValue = 100,
}: {
  data: { name: string; value: number }[];
  maxValue?: number;
}) {
  const safeMax = maxValue > 0 ? maxValue : 100;

  return (
    <div className="space-y-3">
      {(data || []).map((item, index) => {
        const width = Math.max(0, Math.min(100, (Number(item.value || 0) / safeMax) * 100));
        return (
          <div key={`${item.name}-${index}`} className="group">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium truncate max-w-[240px]" title={item.name}>
                {item.name}
              </span>
              <span className="text-cyan font-medium text-sm">{fmtPercent(item.value)}</span>
            </div>
            <div className="relative h-6 bg-secondary/50 rounded-lg overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded-lg border-2 border-coral/60 bg-transparent transition-all duration-700 ease-out"
                style={{ width: `${width}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

const JobDetail = () => {
  const { id } = useParams<{ id: string }>();
  const occ_code = id;
  const { year } = useYear();
  const location = useLocation();
  
  const [skillSort, setSkillSort] = useState('importance');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<JobDetailResponse | null>(null);
  const [employmentTrendData, setEmploymentTrendData] = useState<any[]>([]);
  const [salaryTrendData, setSalaryTrendData] = useState<any[]>([]);
  const [chartLines, setChartLines] = useState<{ key: string; name: string; color: string }[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadJobDetail() {
      if (!occ_code) {
        setError('No job code provided in URL');
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setError(null);

      console.log('🟡 Loading job detail for:', occ_code);

      try {
        const yearFrom = 2011;
        const [data, summary] = await Promise.all([
          JobDetailAPI.get(occ_code),
          JobsAPI.summary(occ_code, yearFrom, year),
        ]);
        if (cancelled) return;
        setJobDetail(data);

        const title = data?.occ_title || summary?.occ_title || occ_code;
        const lineKey = occ_code;
        setChartLines([
          {
            key: lineKey,
            name: title.length > 30 ? title.substring(0, 30) + '...' : title,
            color: 'hsl(186 100% 50%)',
          },
        ]);

        if (summary?.series?.length) {
          const rowsEmployment = summary.series.map((p) => ({
            year: p.year,
            [lineKey]: p.total_employment ?? 0,
          }));
          const rowsSalary = summary.series.map((p) => ({
            year: p.year,
            [lineKey]: p.a_median ?? 0,
          }));
          setEmploymentTrendData(rowsEmployment);
          setSalaryTrendData(rowsSalary);
        } else {
          setEmploymentTrendData([]);
          setSalaryTrendData([]);
        }

        console.log('🟢 Job detail loaded:', data);
        console.log('🟢 Skills count:', data.skills?.length);
        console.log('🟢 Tech skills count:', data.tech_skills?.length);
        console.log('🟢 Soft skills count:', data.soft_skills?.length);
        console.log('🟢 Activities count:', data.activities?.length);
        console.log('🟢 Abilities count:', data.abilities?.length);
        console.log('🟢 Knowledge count:', data.knowledge?.length);
        console.log('🟢 Tools count:', data.tools?.length);
      } catch (e: any) {
        if (cancelled) return;
        console.error('🔴 Job detail error:', e);
        setError(e?.message || 'Failed to load job details');
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    }

    loadJobDetail();
    return () => { cancelled = true; };
  }, [occ_code, year]);

  // Transform metrics for MetricsGrid component
  const metricsGridData = useMemo(() => {
    if (!jobDetail?.metrics) return [];
    
    return jobDetail.metrics.map((metric: JobMetric) => {
      let formattedValue = metric.value;
      let shouldUseCustomFormatting = false;
      
      // Handle different format types
      if (metric.format === 'fmtK' && typeof metric.value === 'number') {
        formattedValue = metric.value;
        shouldUseCustomFormatting = true;
      } else if (metric.format === 'fmtPercent' && typeof metric.value === 'number') {
        formattedValue = Math.round(metric.value) + '%';
      } else if (metric.format === 'fmtM' && typeof metric.value === 'number') {
        formattedValue = metric.value;
        shouldUseCustomFormatting = true;
      }
      
      // Special handling for Job Trend - add % suffix
      if (metric.title === "Job Trend") {
        // If it's already a string with % sign, keep it, otherwise format
        if (typeof metric.value === 'string' && metric.value.includes('%')) {
          formattedValue = metric.value;
        } else if (typeof metric.value === 'number') {
          formattedValue = `${metric.value > 0 ? '+' : ''}${metric.value}%`;
        }
      }
      
      return {
        title: metric.title,
        value: formattedValue,
        prefix: metric.prefix,
        suffix: shouldUseCustomFormatting ? '' : metric.suffix,
        trend: metric.trend ? {
          value: Math.abs(metric.trend.value),
          direction: metric.trend.direction as "up" | "down" | "neutral"
        } : undefined,
        color: metric.color || 'cyan'
      };
    }).filter(metric => metric.title !== "Experience Required"); // Filter out Experience Required
  }, [jobDetail]);

  // Format skills for chart - show all skills but limit display to prevent overcrowding
  const jobSkills = useMemo(() => {
    if (!jobDetail?.skills) return [];
    return jobDetail.skills
      .filter((skill) => String(skill?.name || "").trim().length > 0)
      .map((skill) => ({
        name: skill.name.length > 30 ? skill.name.substring(0, 30) + "..." : skill.name,
        value: Math.round(skill.value),
        type: skill.type,
      }));
  }, [jobDetail]);

  // Tech skills - all of them
  const techSkills = jobDetail?.tech_skills || [];
  
  // Soft skills - all of them
  const softSkills = jobDetail?.soft_skills || [];

  // Activities - all of them
  const activities = useMemo(() => {
    if (!jobDetail?.activities) return [];
    return jobDetail.activities
      .filter((activity) => String(activity?.name || "").trim().length > 0)
      .map((activity) => ({
        name: activity.name.length > 30 ? activity.name.substring(0, 30) + "..." : activity.name,
        value: Math.round(activity.value),
      }));
  }, [jobDetail]);

  // Abilities - all of them
  const abilities = jobDetail?.abilities || [];

  // Knowledge - all of them
  const knowledge = jobDetail?.knowledge || [];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan"></div>
          <div className="text-muted-foreground">Loading job details for {occ_code}...</div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !jobDetail) {
    return (
      <DashboardLayout>
        <div className="space-y-4">
          <Link
            to="/jobs"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Jobs
          </Link>
          <Card className="glass-card border-coral/30">
            <CardContent className="p-6">
              <div className="space-y-2">
                <p className="text-coral font-semibold">Error Loading Job Details</p>
                <p className="text-sm text-muted-foreground">{error || 'Job not found'}</p>
                <p className="text-xs text-muted-foreground mt-2">Job Code: {occ_code}</p>
                <Link 
                  to="/jobs" 
                  className="inline-block mt-4 px-4 py-2 bg-secondary/50 rounded-lg text-sm hover:bg-secondary/70 transition-colors"
                >
                  Browse All Jobs
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Back Button & Header */}
        <div>
          <Link
            to="/jobs"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Jobs
          </Link>
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan to-purple">
              <Briefcase className="h-6 w-6 text-background" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold tracking-tight">
                {jobDetail.occ_title}
              </h1>
              <div className="flex items-center gap-3 mt-1">
                <p className="text-muted-foreground">
                  SOC: {jobDetail.basic_info.soc_code || jobDetail.occ_code}
                </p>
                {jobDetail.education && (
                  <Badge variant="outline" className="text-xs">
                    {jobDetail.education.description}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        {metricsGridData.length > 0 ? (
          <MetricsGrid metrics={metricsGridData} showTrend={false} />
        ) : (
          <Card className="glass-card">
            <CardContent className="p-4 text-center text-muted-foreground">
              No metrics data available
            </CardContent>
          </Card>
        )}

        {/* Job Trends Over Time */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Job Trends Over Time"
              subtitle={`Employment and salary trends for this job (2011-${year})`}
            />
          </CardHeader>
          <CardContent>
            <Tabs
              defaultValue="employment"
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="employment">Employment Trends</TabsTrigger>
                <TabsTrigger value="salary">Salary Trends</TabsTrigger>
              </TabsList>

              <TabsContent value="employment">
                {employmentTrendData.length > 0 && chartLines.length > 0 ? (
                  <>
                    <div className="mb-2 text-xs text-muted-foreground text-center">
                      Showing {employmentTrendData.length} years of historical data (
                      {employmentTrendData[0]?.year} - {employmentTrendData[employmentTrendData.length - 1]?.year})
                    </div>
                    <MultiLineChart
                      data={employmentTrendData}
                      xAxisKey="year"
                      lines={chartLines}
                      height={300}
                      maxLines={1}
                    />
                  </>
                ) : (
                  <div className="text-muted-foreground text-center py-8">
                    No employment trend data available
                  </div>
                )}
              </TabsContent>

              <TabsContent value="salary">
                {salaryTrendData.length > 0 && chartLines.length > 0 ? (
                  <>
                    <div className="mb-2 text-xs text-muted-foreground text-center">
                      Showing {salaryTrendData.length} years of historical data (
                      {salaryTrendData[0]?.year} - {salaryTrendData[salaryTrendData.length - 1]?.year})
                    </div>
                    <MultiLineChart
                      data={salaryTrendData}
                      xAxisKey="year"
                      lines={chartLines}
                      height={300}
                      maxLines={1}
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

        {/* Skills Section */}
        <div className="grid items-stretch gap-6 lg:grid-cols-2">
          {/* Top Skills - FULL HEIGHT */}
          <Card className="glass-card h-full flex flex-col">
            <CardHeader>
              <SectionHeader 
                title="Top Skills Required" 
                subtitle={`${jobSkills.length} skills ranked by importance`}
              >
                <Select value={skillSort} onValueChange={setSkillSort}>
                  <SelectTrigger className="w-[140px] bg-secondary/50">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="importance">Importance</SelectItem>
                    <SelectItem value="demand">Demand</SelectItem>
                  </SelectContent>
                </Select>
              </SectionHeader>
            </CardHeader>
            <CardContent className="flex-1">
              {jobSkills.length > 0 ? (
                <>
                  <div 
                    className="h-[500px] overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                    style={{
                      scrollbarWidth: 'thin',
                      msOverflowStyle: 'auto',
                    }}
                  >
                    <RankedLineBars data={jobSkills} maxValue={100} />
                  </div>
                  <div className="text-xs text-muted-foreground mt-2 text-center border-t border-border/50 pt-2">
                    Showing all {jobSkills.length} skills
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No skills data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top Tech Skills - FULL HEIGHT */}
          <Card className="glass-card h-full flex flex-col">
            <CardHeader>
              <SectionHeader
                title="Top Tech Skills"
                subtitle={`${techSkills.length} technical competencies in demand`}
              />
            </CardHeader>
            <CardContent className="flex-1">
              {techSkills.length > 0 ? (
                <>
                  <div 
                    className="h-[300px] overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                    style={{
                      scrollbarWidth: 'thin',
                      msOverflowStyle: 'auto',
                    }}
                  >
                    {techSkills.map((skill) => {
                      const skillId = getSkillId(skill.name);
                      return (
                        <Link 
                          key={skill.name} 
                          to={`/skills/${skillId}`}
                          state={{ from: location.pathname }}
                          className="block group"
                        >
                          <div className={`p-3 rounded-lg transition-colors ${
                            skill.hot_technology 
                              ? 'bg-cyan/5 hover:bg-cyan/10 border border-cyan/20' 
                              : 'bg-secondary/20 hover:bg-secondary/30'
                          }`}>
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-medium text-sm group-hover:text-cyan transition-colors">
                                  {skill.name}
                                </span>
                                {skill.hot_technology && (
                                  <Badge variant="outline" className="text-xs bg-cyan/10 text-cyan border-cyan/20">
                                    🔥 Hot
                                  </Badge>
                                )}
                                {skill.in_demand && (
                                  <Badge variant="outline" className="text-xs bg-green/10 text-green border-green/20">
                                    📈 In Demand
                                  </Badge>
                                )}
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {Math.round(skill.value)}%
                              </span>
                            </div>
                            {skill.commodity_title && (
                              <p className="text-xs text-muted-foreground mb-2">
                                {skill.commodity_title}
                              </p>
                            )}
                            <div className="w-full bg-secondary/30 rounded-full h-1.5">
                              <div 
                                className={`rounded-full h-1.5 transition-all ${
                                  skill.hot_technology ? 'bg-cyan' : 'bg-purple'
                                }`}
                                style={{ width: `${skill.value}%` }}
                              />
                            </div>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                  
                  <div className="mt-3 text-xs text-muted-foreground text-right border-t border-border/50 pt-2">
                    Showing all {techSkills.length} tech skills
                  </div>

                  {/* Soft Skills Section */}
                  {softSkills.length > 0 && (
                    <div className="mt-6">
                      <h4 className="text-sm font-medium mb-3">Soft Skills ({softSkills.length})</h4>
                      <div 
                        className="h-[200px] overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                        style={{
                          scrollbarWidth: 'thin',
                          msOverflowStyle: 'auto',
                        }}
                      >
                        {softSkills.map((skill) => {
                          const skillId = getSkillId(skill.name);
                          return (
                            <Link 
                              key={skill.name} 
                              to={`/skills/${skillId}`}
                              state={{ from: location.pathname }}
                              className="block group"
                            >
                              <div className="p-2 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                                <div className="flex items-center justify-between">
                                  <span className="text-sm group-hover:text-cyan transition-colors">
                                    {skill.name}
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    {Math.round(skill.value)}%
                                  </span>
                                </div>
                                <div className="mt-1 w-full bg-secondary/30 rounded-full h-1">
                                  <div 
                                    className="bg-green rounded-full h-1"
                                    style={{ width: `${skill.value}%` }}
                                  />
                                </div>
                              </div>
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No technology skills data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Activities & Abilities */}
        <div className="grid items-stretch gap-6 lg:grid-cols-2">
          {/* Top Activities - FULL HEIGHT */}
          <Card className="glass-card h-full flex flex-col">
            <CardHeader>
              <SectionHeader
                title="Top Activities"
                subtitle={`${activities.length} primary work activities for this role`}
              />
            </CardHeader>
            <CardContent className="flex-1">
              {activities.length > 0 ? (
                <>
                  <div 
                    className="h-[500px] overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                    style={{
                      scrollbarWidth: 'thin',
                      msOverflowStyle: 'auto',
                    }}
                  >
                    <RankedLineBars data={activities} maxValue={100} />
                  </div>
                  <div className="text-xs text-muted-foreground mt-2 text-center border-t border-border/50 pt-2">
                    Showing all {activities.length} activities
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No activities data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Abilities - FULL HEIGHT */}
          <Card className="glass-card h-full flex flex-col">
            <CardHeader>
              <SectionHeader
                title="Top Abilities"
                subtitle={`${abilities.length} key competencies required`}
              />
            </CardHeader>
            <CardContent className="flex-1">
              {abilities.length > 0 ? (
                <>
                  <div 
                    className="h-[400px] overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                    style={{
                      scrollbarWidth: 'thin',
                      msOverflowStyle: 'auto',
                    }}
                  >
                    <div className="grid gap-3 sm:grid-cols-2">
                      {abilities.map((ability) => {
                        const skillId = getSkillId(ability.name);
                        return (
                          <Link 
                            key={ability.name} 
                            to={`/skills/${skillId}`}
                            state={{ from: location.pathname }}
                            className="p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors block group"
                          >
                            <p className="font-medium text-sm group-hover:text-cyan transition-colors">
                              {ability.name}
                            </p>
                            <p className="text-xs text-muted-foreground">{ability.category}</p>
                            <div className="mt-1 w-full bg-secondary/50 rounded-full h-1">
                              <div 
                                className="bg-cyan rounded-full h-1" 
                                style={{ width: `${ability.value}%` }}
                              />
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-2 text-right border-t border-border/50 pt-2">
                    Showing all {abilities.length} abilities
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No abilities data available
                </div>
              )}

              {/* Knowledge Section */}
              {knowledge.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium mb-3">Necessary Knowledge ({knowledge.length})</h4>
                  <div 
                    className="h-[200px] overflow-y-auto pr-2 space-y-2 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                    style={{
                      scrollbarWidth: 'thin',
                      msOverflowStyle: 'auto',
                    }}
                  >
                    {knowledge.map((k) => {
                      const skillId = getSkillId(k.name);
                      return (
                        <Link
                          key={k.name}
                          to={`/skills/${skillId}`}
                          state={{ from: location.pathname }}
                          className="flex items-center justify-between p-2 rounded bg-secondary/20 hover:bg-secondary/30 transition-colors group"
                        >
                          <span className="text-sm group-hover:text-cyan transition-colors">{k.name}</span>
                          <Badge variant="outline" className="text-xs">
                            {k.level}
                          </Badge>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Tools Section - SCROLLABLE */}
        {jobDetail.tools && jobDetail.tools.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Tools Used"
                subtitle={`${jobDetail.tools.length} common tools and technologies for this role`}
              />
            </CardHeader>
            <CardContent>
              <div 
                className="max-h-[400px] overflow-y-auto p-2 flex flex-wrap gap-2 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                style={{
                  scrollbarWidth: 'thin',
                  msOverflowStyle: 'auto',
                }}
              >
                {jobDetail.tools.map((tool) => {
                  const skillId = getSkillId(tool.name);
                  return (
                    <Link 
                      key={tool.name} 
                      to={`/skills/${skillId}`}
                      state={{ from: location.pathname }}
                      className="inline-block"
                    >
                      <Badge
                        variant="outline"
                        className="px-3 py-2 text-sm bg-secondary/20 hover:bg-secondary/30 cursor-pointer transition-colors"
                      >
                        {tool.name}
                        {tool.commodity_title && (
                          <span className="ml-2 text-xs text-muted-foreground">
                            {tool.commodity_title}
                          </span>
                        )}
                      </Badge>
                    </Link>
                  );
                })}
              </div>
              <div className="text-xs text-muted-foreground mt-2 text-right border-t border-border/50 pt-2">
                Showing all {jobDetail.tools.length} tools
              </div>
            </CardContent>
          </Card>
        )}

        {/* Debug Info - Only in development */}
        {process.env.NODE_ENV === 'development' && (
          <Card className="glass-card border-amber/30">
            <CardHeader>
              <SectionHeader title="Debug Info" subtitle="Remove in production" />
            </CardHeader>
            <CardContent>
              <div className="space-y-1 text-xs max-h-[300px] overflow-y-auto">
                <p><span className="font-bold">Job Code:</span> {jobDetail.occ_code}</p>
                <p><span className="font-bold">Job Title:</span> {jobDetail.occ_title}</p>
                <p><span className="font-bold">SOC Code:</span> {jobDetail.basic_info.soc_code || 'N/A'}</p>
                <p><span className="font-bold">Skills Count:</span> {jobDetail.skills.length}</p>
                <p><span className="font-bold">Tech Skills Count:</span> {jobDetail.tech_skills.length}</p>
                <p><span className="font-bold">Soft Skills Count:</span> {jobDetail.soft_skills.length}</p>
                <p><span className="font-bold">Activities Count:</span> {jobDetail.activities.length}</p>
                <p><span className="font-bold">Abilities Count:</span> {jobDetail.abilities.length}</p>
                <p><span className="font-bold">Knowledge Count:</span> {jobDetail.knowledge.length}</p>
                <p><span className="font-bold">Tools Count:</span> {jobDetail.tools.length}</p>
                <p><span className="font-bold">Has Education:</span> {jobDetail.education ? 'Yes' : 'No'}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default JobDetail;
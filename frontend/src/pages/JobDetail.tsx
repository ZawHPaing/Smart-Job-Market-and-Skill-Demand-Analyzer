import { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, Briefcase } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { HorizontalBarChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { JobDetailAPI } from '@/lib/jobDetail';
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

const JobDetail = () => {
  const { id } = useParams<{ id: string }>();
  const occ_code = id;
  
  const [skillSort, setSkillSort] = useState('importance');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<JobDetailResponse | null>(null);

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
        const data = await JobDetailAPI.get(occ_code);
        if (cancelled) return;
        setJobDetail(data);
        console.log('🟢 Job detail loaded:', data);
        console.log('🟢 Knowledge count:', data.knowledge?.length);
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
  }, [occ_code]);

  // Transform metrics for MetricsGrid component
  const metricsGridData = useMemo(() => {
    if (!jobDetail?.metrics) return [];
    
    return jobDetail.metrics.map((metric: JobMetric) => {
      let formattedValue = metric.value;
      if (metric.format === 'fmtK' && typeof metric.value === 'number') {
        formattedValue = fmtK(metric.value);
      } else if (metric.format === 'fmtPercent' && typeof metric.value === 'number') {
        formattedValue = fmtPercent(metric.value);
      }
      
      return {
        title: metric.title,
        value: formattedValue,
        prefix: metric.prefix,
        suffix: metric.suffix,
        trend: metric.trend ? {
          value: Math.abs(metric.trend.value),
          direction: metric.trend.direction as "up" | "down" | "neutral"
        } : undefined,
        color: metric.color || 'cyan'
      };
    });
  }, [jobDetail]);

  // Format skills for chart - get 10 items
  const jobSkills = useMemo(() => {
    if (!jobDetail?.skills) return [];
    return jobDetail.skills.slice(0, 10).map(skill => ({
      name: skill.name.length > 30 ? skill.name.substring(0, 30) + '...' : skill.name,
      value: Math.round(skill.value),
      type: skill.type,
    }));
  }, [jobDetail]);

  // Tech and soft skills - get 10 each
  const techSkills = jobDetail?.tech_skills?.slice(0, 10) || [];
  
  // Soft skills now come from the skills list (already filtered in backend)
  const softSkills = jobDetail?.soft_skills?.slice(0, 10) || [];

  // Activities for chart - get 10 items
  const activities = useMemo(() => {
    if (!jobDetail?.activities) return [];
    return jobDetail.activities.slice(0, 10).map(activity => ({
      name: activity.name.length > 30 ? activity.name.substring(0, 30) + '...' : activity.name,
      value: Math.round(activity.value),
    }));
  }, [jobDetail]);

  // Abilities - get 10
  const abilities = jobDetail?.abilities?.slice(0, 10) || [];

  // Knowledge - get 10 (increased from 6)
  const knowledge = jobDetail?.knowledge?.slice(0, 10) || [];

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
          <MetricsGrid metrics={metricsGridData} />
        ) : (
          <Card className="glass-card">
            <CardContent className="p-4 text-center text-muted-foreground">
              No metrics data available
            </CardContent>
          </Card>
        )}

        {/* Skills Section */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Top Skills */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader title="Top Skills Required" subtitle="Ranked by importance">
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
            <CardContent>
              {jobSkills.length > 0 ? (
                <>
                  <HorizontalBarChart
                    data={jobSkills}
                    formatValue={(v) => `${Math.round(v)}%`}
                    primaryLabel="Importance"
                    maxValue={100} // ADD THIS LINE
                  />
                  <div className="text-xs text-muted-foreground mt-2 text-center">
                    Showing {jobSkills.length} skills
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No skills data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top Tech Skills */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Tech Skills"
                subtitle="Technical competencies in demand"
              />
            </CardHeader>
            <CardContent>
              {techSkills.length > 0 ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    {techSkills.map((skill) => {
                      const skillId = getSkillId(skill.name);
                      return (
                        <Link 
                          key={skill.name} 
                          to={`/skills/${skillId}`}
                          className="inline-block"
                        >
                          <Badge
                            variant="secondary"
                            className={`px-3 py-2 text-sm ${
                              skill.hot_technology 
                                ? 'bg-cyan/10 text-cyan border-cyan/20 hover:bg-cyan/20' 
                                : 'bg-secondary/30 hover:bg-secondary/50'
                            } cursor-pointer transition-colors`}
                          >
                            {skill.name}
                            {skill.hot_technology && (
                              <span className="ml-2 text-xs text-cyan">🔥</span>
                            )}
                          </Badge>
                        </Link>
                      );
                    })}
                  </div>
                  <div className="text-xs text-muted-foreground mt-2 text-right">
                    {techSkills.length} tech skills
                  </div>

                  {softSkills.length > 0 && (
                    <div className="mt-6">
                      <h4 className="text-sm font-medium mb-3">Soft Skills (from top skills)</h4>
                      <div className="flex flex-wrap gap-2">
                        {softSkills.map((skill) => {
                          const skillId = getSkillId(skill.name);
                          return (
                            <Link 
                              key={skill.name} 
                              to={`/skills/${skillId}`}
                              className="inline-block"
                            >
                              <Badge
                                variant="outline"
                                className="px-3 py-2 text-sm hover:bg-secondary/40 cursor-pointer transition-colors"
                              >
                                {skill.name}
                                <span className="ml-1 text-xs text-muted-foreground">
                                  {Math.round(skill.value)}%
                                </span>
                              </Badge>
                            </Link>
                          );
                        })}
                      </div>
                      <div className="text-xs text-muted-foreground mt-2 text-right">
                        {softSkills.length} soft skills
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
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Top Activities */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Activities"
                subtitle="Primary work activities for this role"
              />
            </CardHeader>
            <CardContent>
              {activities.length > 0 ? (
                <>
                  <HorizontalBarChart
                    data={activities}
                    formatValue={(v) => `${Math.round(v)}%`}
                    primaryLabel="Importance"
                    maxValue={100} // ADD THIS LINE
                  />
                  <div className="text-xs text-muted-foreground mt-2 text-center">
                    Showing {activities.length} activities
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No activities data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Abilities & Knowledge */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Abilities"
                subtitle="Key competencies required"
              />
            </CardHeader>
            <CardContent>
              {abilities.length > 0 ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {abilities.map((ability) => {
                      const skillId = getSkillId(ability.name);
                      return (
                        <Link 
                          key={ability.name} 
                          to={`/skills/${skillId}`}
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
                  <div className="text-xs text-muted-foreground mt-2 text-right">
                    {abilities.length} abilities
                  </div>
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No abilities data available
                </div>
              )}

              {knowledge.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium mb-3">Necessary Knowledge</h4>
                  <div className="space-y-2">
                    {knowledge.map((k) => {
                      const skillId = getSkillId(k.name);
                      return (
                        <Link
                          key={k.name}
                          to={`/skills/${skillId}`}
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
                  <div className="text-xs text-muted-foreground mt-2 text-right">
                    {knowledge.length} knowledge areas
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Tools Section */}
        {jobDetail.tools && jobDetail.tools.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Tools Used"
                subtitle="Common tools and technologies for this role"
              />
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {jobDetail.tools.map((tool) => {
                  const skillId = getSkillId(tool.name);
                  return (
                    <Link 
                      key={tool.name} 
                      to={`/skills/${skillId}`}
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
              <div className="text-xs text-muted-foreground mt-2 text-right">
                {jobDetail.tools.length} tools
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
              <div className="space-y-1 text-xs">
                <p><span className="font-bold">Job Code:</span> {jobDetail.occ_code}</p>
                <p><span className="font-bold">Job Title:</span> {jobDetail.occ_title}</p>
                <p><span className="font-bold">SOC Code:</span> {jobDetail.basic_info.soc_code || 'N/A'}</p>
                <p><span className="font-bold">Skills Count:</span> {jobDetail.skills.length}</p>
                <p><span className="font-bold">Skills (first 3):</span> {jobDetail.skills.slice(0,3).map(s => s.name).join(', ')}</p>
                <p><span className="font-bold">Skills Values:</span> {jobDetail.skills.slice(0,3).map(s => Math.round(s.value)).join('%, ')}%</p>
                <p><span className="font-bold">Tech Skills:</span> {jobDetail.tech_skills.length}</p>
                <p><span className="font-bold">Soft Skills (from skills list):</span> {jobDetail.soft_skills.length}</p>
                <p><span className="font-bold">Activities Count:</span> {jobDetail.activities.length}</p>
                <p><span className="font-bold">Activities (first 3):</span> {jobDetail.activities.slice(0,3).map(a => a.name).join(', ')}</p>
                <p><span className="font-bold">Activities Values:</span> {jobDetail.activities.slice(0,3).map(a => Math.round(a.value)).join('%, ')}%</p>
                <p><span className="font-bold">Abilities:</span> {jobDetail.abilities.length}</p>
                <p><span className="font-bold">Knowledge:</span> {jobDetail.knowledge.length}</p>
                <p><span className="font-bold">Knowledge (first 3):</span> {jobDetail.knowledge.slice(0,3).map(k => k.name).join(', ')}</p>
                <p><span className="font-bold">Tools:</span> {jobDetail.tools.length}</p>
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
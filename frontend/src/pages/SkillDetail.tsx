import { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, Code, Briefcase } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { DonutChart, SkillNetworkGraph, HorizontalBarChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SkillsAPI } from '@/lib/skills'; // ✅ IMPORTING THE CORRECT API
import type { SkillDetailResponse, CoOccurringSkill, JobRequiringSkill } from '@/lib/skills';

// Helper functions
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtPercent = (n: number) => `${Math.round(n)}%`;

const SkillDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skillDetail, setSkillDetail] = useState<SkillDetailResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSkillDetail() {
      if (!id) {
        setError('No skill ID provided');
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setError(null);

      console.log('🟡 Loading skill detail for ID:', id);
      console.log('🟡 API URL:', `/skills/${encodeURIComponent(id)}`);

      try {
        // ✅ USING THE CORRECT API - SkillsAPI.getDetail, NOT JobDetailAPI
        const data = await SkillsAPI.getDetail(id);
        if (cancelled) return;
        console.log('🟢 Skill detail loaded:', data);
        setSkillDetail(data);
      } catch (e: any) {
        console.error('🔴 Skill detail error:', e);
        if (cancelled) return;
        setError(e?.message || 'Failed to load skill details');
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    }

    loadSkillDetail();
    return () => { cancelled = true; };
  }, [id]);

  // Transform metrics for MetricsGrid
  const metricsGridData = useMemo(() => {
    if (!skillDetail?.metrics) return [];
    
    return skillDetail.metrics.map((metric: any) => {
      let value = metric.value;
      if (metric.format === 'fmtK' && typeof metric.value === 'number') {
        value = fmtK(metric.value);
      } else if (metric.format === 'fmtPercent' && typeof metric.value === 'number') {
        value = fmtPercent(metric.value);
      }
      
      return {
        title: metric.title,
        value,
        suffix: metric.suffix,
        prefix: metric.prefix,
        trend: metric.trend ? {
          value: Math.abs(metric.trend.value),
          direction: metric.trend.direction as "up" | "down" | "neutral"
        } : undefined,
        color: metric.color || 'cyan'
      };
    });
  }, [skillDetail]);

  // Prepare data for donut chart
  const usageData = skillDetail?.usage_data || [
    { name: 'Jobs Requiring', value: 0, color: 'hsl(186 100% 50%)' },
    { name: 'Jobs Not Requiring', value: 100, color: 'hsl(0 0% 25%)' }
  ];

  // Prepare network graph data
  const networkData = useMemo(() => {
  if (!skillDetail) {
    return {
      nodes: [{ 
        id: id || 'skill', 
        name: 'Skill', 
        group: '1',  // Changed from number 1 to string '1'
        value: 20 
      }],
      links: []
    };
  }
  
  return {
    nodes: [
      { 
        id: skillDetail.basic_info.skill_id, 
        name: skillDetail.basic_info.skill_name, 
        group: '1',  // Changed from number 1 to string '1'
        value: 20 
      },
      ...skillDetail.co_occurring_skills.slice(0, 5).map((s, i) => ({
        id: s.id,
        name: s.name.length > 20 ? s.name.substring(0, 20) + '...' : s.name,
        group: '2',  // Changed from number 2 to string '2'
        value: 15 - i
      }))
    ],
    links: skillDetail.co_occurring_skills.slice(0, 5).map(s => ({
      source: skillDetail.basic_info.skill_id,
      target: s.id,
      value: s.co_occurrence_rate || 50
    }))
  };
}, [skillDetail, id]);

  // Get top co-occurring skills for "What to Learn Next"
  const nextSkills = useMemo(() => {
    return skillDetail?.co_occurring_skills?.slice(0, 4) || [];
  }, [skillDetail]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan"></div>
          <div className="text-muted-foreground">Loading skill details...</div>
          <div className="text-xs text-muted-foreground">Skill ID: {id}</div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !skillDetail) {
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
                <p className="text-coral font-semibold">Skill Not Found</p>
                <p className="text-sm text-muted-foreground">
                  {error || `No skill found with ID: ${id}`}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  The skill you're looking for might not be in our database yet.
                </p>
                <Link 
                  to="/jobs" 
                  className="inline-block mt-4 px-4 py-2 bg-secondary/50 rounded-lg text-sm hover:bg-secondary/70 transition-colors"
                >
                  Browse Jobs
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
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple to-coral">
              <Code className="h-6 w-6 text-background" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold tracking-tight">
                {skillDetail.basic_info.skill_name}
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-xs">
                  {skillDetail.basic_info.skill_type.replace('_', ' ').toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {skillDetail.total_jobs_count?.toLocaleString() || 0} jobs analyzed
                </span>
              </div>
              {skillDetail.basic_info.description && (
                <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
                  {skillDetail.basic_info.description}
                </p>
              )}
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

        {/* Skill Usage & Network */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Skill Usage Ring */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Skill Usage"
                subtitle="Percentage of jobs requiring this skill"
              />
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <div className="relative">
                <DonutChart
                  data={usageData}
                  innerRadius={80}
                  outerRadius={110}
                  showLabels={false}
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-cyan">
                    {skillDetail.usage_percentage || 0}%
                  </span>
                  <span className="text-sm text-muted-foreground">of jobs</span>
                </div>
              </div>
              <p className="mt-4 text-center text-muted-foreground">
                {skillDetail.usage_percentage || 0}% of analyzed job postings require {skillDetail.basic_info.skill_name}
              </p>
            </CardContent>
          </Card>

          {/* Co-Occurring Skills Network */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Co-Occurring Skills"
                subtitle="Skills frequently paired with this one"
              />
            </CardHeader>
            <CardContent className="flex justify-center">
              {networkData.nodes.length > 1 ? (
                <SkillNetworkGraph
                  nodes={networkData.nodes}
                  links={networkData.links}
                  centerNode={skillDetail.basic_info.skill_id}
                  width={350}
                  height={350}
                />
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No co-occurring skills data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* What to Learn Next */}
        {nextSkills.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="What Skills to Learn Next?"
                subtitle="Recommended skills to complement your expertise"
              />
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {nextSkills.map((skill) => (
                  <Link
                    key={skill.id}
                    to={`/skills/${skill.id}`}
                    className="group p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 border border-transparent hover:border-cyan/30 transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple/20">
                        <Briefcase className="h-5 w-5 text-purple" />
                      </div>
                      <Badge
                        variant="secondary"
                        className={`text-xs ${
                          skill.type === 'tech' ? 'bg-cyan/10 text-cyan' : 
                          skill.type === 'soft' ? 'bg-green/10 text-green' : 
                          'bg-purple/10 text-purple'
                        }`}
                      >
                        {skill.type}
                      </Badge>
                    </div>
                    <h4 className="mt-3 font-medium group-hover:text-cyan transition-colors">
                      {skill.name}
                    </h4>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Co-occurs in {skill.co_occurrence_rate || 0}% of jobs
                    </p>
                    {skill.salary_association && (
                      <p className="text-sm text-green-500">
                        ${(skill.salary_association / 1000).toFixed(0)}K avg salary
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Top Jobs Using This Skill */}
        {skillDetail.top_jobs && skillDetail.top_jobs.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Jobs Using This Skill"
                subtitle="Roles where this skill is highly valued"
              />
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {skillDetail.top_jobs.slice(0, 6).map((job) => (
                  <Link
                    key={job.soc_code}
                    to={`/jobs/${job.soc_code.replace('.00', '')}`}
                    className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors group"
                  >
                    <div>
                      <p className="font-medium group-hover:text-cyan transition-colors">
                        {job.title}
                      </p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>Importance: {Math.round(job.importance || 0)}%</span>
                        {job.level && <span>• Level: {Math.round(job.level)}%</span>}
                      </div>
                    </div>
                    {job.median_salary && (
                      <span className="text-cyan font-medium">
                        ${(job.median_salary / 1000).toFixed(0)}K
                      </span>
                    )}
                  </Link>
                ))}
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
              <div className="space-y-2">
                <p className="text-xs">
                  <span className="font-bold">Skill ID:</span> {skillDetail.basic_info.skill_id}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Skill Name:</span> {skillDetail.basic_info.skill_name}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Type:</span> {skillDetail.basic_info.skill_type}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Co-occurring Skills:</span> {skillDetail.co_occurring_skills.length}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Top Jobs:</span> {skillDetail.top_jobs.length}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Usage Percentage:</span> {skillDetail.usage_percentage}%
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default SkillDetail;
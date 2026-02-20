import { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, Code, Briefcase, TrendingUp, Users, Calendar } from 'lucide-react';
import { DashboardLayout, useYear } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { DonutChart, SkillNetworkGraph } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SkillsAPI } from '@/lib/skills';
import type { SkillDetailResponse, CoOccurringSkill } from '@/lib/skills';

// Helper functions
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtNumber = (n: number) => n.toLocaleString();

const SkillDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { year } = useYear();
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

      try {
        console.log(`🔍 Fetching skill detail for ID: ${id} with year: ${year}`);
        const data = await SkillsAPI.getDetail(id, year);
        if (cancelled) return;
        console.log('✅ Skill detail received:', data);
        setSkillDetail(data);
      } catch (e: any) {
        console.error('❌ Skill detail error:', e);
        if (cancelled) return;
        setError(e?.message || 'Failed to load skill details');
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    }

    loadSkillDetail();
    return () => { cancelled = true; };
  }, [id, year]);

  // Debug effect to log co-occurring skills data
  useEffect(() => {
    if (skillDetail) {
      console.log('=== SKILL DETAIL DEBUG ===');
      console.log('Skill name:', skillDetail.basic_info.skill_name);
      console.log('Skill type:', skillDetail.basic_info.skill_type);
      console.log('Year:', skillDetail.year);
      console.log('Total jobs count:', skillDetail.total_jobs_count);
      console.log('Usage percentage:', skillDetail.usage_percentage);
      
      console.log('\n📊 CO-OCCURRING SKILLS:');
      console.log('Array length:', skillDetail.co_occurring_skills?.length || 0);
      
      console.log('\n📈 METRICS:');
      console.log(skillDetail.metrics);
      
      console.log('\n🔗 NETWORK GRAPH:');
      console.log(skillDetail.network_graph);
      
      console.log('\n💼 TOP JOBS:');
      console.log(skillDetail.top_jobs?.slice(0, 3));
      
      console.log('========================\n');
    }
  }, [skillDetail]);

  // Transform metrics for MetricsGrid
  const metricsGridData = useMemo(() => {
    if (!skillDetail?.metrics) return [];
    
    return skillDetail.metrics.map((metric: any) => {
      let value = metric.value;
      if (metric.format === 'fmtK' && typeof metric.value === 'number') {
        value = fmtK(metric.value);
      } else if (metric.format === 'fmtPercent' && typeof metric.value === 'number') {
        value = `${Math.round(metric.value)}%`;
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
    { name: 'Jobs Requiring', value: 0 },
    { name: 'Jobs Not Requiring', value: 100 }
  ];

  // Prepare network graph data
  const networkData = useMemo(() => {
    if (!skillDetail) {
      return {
        nodes: [{ 
          id: id || 'skill', 
          name: 'Skill', 
          group: '1',
          value: 20
        }],
        links: []
      };
    }
    
    // Use network_graph if available from API
    if (skillDetail.network_graph) {
      return skillDetail.network_graph;
    }
    
    // Fallback to old format
    return {
      nodes: [
        { 
          id: skillDetail.basic_info.skill_id, 
          name: skillDetail.basic_info.skill_name, 
          group: '1',
          value: 30
        },
        ...skillDetail.co_occurring_skills.slice(0, 10).map((s, i) => ({
          id: s.id,
          name: s.name.length > 20 ? s.name.substring(0, 20) + '...' : s.name,
          group: '2',
          value: 25 - (i * 1.5)
        }))
      ],
      links: skillDetail.co_occurring_skills.slice(0, 10).map(s => ({
        source: skillDetail.basic_info.skill_id,
        target: s.id,
        value: s.co_occurrence_rate || 50
      }))
    };
  }, [skillDetail, id]);

  // Get top co-occurring skills for "What to Learn Next"
  const nextSkills = useMemo(() => {
    if (!skillDetail?.co_occurring_skills) {
      return [];
    }
    
    const sorted = [...skillDetail.co_occurring_skills]
      .sort((a, b) => (b.co_occurrence_rate || 0) - (a.co_occurrence_rate || 0))
      .slice(0, 4);
    
    return sorted;
  }, [skillDetail]);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan"></div>
          <div className="text-muted-foreground">Loading skill details...</div>
          <div className="text-xs text-muted-foreground">Skill ID: {id} (Year: {year})</div>
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
            <div className="flex-1">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="font-display text-3xl font-bold tracking-tight">
                  {skillDetail.basic_info.skill_name}
                </h1>
                {/* Year badge */}
                <Badge variant="outline" className="bg-cyan/10 text-cyan border-cyan/20">
                  <Calendar className="h-3 w-3 mr-1" />
                  {skillDetail.year || year} Data
                </Badge>
              </div>
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
              <div className="relative w-full max-w-md mx-auto">
                <DonutChart
                  data={usageData}
                  height={300}
                  topListCount={2}
                  context="skill"
                  showSubtitle={false}
                  showHoverText={false}
                  showCenterTotal={false}
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
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
                title="Co-Occurring Skills Network"
                subtitle="Top 10 skills most frequently paired with this one"
              />
            </CardHeader>
            <CardContent className="flex justify-center">
              {networkData.nodes.length > 1 ? (
                <SkillNetworkGraph
                  nodes={networkData.nodes}
                  links={networkData.links}
                  centerNode={skillDetail.basic_info.skill_id}
                  width={380}
                  height={380}
                />
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No co-occurring skills data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* What to Learn Next - CONDITIONAL DISPLAY FOR TECH VS OTHER SKILLS */}
        {nextSkills.length > 0 ? (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="What Skills to Learn Next?"
                subtitle="Top 4 skills most commonly paired with this one"
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
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan/20 to-purple/20">
                        {skill.type === 'tech' ? (
                          <Code className="h-5 w-5 text-cyan" />
                        ) : (
                          <Briefcase className="h-5 w-5 text-purple" />
                        )}
                      </div>
                      <Badge
                        variant="secondary"
                        className={`text-xs ${
                          skill.type === 'tech' ? 'bg-cyan/10 text-cyan border-cyan/20' : 
                          skill.type === 'soft' ? 'bg-green/10 text-green border-green/20' : 
                          'bg-purple/10 text-purple border-purple/20'
                        }`}
                      >
                        {skill.type || 'general'}
                      </Badge>
                    </div>
                    <h4 className="mt-3 font-medium group-hover:text-cyan transition-colors line-clamp-1">
                      {skill.name}
                    </h4>
                    
                    {/* Co-occurrence rate with progress bar */}
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Co-occurrence</span>
                        <span className="font-medium text-cyan">
                          {skill.co_occurrence_rate ? skill.co_occurrence_rate.toFixed(1) : '0'}%
                        </span>
                      </div>
                      <div className="w-full bg-secondary/50 rounded-full h-1.5">
                        <div 
                          className="bg-cyan rounded-full h-1.5 transition-all group-hover:bg-cyan/80" 
                          style={{ width: `${Math.min(100, skill.co_occurrence_rate || 0)}%` }}
                        />
                      </div>
                    </div>

                    {/* EXACT JOB COUNT */}
                    {skill.usage_count ? (
                      <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                        <Users className="h-3 w-3" />
                        <span>{skill.usage_count.toLocaleString()} jobs</span>
                      </div>
                    ) : skill.frequency ? (
                      <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                        <Users className="h-3 w-3" />
                        <span>{skill.frequency.toLocaleString()} jobs</span>
                      </div>
                    ) : null}

                    {/* CONDITIONAL DISPLAY - TECH SKILLS SHOW BADGES, OTHERS SHOW IMPORTANCE */}
                    {skill.type === 'tech' ? (
                      // For tech skills, show hot/in demand badges
                      <div className="mt-2 flex flex-wrap gap-1">
                        {skill.hot_technology ? (
                          <Badge variant="outline" className="text-xs bg-coral/10 text-coral border-coral/20">
                            🔥 Hot Technology
                          </Badge>
                        ) : null}
                        {skill.in_demand ? (
                          <Badge variant="outline" className="text-xs bg-green/10 text-green border-green/20">
                            📈 In Demand
                          </Badge>
                        ) : null}
                        {/* If neither flag is true, show a placeholder to maintain height consistency */}
                        {!skill.hot_technology && !skill.in_demand && (
                          <div className="h-5"></div>
                        )}
                      </div>
                    ) : skill.type === 'tool' ? (
                      // For tools, show minimal info or nothing
                      <div className="mt-2 h-5"></div>
                    ) : (
                      // For all other skills (ability, knowledge, work_activity, etc.), show importance and level
                      <div className="mt-2 space-y-1">
                        {skill.avg_importance && skill.avg_importance > 0 && (
                          <div className="flex items-center gap-1 text-xs">
                            <TrendingUp className="h-3 w-3 text-purple" />
                            <span className="text-muted-foreground">Importance:</span>
                            <span className="text-purple font-medium">{Math.round(skill.avg_importance)}%</span>
                          </div>
                        )}
                        {skill.avg_level && skill.avg_level > 0 && (
                          <div className="flex items-center gap-1 text-xs">
                            <Briefcase className="h-3 w-3 text-coral" />
                            <span className="text-muted-foreground">Proficiency:</span>
                            <span className="text-coral font-medium">{Math.round(skill.avg_level)}%</span>
                          </div>
                        )}
                        {/* If no importance/level data, show placeholder */}
                        {(!skill.avg_importance || skill.avg_importance <= 0) && 
                         (!skill.avg_level || skill.avg_level <= 0) && (
                          <div className="h-5"></div>
                        )}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="What Skills to Learn Next?"
                subtitle="No co-occurring skills data available"
              />
            </CardHeader>
            <CardContent className="text-center text-muted-foreground py-4">
              No related skills found for this skill.
            </CardContent>
          </Card>
        )}

        {/* Top Jobs Using This Skill */}
        {skillDetail.top_jobs && skillDetail.top_jobs.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title={`Top Jobs Using This Skill (${skillDetail.year || year})`}
                subtitle="Roles where this skill is most important"
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
                    <div className="flex-1 min-w-0">
                      <p className="font-medium group-hover:text-cyan transition-colors truncate">
                        {job.title}
                      </p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>Importance: {Math.round(job.importance || 0)}%</span>
                        {job.level && (
                          <>
                            <span>•</span>
                            <span>Level: {Math.round(job.level)}%</span>
                          </>
                        )}
                      </div>
                      {/* Show salary if available for the selected year */}
                      {job.median_salary ? (
                        <div className="text-sm mt-1">
                          <span className="text-cyan font-medium">
                            ${(job.median_salary / 1000).toFixed(0)}K
                          </span>
                          <span className="text-xs text-muted-foreground ml-1">
                            ({skillDetail.year || year})
                          </span>
                        </div>
                      ) : (
                        <div className="text-sm text-muted-foreground mt-1">
                          Salary data unavailable for {skillDetail.year || year}
                        </div>
                      )}
                      {/* Show tech flags for jobs if they exist */}
                      {(job.hot_technology || job.in_demand) && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {job.hot_technology && (
                            <Badge variant="outline" className="text-xs bg-coral/10 text-coral border-coral/20">
                              🔥 Hot Tech
                            </Badge>
                          )}
                          {job.in_demand && (
                            <Badge variant="outline" className="text-xs bg-green/10 text-green border-green/20">
                              📈 In Demand
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
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
                  <span className="font-bold">Year:</span> {skillDetail.year || year}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Co-occurring Skills:</span> {skillDetail.co_occurring_skills.length}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Network Graph Nodes:</span> {networkData.nodes.length}
                </p>
                <p className="text-xs">
                  <span className="font-bold">Network Graph Links:</span> {networkData.links.length}
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
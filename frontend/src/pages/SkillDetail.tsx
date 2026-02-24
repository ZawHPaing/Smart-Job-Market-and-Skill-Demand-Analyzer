import { useEffect, useState, useMemo } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { ChevronLeft, Code, Briefcase, TrendingUp, Users, Calendar, Filter, ArrowRight, Sparkles } from 'lucide-react';
import { DashboardLayout, useYear } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { DonutChart, SkillNetworkGraph } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SkillsAPI } from '@/lib/skills';
import type { SkillDetailResponse, CoOccurringSkill } from '@/lib/skills';

// Helper functions
const fmtK = (n: number) => `${Math.round(n / 1000)}K`;
const fmtNumber = (n: number) => n.toLocaleString();

// Classification display names and colors - REMOVED 'general'
const classificationConfig: Record<string, { name: string; color: string; badgeColor: string }> = {
  'tech': { 
    name: 'Technology Skills', 
    color: 'from-cyan to-blue', 
    badgeColor: 'bg-cyan/10 text-cyan border-cyan/20' 
  },
  'ability': { 
    name: 'Abilities', 
    color: 'from-purple to-pink', 
    badgeColor: 'bg-purple/10 text-purple border-purple/20' 
  },
  'knowledge': { 
    name: 'Knowledge Areas', 
    color: 'from-amber to-orange', 
    badgeColor: 'bg-amber/10 text-amber border-amber/20' 
  },
  'work_activity': { 
    name: 'Work Activities', 
    color: 'from-coral to-red', 
    badgeColor: 'bg-coral/10 text-coral border-coral/20' 
  },
  'skill': { 
    name: 'Skills', 
    color: 'from-green to-emerald', 
    badgeColor: 'bg-green/10 text-green border-green/20' 
  },
  'tool': { 
    name: 'Tools', 
    color: 'from-gray to-slate', 
    badgeColor: 'bg-gray-500/20 text-gray-300 border-gray-500/30' 
  }
};

// List of tech skills that should NEVER appear in other categories
const FORCE_TECH_SKILLS = new Set([
  'c',
  'c++',
  'c#',
  'java',
  'python',
  'javascript',
  'typescript',
  'rust',
  'go',
  'swift',
  'kotlin',
  'php',
  'ruby',
  'html',
  'css',
  'sql',
  'mongodb',
  'postgresql',
  'mysql',
  'react',
  'angular',
  'vue',
  'node.js',
  'express',
  'django',
  'flask',
  'spring',
  'asp.net',
  'aws',
  'azure',
  'gcp',
  'docker',
  'kubernetes',
  'terraform',
  'git',
  'github',
  'gitlab',
  'jenkins',
  'jira',
  'confluence'
]);

// Helper function to get badge color based on skill type
const getSkillTypeBadgeColor = (type: string, isSameType: boolean = false): string => {
  if (isSameType) return 'bg-cyan/20 text-cyan border-cyan/30 font-semibold';
  if (type === 'tool') return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  return classificationConfig[type]?.badgeColor || 'bg-purple/10 text-purple border-purple/20';
};

// Helper function to get progress bar color based on skill type and value
const getProgressColor = (skill: CoOccurringSkill): string => {
  if (skill.type === 'tech') {
    if (skill.hot_technology && skill.in_demand) return 'bg-purple';
    if (skill.hot_technology) return 'bg-cyan';
    if (skill.in_demand) return 'bg-green';
    return 'bg-amber';
  }
  
  if (skill.type === 'tool') return 'bg-gray-500';
  
  switch(skill.type) {
    case 'ability': return 'bg-purple';
    case 'knowledge': return 'bg-amber';
    case 'work_activity': return 'bg-coral';
    case 'skill': return 'bg-green';
    default: return 'bg-cyan';
  }
};

// Helper function to get value color based on skill type
const getValueColor = (skill: CoOccurringSkill): string => {
  if (skill.type === 'tech') {
    if (skill.hot_technology && skill.in_demand) return 'text-purple';
    if (skill.hot_technology) return 'text-cyan';
    if (skill.in_demand) return 'text-green';
    return 'text-amber';
  }
  
  if (skill.type === 'tool') return 'text-gray-400';
  
  switch(skill.type) {
    case 'ability': return 'text-purple';
    case 'knowledge': return 'text-amber';
    case 'work_activity': return 'text-coral';
    case 'skill': return 'text-green';
    default: return 'text-cyan';
  }
};

// Helper function to get correlation badge color and text - ONLY SHOW LIFT VALUE
const getCorrelationBadge = (skill: CoOccurringSkill) => {
  const isSignificant = skill.is_significant || false;
  const lift = skill.lift || 1.0;
  
  if (!isSignificant) {
    return null;
  }
  
  if (skill.type === 'tool') {
    return {
      text: `${lift.toFixed(2)}x`,
      color: 'bg-gray-500/20 text-gray-300 border-gray-500/40',
    };
  }
  
  // Use color based on correlation type but just show lift value
  const correlationType = skill.correlation_type || 'neutral';
  switch(correlationType) {
    case 'strong_positive':
      return {
        text: `${lift.toFixed(2)}x`,
        color: 'bg-green/10 text-green border-green/20',
      };
    case 'moderate_positive':
      return {
        text: `${lift.toFixed(2)}x`,
        color: 'bg-cyan/10 text-cyan border-cyan/20',
      };
    case 'neutral':
      return {
        text: `${lift.toFixed(2)}x`,
        color: 'bg-amber/10 text-amber border-amber/20',
      };
    case 'moderate_negative':
      return {
        text: `${lift.toFixed(2)}x`,
        color: 'bg-coral/10 text-coral border-coral/20',
      };
    case 'strong_negative':
      return {
        text: `${lift.toFixed(2)}x`,
        color: 'bg-red/10 text-red border-red/20',
      };
    default:
      return {
        text: `${lift.toFixed(2)}x`,
        color: 'bg-purple/10 text-purple border-purple/20',
      };
  }
};

// Helper function to calculate a composite score for sorting
const getCompositeScore = (skill: CoOccurringSkill): number => {
  if (skill.type === 'tech') {
    let score = skill.co_occurrence_rate || 0;
    if (skill.hot_technology) score += 100;
    if (skill.in_demand) score += 50;
    return score;
  } else {
    const importanceScore = (skill.avg_importance || 0) * 2;
    const levelScore = (skill.avg_level || 0);
    return (skill.co_occurrence_rate || 0) + importanceScore + levelScore;
  }
};

// Helper function to clean and deduplicate skills
const cleanAndDeduplicateSkills = (skills: CoOccurringSkill[]): CoOccurringSkill[] => {
  let cleaned = skills.filter(skill => skill.type !== 'general');
  
  cleaned = cleaned.map(skill => {
    const skillName = skill.name.toLowerCase();
    if (FORCE_TECH_SKILLS.has(skillName)) {
      return { ...skill, type: 'tech' };
    }
    return skill;
  });
  
  const seen = new Map<string, CoOccurringSkill>();
  
  cleaned.forEach(skill => {
    const key = skill.name.toLowerCase();
    const existing = seen.get(key);
    
    if (!existing) {
      seen.set(key, skill);
    } else {
      const existingScore = existing.co_occurrence_rate || 0;
      const newScore = skill.co_occurrence_rate || 0;
      
      if (newScore > existingScore) {
        seen.set(key, skill);
      } else if (skill.type === 'tech' && existing.type !== 'tech') {
        seen.set(key, skill);
      }
    }
  });
  
  return Array.from(seen.values());
};

const SkillDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { year } = useYear();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skillDetail, setSkillDetail] = useState<SkillDetailResponse | null>(null);
  const [networkFilter, setNetworkFilter] = useState<string>('same');
  const [nextSkillsFilter, setNextSkillsFilter] = useState<string>('all');
  const [nextSkillsSort, setNextSkillsSort] = useState<'composite' | 'correlation'>('composite');

  const previousPage = location.state?.from || '/jobs';

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
        
        if (data.co_occurring_skills) {
          const originalCount = data.co_occurring_skills.length;
          const originalByType: Record<string, number> = {};
          data.co_occurring_skills.forEach(s => {
            originalByType[s.type] = (originalByType[s.type] || 0) + 1;
          });
          console.log('📊 Original skills by type:', originalByType);
          
          data.co_occurring_skills = cleanAndDeduplicateSkills(data.co_occurring_skills);
          
          const cleanedByType: Record<string, number> = {};
          data.co_occurring_skills.forEach(s => {
            cleanedByType[s.type] = (cleanedByType[s.type] || 0) + 1;
          });
          console.log(`📊 Cleaned skills: ${originalCount} -> ${data.co_occurring_skills.length}`);
          console.log('📊 Cleaned skills by type:', cleanedByType);
        }
        
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

  const usageData = skillDetail?.usage_data || [
    { name: 'Jobs Requiring', value: 0 },
    { name: 'Jobs Not Requiring', value: 100 }
  ];

  const availableTypes = useMemo(() => {
    if (!skillDetail?.co_occurring_skills) return [];
    
    const types = new Set<string>();
    skillDetail.co_occurring_skills.forEach(skill => {
      if (skill.type !== 'general') {
        types.add(skill.type);
      }
    });
    
    return Array.from(types).sort();
  }, [skillDetail]);

  const filteredNetworkSkills = useMemo(() => {
    if (!skillDetail?.co_occurring_skills) return [];
    
    const currentType = skillDetail.basic_info.skill_type;
    
    let filtered = [];
    if (networkFilter === 'same') {
      filtered = skillDetail.co_occurring_skills.filter(
        skill => skill.type === currentType
      );
    } else {
      filtered = skillDetail.co_occurring_skills.filter(
        skill => skill.type === networkFilter
      );
    }
    
    const top10 = [...filtered]
      .sort((a, b) => (b.co_occurrence_rate || 0) - (a.co_occurrence_rate || 0))
      .slice(0, 10);
    
    return top10;
  }, [skillDetail, networkFilter]);

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
    
    const mainSkillId = skillDetail.basic_info.skill_id;
    const mainSkillName = skillDetail.basic_info.skill_name;
    const skillsForNetwork = filteredNetworkSkills;
    
    const nodes = [
      { 
        id: mainSkillId, 
        name: mainSkillName, 
        group: '1',
        value: 30,
        usage_count: undefined,
        co_occurrence_rate: undefined,
        avg_importance: undefined,
        avg_level: undefined,
        lift: undefined,
        is_significant: undefined
      }
    ];
    
    skillsForNetwork.forEach((skill, i) => {
      nodes.push({
        id: skill.id,
        name: skill.name.length > 20 ? skill.name.substring(0, 20) + '...' : skill.name,
        group: '2',
        value: 25 - (i * 1.5),
        usage_count: skill.usage_count,
        co_occurrence_rate: skill.co_occurrence_rate,
        avg_importance: skill.avg_importance,
        avg_level: skill.avg_level,
        lift: skill.lift,
        is_significant: skill.is_significant
      });
    });
    
    const links = skillsForNetwork.map(skill => ({
      source: mainSkillId,
      target: skill.id,
      value: (skill.co_occurrence_rate || 50) / 10,
      co_occurrence_rate: skill.co_occurrence_rate,
      lift: skill.lift,
      is_significant: skill.is_significant
    }));
    
    return { nodes, links };
  }, [skillDetail, filteredNetworkSkills, id]);

  const filteredNextSkills = useMemo(() => {
    if (!skillDetail?.co_occurring_skills) return [];
    
    let filtered = [];
    if (nextSkillsFilter === 'all') {
      filtered = skillDetail.co_occurring_skills;
    } else {
      filtered = skillDetail.co_occurring_skills.filter(
        skill => skill.type === nextSkillsFilter
      );
    }
    
    const sorted = [...filtered].sort((a, b) => {
      switch(nextSkillsSort) {
        case 'correlation':
          const aSig = a.is_significant ? 100 : 0;
          const bSig = b.is_significant ? 100 : 0;
          const aLift = a.lift || 0;
          const bLift = b.lift || 0;
          
          if (Math.abs(bLift - aLift) > 0.01) {
            return bLift - aLift;
          }
          return bSig - aSig;
          
        case 'composite':
        default:
          return getCompositeScore(b) - getCompositeScore(a);
      }
    });
    
    return sorted;
  }, [skillDetail, nextSkillsFilter, nextSkillsSort]);

  const sortedJobs = useMemo(() => {
    if (!skillDetail?.top_jobs) return [];
    
    const sorted = [...skillDetail.top_jobs].sort((a, b) => {
      const empA = a.employment ? Number(a.employment) : 0;
      const empB = b.employment ? Number(b.employment) : 0;
      return empB - empA;
    });
    
    return sorted;
  }, [skillDetail?.top_jobs]);

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
            to={previousPage}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Job Details
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
            to={previousPage}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Job Details
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
          <MetricsGrid metrics={metricsGridData} showTrend={false} />
        ) : (
          <Card className="glass-card">
            <CardContent className="p-4 text-center text-muted-foreground">
              No metrics data available
            </CardContent>
          </Card>
        )}

        {/* Skill Usage & Network */}
        <div className="grid gap-6 lg:grid-cols-2">
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

          <Card className="glass-card">
            <CardHeader>
              <div className="flex items-center justify-between">
                <SectionHeader
                  title="Co-Occurring Skills Network"
                  subtitle={`Top 10 ${networkFilter === 'same' 
                    ? classificationConfig[skillDetail.basic_info.skill_type]?.name.toLowerCase() 
                    : classificationConfig[networkFilter]?.name.toLowerCase() || 'skills'} most frequently paired`}
                />
                {availableTypes.length > 0 && (
                  <Select value={networkFilter} onValueChange={setNetworkFilter}>
                    <SelectTrigger className="w-[180px] bg-secondary/50">
                      <Filter className="h-3 w-3 mr-2" />
                      <SelectValue placeholder="Filter by type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="same">
                        Same Type ({classificationConfig[skillDetail.basic_info.skill_type]?.name})
                      </SelectItem>
                      {availableTypes.map(type => (
                        <SelectItem key={type} value={type}>
                          {classificationConfig[type]?.name || type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex justify-center">
              {networkData.nodes.length > 1 ? (
                <>
                  <SkillNetworkGraph
                    nodes={networkData.nodes}
                    links={networkData.links}
                    centerNode={skillDetail.basic_info.skill_id}
                    width={380}
                    height={380}
                  />
                  {filteredNetworkSkills.length < 10 && (
                    <div className="text-xs text-amber mt-2">
                      Only showing {filteredNetworkSkills.length} available skills of this type
                    </div>
                  )}
                </>
              ) : (
                <div className="text-muted-foreground text-center py-8">
                  No co-occurring skills of this type found
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Correlation Summary Card */}
        {skillDetail.correlation_analysis && skillDetail.correlation_analysis.summary.total_correlations > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Correlation Analysis"
                subtitle={`${skillDetail.correlation_analysis.summary.significant_count} statistically significant relationships found`}
              />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-secondary/30">
                  <p className="text-xs text-muted-foreground">Total Correlations</p>
                  <p className="text-2xl font-bold text-cyan">{skillDetail.correlation_analysis.summary.total_correlations}</p>
                </div>
                <div className="p-4 rounded-lg bg-secondary/30">
                  <p className="text-xs text-muted-foreground">Average Lift</p>
                  <p className="text-2xl font-bold text-purple">{skillDetail.correlation_analysis.summary.avg_lift.toFixed(2)}x</p>
                </div>
                <div className="p-4 rounded-lg bg-secondary/30">
                  <p className="text-xs text-muted-foreground">Max Lift</p>
                  <p className="text-2xl font-bold text-green">{skillDetail.correlation_analysis.summary.max_lift.toFixed(2)}x</p>
                </div>
                <div className="p-4 rounded-lg bg-secondary/30">
                  <p className="text-xs text-muted-foreground">Significant</p>
                  <p className="text-2xl font-bold text-coral">{skillDetail.correlation_analysis.summary.significant_count}</p>
                </div>
              </div>
              
              <div className="mt-4 flex flex-wrap gap-3">
                {Object.entries(skillDetail.correlation_analysis.summary.correlation_types).map(([type, count]) => {
                  if (count === 0) return null;
                  const colors = {
                    strong_positive: 'bg-green/10 text-green border-green/20',
                    moderate_positive: 'bg-cyan/10 text-cyan border-cyan/20',
                    neutral: 'bg-amber/10 text-amber border-amber/20',
                    moderate_negative: 'bg-coral/10 text-coral border-coral/20',
                    strong_negative: 'bg-red/10 text-red border-red/20'
                  };
                  const labels = {
                    strong_positive: 'Strong Positive',
                    moderate_positive: 'Moderate Positive',
                    neutral: 'Neutral',
                    moderate_negative: 'Moderate Negative',
                    strong_negative: 'Strong Negative'
                  };
                  return (
                    <Badge key={type} variant="outline" className={colors[type as keyof typeof colors]}>
                      {labels[type as keyof typeof labels]}: {count}
                    </Badge>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* What to Learn Next - NO TOOLTIPS, NO LEGEND */}
        {filteredNextSkills.length > 0 ? (
          <Card className="glass-card">
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <SectionHeader
                    title="What Skills to Learn Next?"
                    subtitle={`${filteredNextSkills.length} related skills${
                      nextSkillsFilter !== 'all' 
                        ? ` (${classificationConfig[nextSkillsFilter]?.name.toLowerCase()})` 
                        : ''
                    }`}
                  />
                </div>
                <div className="flex gap-2">
                  <Select value={nextSkillsSort} onValueChange={(v) => setNextSkillsSort(v as 'composite' | 'correlation')}>
                    <SelectTrigger className="w-[160px] bg-secondary/50">
                      <Sparkles className="h-3 w-3 mr-2" />
                      <SelectValue placeholder="Sort by" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="composite">Recommended</SelectItem>
                      <SelectItem value="correlation">Strongest Correlation</SelectItem>
                    </SelectContent>
                  </Select>
                  
                  {availableTypes.length > 0 && (
                    <Select value={nextSkillsFilter} onValueChange={setNextSkillsFilter}>
                      <SelectTrigger className="w-[180px] bg-secondary/50">
                        <Filter className="h-3 w-3 mr-2" />
                        <SelectValue placeholder="Filter by type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Types</SelectItem>
                        {availableTypes.map(type => (
                          <SelectItem key={type} value={type}>
                            {classificationConfig[type]?.name || type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <div 
                  className="flex overflow-x-auto gap-4 pb-4 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                  style={{
                    scrollbarWidth: 'thin',
                    msOverflowStyle: 'auto',
                    WebkitOverflowScrolling: 'touch',
                  }}
                >
                  {filteredNextSkills.map((skill) => {
                    const isSameType = skill.type === skillDetail.basic_info.skill_type;
                    const progressColor = getProgressColor(skill);
                    const valueColor = getValueColor(skill);
                    const correlationBadge = getCorrelationBadge(skill);
                    
                    return (
                      <Link
                        key={`${skill.id}-${skill.type}-${skill.name}`}
                        to={`/skills/${skill.id}`}
                        state={{ from: location.pathname }}
                        className="flex-none w-[280px] group p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 border border-transparent hover:border-cyan/30 transition-all"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan/20 to-purple/20">
                            {skill.type === 'tech' ? (
                              <Code className="h-5 w-5 text-cyan" />
                            ) : (
                              <Briefcase className="h-5 w-5 text-purple" />
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <Badge
                              variant="secondary"
                              className={`text-xs ${getSkillTypeBadgeColor(skill.type, isSameType)}`}
                            >
                              {isSameType ? `★ ${skill.type}` : skill.type}
                            </Badge>
                            {correlationBadge && (
                              <Badge
                                variant="outline"
                                className={`text-xs ${correlationBadge.color} group-hover:opacity-100 transition-opacity`}
                              >
                                {correlationBadge.text}
                              </Badge>
                            )}
                          </div>
                        </div>
                        
                        <h4 className="mt-3 font-medium group-hover:text-cyan transition-colors line-clamp-2 min-h-[3rem]">
                          {skill.name}
                        </h4>
                        
                        <div className="mt-2 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">Co-occurrence</span>
                            <span className={`font-medium ${valueColor}`}>
                              {skill.co_occurrence_rate ? skill.co_occurrence_rate.toFixed(1) : '0'}%
                            </span>
                          </div>
                          <div className="w-full bg-secondary/50 rounded-full h-1.5">
                            <div 
                              className={`rounded-full h-1.5 transition-all ${progressColor} group-hover:opacity-80`}
                              style={{ width: `${Math.min(100, skill.co_occurrence_rate || 0)}%` }}
                            />
                          </div>
                        </div>

                        {skill.type === 'tech' ? (
                          <div className="mt-3 flex flex-wrap gap-1">
                            {skill.hot_technology && (
                              <Badge variant="outline" className="text-xs bg-coral/10 text-coral border-coral/20">
                                🔥 Hot
                              </Badge>
                            )}
                            {skill.in_demand && (
                              <Badge variant="outline" className="text-xs bg-green/10 text-green border-green/20">
                                📈 Demand
                              </Badge>
                            )}
                          </div>
                        ) : skill.type === 'tool' ? (
                          <div className="mt-3 space-y-2">
                            {skill.usage_count ? (
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Jobs Using</span>
                                <span className="text-gray-400 font-medium">
                                  {skill.usage_count.toLocaleString()}
                                </span>
                              </div>
                            ) : (
                              <div className="text-xs text-muted-foreground">&nbsp;</div>
                            )}
                          </div>
                        ) : (
                          <div className="mt-3 space-y-2">
                            {skill.avg_importance && skill.avg_importance > 0 && (
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Importance</span>
                                <span className="text-purple font-medium">
                                  {Math.round(skill.avg_importance)}%
                                </span>
                              </div>
                            )}
                            {skill.avg_level && skill.avg_level > 0 && (
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Proficiency</span>
                                <span className="text-coral font-medium">
                                  {Math.round(skill.avg_level)}%
                                </span>
                              </div>
                            )}
                          </div>
                        )}

                        {(skill.usage_count || skill.frequency) && (
                          <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground border-t border-border/50 pt-2">
                            <Users className="h-3 w-3" />
                            <span>{(skill.usage_count || skill.frequency || 0).toLocaleString()} jobs</span>
                          </div>
                        )}
                      </Link>
                    );
                  })}
                </div>
                
                {filteredNextSkills.length > 3 && (
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none">
                    <div className="bg-gradient-to-l from-background to-transparent w-12 h-full flex items-center justify-end pr-2">
                      <ArrowRight className="h-5 w-5 text-muted-foreground animate-pulse" />
                    </div>
                  </div>
                )}
              </div>
              
              <div className="mt-3 text-xs text-muted-foreground text-right border-t border-border/50 pt-2">
                Showing {filteredNextSkills.length} unique skills • Sorted by {nextSkillsSort === 'composite' ? 'recommendation' : 'correlation strength'}
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="What Skills to Learn Next?"
                subtitle="No related skills found"
              />
            </CardHeader>
            <CardContent className="text-center text-muted-foreground py-4">
              No related skills found for this skill.
            </CardContent>
          </Card>
        )}

        {/* Top Jobs Using This Skill */}
        {sortedJobs.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title={`Top Jobs Using This Skill (${skillDetail.year || year})`}
                subtitle={`${sortedJobs.length} jobs sorted by total employment (highest first)`}
              />
            </CardHeader>
            <CardContent>
              <div 
                className="max-h-[600px] overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent hover:scrollbar-thumb-secondary/80"
                style={{
                  scrollbarWidth: 'thin',
                  msOverflowStyle: 'auto',
                }}
              >
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {sortedJobs.map((job) => (
                    <Link
                      key={job.soc_code}
                      to={`/jobs/${job.soc_code.replace('.00', '')}`}
                      state={{ from: location.pathname }}
                      className="block p-4 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors group"
                    >
                      <div className="space-y-2">
                        <p className="font-medium group-hover:text-cyan transition-colors line-clamp-2 min-h-[3rem]">
                          {job.title}
                        </p>
                        
                        {job.employment ? (
                          <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-cyan" />
                            <div>
                              <span className="text-lg font-semibold text-cyan">
                                {Number(job.employment).toLocaleString()}
                              </span>
                              <span className="text-xs text-muted-foreground ml-1">employed</span>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Users className="h-4 w-4" />
                            <span className="text-sm">Employment data unavailable</span>
                          </div>
                        )}
                        
                        {job.median_salary ? (
                          <div className="flex items-center gap-2">
                            <Briefcase className="h-4 w-4 text-purple" />
                            <div>
                              <span className="text-base font-medium text-purple">
                                ${(Number(job.median_salary) / 1000).toFixed(0)}K
                              </span>
                              <span className="text-xs text-muted-foreground ml-1">median salary</span>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Briefcase className="h-4 w-4" />
                            <span className="text-sm">Salary data unavailable</span>
                          </div>
                        )}
                        
                        <div className="text-xs text-muted-foreground mt-1">
                          Data from {skillDetail.year || year}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
              
              <div className="mt-3 text-xs text-muted-foreground text-right border-t border-border/50 pt-2">
                Showing all {sortedJobs.length} jobs that require this skill
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default SkillDetail;
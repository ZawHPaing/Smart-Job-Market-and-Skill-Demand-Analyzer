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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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
    badgeColor: 'bg-secondary/30 text-muted-foreground border-secondary/40' 
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
  
  switch(skill.type) {
    case 'ability': return 'bg-purple';
    case 'knowledge': return 'bg-amber';
    case 'work_activity': return 'bg-coral';
    case 'skill': return 'bg-green';
    case 'tool': return 'bg-gray';
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
  
  switch(skill.type) {
    case 'ability': return 'text-purple';
    case 'knowledge': return 'text-amber';
    case 'work_activity': return 'text-coral';
    case 'skill': return 'text-green';
    case 'tool': return 'text-gray';
    default: return 'text-cyan';
  }
};

// Helper function to get correlation badge color and text
const getCorrelationBadge = (skill: CoOccurringSkill) => {
  const correlationType = skill.correlation_type || 'neutral';
  const isSignificant = skill.is_significant || false;
  const lift = skill.lift || 1.0;
  
  if (!isSignificant) {
    return {
      text: 'Not significant',
      color: 'bg-gray/10 text-gray border-gray/20',
      icon: '⚪'
    };
  }
  
  switch(correlationType) {
    case 'strong_positive':
      return {
        text: `Strong (${lift.toFixed(2)}x)`,
        color: 'bg-green/10 text-green border-green/20',
        icon: '🚀'
      };
    case 'moderate_positive':
      return {
        text: `Moderate (${lift.toFixed(2)}x)`,
        color: 'bg-cyan/10 text-cyan border-cyan/20',
        icon: '📈'
      };
    case 'neutral':
      return {
        text: `Neutral (${lift.toFixed(2)}x)`,
        color: 'bg-amber/10 text-amber border-amber/20',
        icon: '⚖️'
      };
    case 'moderate_negative':
      return {
        text: `Moderate (${lift.toFixed(2)}x)`,
        color: 'bg-coral/10 text-coral border-coral/20',
        icon: '📉'
      };
    case 'strong_negative':
      return {
        text: `Strong (${lift.toFixed(2)}x)`,
        color: 'bg-red/10 text-red border-red/20',
        icon: '⚠️'
      };
    default:
      return {
        text: `Lift: ${lift.toFixed(2)}x`,
        color: 'bg-purple/10 text-purple border-purple/20',
        icon: '🔗'
      };
  }
};

// Helper function to get correlation description
const getCorrelationDescription = (skill: CoOccurringSkill): string => {
  const correlationType = skill.correlation_type || 'neutral';
  const isSignificant = skill.is_significant || false;
  const chiSquare = skill.chi_square || 0;
  const lift = skill.lift || 1.0;
  
  if (!isSignificant) {
    return 'Not statistically significant (p ≥ 0.05)';
  }
  
  let description = '';
  switch(correlationType) {
    case 'strong_positive':
      description = 'Strongly correlated - appears together very frequently';
      break;
    case 'moderate_positive':
      description = 'Moderately correlated - often appears together';
      break;
    case 'neutral':
      description = 'No strong correlation - appears independently';
      break;
    case 'moderate_negative':
      description = 'Moderately inverse correlation - rarely appears together';
      break;
    case 'strong_negative':
      description = 'Strongly inverse correlation - almost never appears together';
      break;
    default:
      description = 'Correlation analysis available';
  }
  
  return `${description} (Lift: ${lift.toFixed(2)}x, χ²: ${chiSquare.toFixed(2)})`;
};

// Helper function to calculate a composite score for sorting
const getCompositeScore = (skill: CoOccurringSkill): number => {
  if (skill.type === 'tech') {
    // For tech skills: prioritize hot_technology and in_demand
    let score = skill.co_occurrence_rate || 0;
    if (skill.hot_technology) score += 100;
    if (skill.in_demand) score += 50;
    return score;
  } else {
    // For other skills: use importance and level
    const importanceScore = (skill.avg_importance || 0) * 2;
    const levelScore = (skill.avg_level || 0);
    return (skill.co_occurrence_rate || 0) + importanceScore + levelScore;
  }
};

// Helper function to clean and deduplicate skills
const cleanAndDeduplicateSkills = (skills: CoOccurringSkill[]): CoOccurringSkill[] => {
  // First, remove any 'general' category skills
  let cleaned = skills.filter(skill => skill.type !== 'general');
  
  // Force correct categorization for known tech skills
  cleaned = cleaned.map(skill => {
    const skillName = skill.name.toLowerCase();
    if (FORCE_TECH_SKILLS.has(skillName)) {
      return { ...skill, type: 'tech' };
    }
    return skill;
  });
  
  // Deduplicate by name, keeping the best version
  const seen = new Map<string, CoOccurringSkill>();
  
  cleaned.forEach(skill => {
    const key = skill.name.toLowerCase();
    const existing = seen.get(key);
    
    // If we haven't seen this skill, add it
    if (!existing) {
      seen.set(key, skill);
    } else {
      // If we have seen it, keep the one with higher co-occurrence rate
      // and prefer tech category for tech skills
      const existingScore = existing.co_occurrence_rate || 0;
      const newScore = skill.co_occurrence_rate || 0;
      
      // If the new one has a higher score, replace
      if (newScore > existingScore) {
        seen.set(key, skill);
      } 
      // If scores are equal or new is lower, but new is tech and existing isn't, replace
      else if (skill.type === 'tech' && existing.type !== 'tech') {
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

  // Get the previous page from location state, default to jobs page
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
        
        // Clean and deduplicate co-occurring skills
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

  // Get unique skill types from co-occurring skills (after cleaning, excluding 'general')
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

  // Filter co-occurring skills for network graph based on selected filter
  const filteredNetworkSkills = useMemo(() => {
    if (!skillDetail?.co_occurring_skills) return [];
    
    const currentType = skillDetail.basic_info.skill_type;
    
    let filtered = [];
    if (networkFilter === 'same') {
      // Only skills of the same type as current skill
      filtered = skillDetail.co_occurring_skills.filter(
        skill => skill.type === currentType
      );
    } else {
      // Skills of the selected type
      filtered = skillDetail.co_occurring_skills.filter(
        skill => skill.type === networkFilter
      );
    }
    
    // Sort by co-occurrence rate and take top 10 for network graph
    const top10 = [...filtered]
      .sort((a, b) => (b.co_occurrence_rate || 0) - (a.co_occurrence_rate || 0))
      .slice(0, 10);
    
    return top10;
  }, [skillDetail, networkFilter]);

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
    
    const mainSkillId = skillDetail.basic_info.skill_id;
    const mainSkillName = skillDetail.basic_info.skill_name;
    
    // Use filtered skills for network graph
    const skillsForNetwork = filteredNetworkSkills;
    
    // Create nodes array
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
    
    // Add co-occurring skill nodes
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
    
    // Create links
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

  // Filter skills for "What to Learn Next" based on selected filter and sort
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
    
    // Sort based on selected sort option
    const sorted = [...filtered].sort((a, b) => {
      switch(nextSkillsSort) {
        case 'correlation':
          // Sort by lift (higher is better), with significance as tiebreaker
          const aSig = a.is_significant ? 100 : 0;
          const bSig = b.is_significant ? 100 : 0;
          const aLift = a.lift || 0;
          const bLift = b.lift || 0;
          
          // Primary: lift value, Secondary: significance
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

  // Sort jobs by employment (highest first)
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

          {/* Co-Occurring Skills Network - WITH FILTER */}
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
              
              {/* Correlation type breakdown */}
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

        {/* What to Learn Next - SIDESCROLL WITH FILTER AND SORT */}
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
                  {/* Sort dropdown - now with just 2 options */}
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
                  
                  {/* Filter dropdown */}
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
              {/* Legend for correlation badges */}
              <div className="flex flex-wrap gap-3 mb-4 text-xs">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-green"></div>
                        <span>🚀 Strong Positive</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Lift {'>'} 1.5 - Always appear together</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-cyan"></div>
                        <span>📈 Moderate Positive</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Lift 1.1-1.5 - Often appear together</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-amber"></div>
                        <span>⚖️ Neutral</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Lift 0.9-1.1 - Appear independently</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-coral"></div>
                        <span>📉 Moderate Negative</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Lift 0.5-0.9 - Rarely appear together</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-red"></div>
                        <span>⚠️ Strong Negative</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Lift {'<'} 0.5 - Almost never appear together</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              {/* Horizontal scrollable container */}
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
                    const correlationDesc = getCorrelationDescription(skill);
                    
                    return (
                      <TooltipProvider key={`${skill.id}-${skill.type}-${skill.name}`}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Link
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
                                  {/* Correlation badge */}
                                  {skill.lift && skill.lift !== 1.0 && (
                                    <Badge
                                      variant="outline"
                                      className={`text-xs ${correlationBadge.color} group-hover:opacity-100 transition-opacity`}
                                    >
                                      {correlationBadge.icon} {correlationBadge.text}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                              
                              <h4 className="mt-3 font-medium group-hover:text-cyan transition-colors line-clamp-2 min-h-[3rem]">
                                {skill.name}
                              </h4>
                              
                              {/* Co-occurrence rate */}
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

                              {/* Type-specific metrics */}
                              {skill.type === 'tech' ? (
                                // Tech skills show badges
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
                                // Tools show minimal info
                                <div className="mt-3 text-xs text-muted-foreground">
                                  {skill.usage_count ? (
                                    <span>{skill.usage_count.toLocaleString()} jobs</span>
                                  ) : (
                                    <span>&nbsp;</span>
                                  )}
                                </div>
                              ) : (
                                // Other skills show importance and level
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

                              {/* Job count */}
                              {(skill.usage_count || skill.frequency) && (
                                <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground border-t border-border/50 pt-2">
                                  <Users className="h-3 w-3" />
                                  <span>{(skill.usage_count || skill.frequency || 0).toLocaleString()} jobs</span>
                                </div>
                              )}
                            </Link>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="max-w-xs">
                            <p className="text-sm">{correlationDesc}</p>
                            {skill.chi_square && skill.chi_square > 0 && (
                              <p className="text-xs text-muted-foreground mt-1">
                                χ² = {skill.chi_square.toFixed(2)} {skill.is_significant ? '(p < 0.05)' : '(p ≥ 0.05)'}
                              </p>
                            )}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    );
                  })}
                </div>
                
                {/* Scroll hint */}
                {filteredNextSkills.length > 3 && (
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none">
                    <div className="bg-gradient-to-l from-background to-transparent w-12 h-full flex items-center justify-end pr-2">
                      <ArrowRight className="h-5 w-5 text-muted-foreground animate-pulse" />
                    </div>
                  </div>
                )}
              </div>
              
              {/* Count indicator - updated to show only 2 sort options */}
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
              {/* Scrollable container for all jobs */}
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
                        {/* Job Title */}
                        <p className="font-medium group-hover:text-cyan transition-colors line-clamp-2 min-h-[3rem]">
                          {job.title}
                        </p>
                        
                        {/* Employment */}
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
                        
                        {/* Salary */}
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
                        
                        {/* Year indicator */}
                        <div className="text-xs text-muted-foreground mt-1">
                          Data from {skillDetail.year || year}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
              
              {/* Job count indicator */}
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
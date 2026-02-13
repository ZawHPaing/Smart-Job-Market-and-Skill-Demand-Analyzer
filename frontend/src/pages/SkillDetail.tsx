import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, Code, TrendingUp, BarChart3, DollarSign, Lightbulb } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { DonutChart, SkillNetworkGraph, HorizontalBarChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { skills, skillNetworkData, jobTitles } from '@/data/mockData';

const SkillDetail = () => {
  const { id } = useParams<{ id: string }>();

  const skill = skills.find((s) => s.id === id) || skills[0];

  const metrics = [
    {
      title: 'Skill Type',
      value: skill.type === 'tech' ? 'Tech Skill' : skill.type === 'soft' ? 'Soft Skill' : 'General',
      color: 'cyan' as const,
    },
    {
      title: 'Importance Level',
      value: skill.importance.toFixed(1),
      suffix: '/10',
      color: 'purple' as const,
    },
    {
      title: 'Required Proficiency',
      value: skill.proficiency.toFixed(1),
      suffix: '/10',
      color: 'coral' as const,
    },
    {
      title: 'Demand Trend',
      value: `+${skill.demandTrend}%`,
      trend: { value: skill.demandTrend, direction: 'up' as const },
      color: 'green' as const,
    },
    {
      title: 'Salary Association',
      value: skill.salaryAssociation,
      prefix: '$',
      trend: { value: 5.2, direction: 'up' as const },
      color: 'amber' as const,
    },
  ];

  // Skill usage data for donut chart
  const usageData = [
    { name: 'Jobs Requiring', value: skill.jobsRequiring, color: 'hsl(186 100% 50%)' },
    { name: 'Jobs Not Requiring', value: 100 - skill.jobsRequiring, color: 'hsl(0 0% 25%)' },
  ];

  // Top jobs using this skill
  const relatedJobs = jobTitles.slice(0, 6).map((job) => ({
    name: job.title,
    value: Math.round(Math.random() * 30 + 70), // Usage percentage
    secondaryValue: job.salary,
  }));

  // Skills to learn next
  const nextSkills = skills
    .filter((s) => s.id !== skill.id && skill.coOccurringSkills.includes(s.id))
    .slice(0, 4);

  // Fallback if no co-occurring skills found
  const recommendedSkills = nextSkills.length > 0 ? nextSkills : skills.filter((s) => s.id !== skill.id).slice(0, 4);

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
                {skill.name}
              </h1>
              <p className="mt-1 text-muted-foreground">
                Complete analysis of skill demand, usage, and career impact
              </p>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <MetricsGrid metrics={metrics} />

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
                  <span className="text-4xl font-bold text-cyan">{skill.jobsRequiring}%</span>
                  <span className="text-sm text-muted-foreground">of jobs</span>
                </div>
              </div>
              <p className="mt-4 text-center text-muted-foreground">
                {skill.jobsRequiring}% of analyzed job postings require {skill.name}
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
              <SkillNetworkGraph
                nodes={skillNetworkData.nodes}
                links={skillNetworkData.links}
                centerNode={skill.id}
                width={350}
                height={350}
              />
            </CardContent>
          </Card>
        </div>

        {/* What to Learn Next */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="What Skills to Learn Next?"
              subtitle="Recommended skills to complement your expertise"
            />
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {recommendedSkills.map((s) => (
                <Link
                  key={s.id}
                  to={`/skills/${s.id}`}
                  className="group p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 border border-transparent hover:border-cyan/30 transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple/20">
                      <Lightbulb className="h-5 w-5 text-purple" />
                    </div>
                    <Badge
                      variant="secondary"
                      className={`text-xs ${
                        s.type === 'tech' ? 'bg-cyan/10 text-cyan' : 'bg-purple/10 text-purple'
                      }`}
                    >
                      {s.type}
                    </Badge>
                  </div>
                  <h4 className="mt-3 font-medium group-hover:text-cyan transition-colors">
                    {s.name}
                  </h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    +{s.demandTrend}% demand growth
                  </p>
                  <p className="text-sm text-green-500">
                    ${(s.salaryAssociation / 1000).toFixed(0)}K avg salary
                  </p>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Jobs Using This Skill */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Top Jobs Using This Skill"
              subtitle="Roles where this skill is highly valued"
            />
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {relatedJobs.map((job) => (
                <div
                  key={job.name}
                  className="flex items-center justify-between p-3 rounded-lg bg-secondary/30"
                >
                  <div>
                    <p className="font-medium">{job.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {job.value}% importance
                    </p>
                  </div>
                  <span className="text-cyan font-medium">
                    ${(job.secondaryValue / 1000).toFixed(0)}K
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default SkillDetail;

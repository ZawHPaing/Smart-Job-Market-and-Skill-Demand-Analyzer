import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { DonutChart, HorizontalBarChart, MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  overviewMetrics,
  industryDistribution,
  topJobTitles,
  employmentTimeSeries,
} from '@/data/mockData';

const Home = () => {
  const metrics = [
    {
      title: 'Total Job Postings',
      value: overviewMetrics.totalJobs,
      trend: { value: 8.5, direction: 'up' as const },
      color: 'cyan' as const,
    },
    {
      title: 'Unique Industries',
      value: overviewMetrics.uniqueIndustries,
      trend: { value: 2.3, direction: 'up' as const },
      color: 'purple' as const,
    },
    {
      title: 'Unique Job Titles',
      value: overviewMetrics.uniqueJobs,
      trend: { value: 5.1, direction: 'up' as const },
      color: 'coral' as const,
    },
    {
      title: 'Overall Industry Trend',
      value: '+8.5%',
      trend: { value: 1.2, direction: 'up' as const },
      color: 'green' as const,
    },
    {
      title: 'Median Annual Salary',
      value: overviewMetrics.medianSalary,
      prefix: '$',
      trend: { value: 4.8, direction: 'up' as const },
      color: 'amber' as const,
    },
  ];

  const chartData = topJobTitles.map((job) => ({
    name: job.name,
    value: job.postings,
    secondaryValue: job.salary,
  }));

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Page Title */}
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">
            Job Market <span className="gradient-text">Overview</span>
          </h1>
          <p className="mt-1 text-muted-foreground">
            Real-time analytics across industries, jobs, and skills
          </p>
        </div>

        {/* Key Metrics */}
        <MetricsGrid metrics={metrics} />

        {/* Charts Section */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Job Distribution by Industry */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Job Distributions by Industry"
                subtitle="2024 job postings breakdown"
                action={{ label: 'See More', href: '/industries' }}
              />
            </CardHeader>
            <CardContent>
              <DonutChart data={industryDistribution} />
            </CardContent>
          </Card>

          {/* Top Job Titles */}
          <Card className="glass-card">
            <CardHeader>
              <SectionHeader
                title="Top Job Titles & Salary"
                subtitle="Postings count with median salary overlay"
                action={{ label: 'See More', href: '/jobs' }}
              />
            </CardHeader>
            <CardContent>
              <HorizontalBarChart
                data={chartData.slice(0, 8)}
                showSecondary
                primaryLabel="Job Postings"
                secondaryLabel="Median Salary"
              />
            </CardContent>
          </Card>
        </div>

        {/* Employment Trends */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Employment per Industry Over Time"
              subtitle="Historical employment trends by major industry"
              action={{ label: 'View Trends', href: '/trends' }}
            />
          </CardHeader>
          <CardContent>
            <MultiLineChart
              data={employmentTimeSeries}
              xAxisKey="year"
              lines={[
                { key: 'tech', name: 'Technology', color: 'hsl(186 100% 50%)' },
                { key: 'healthcare', name: 'Healthcare', color: 'hsl(0 100% 71%)' },
                { key: 'finance', name: 'Finance', color: 'hsl(258 90% 76%)' },
              ]}
              height={350}
            />
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Home;

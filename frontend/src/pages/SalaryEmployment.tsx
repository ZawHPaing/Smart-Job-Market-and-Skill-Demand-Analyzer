import { useState } from 'react';
import { Search } from 'lucide-react';
import { DashboardLayout } from '@/components/layout';
import { MetricsGrid, SectionHeader } from '@/components/dashboard';
import { HorizontalBarChart, MultiLineChart } from '@/components/charts';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { salaryEmploymentData, salaryTimeSeries, industries } from '@/data/mockData';

const SalaryEmployment = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const metrics = [
    {
      title: 'Total Employment',
      value: 24300000,
      trend: { value: 3.2, direction: 'up' as const },
      color: 'cyan' as const,
    },
    {
      title: 'Median Salary',
      value: 78500,
      prefix: '$',
      trend: { value: 4.8, direction: 'up' as const },
      color: 'purple' as const,
    },
    {
      title: 'Employment Trend',
      value: '+3.2%',
      trend: { value: 0.8, direction: 'up' as const },
      color: 'green' as const,
    },
    {
      title: 'Salary Trend',
      value: '+4.8%',
      trend: { value: 1.2, direction: 'up' as const },
      color: 'coral' as const,
    },
    {
      title: 'Highest Paying Industry',
      value: 'Technology',
      color: 'amber' as const,
    },
  ];

  const industryData = salaryEmploymentData.map((d) => ({
    name: d.industry,
    value: d.employment,
    secondaryValue: d.salary,
  }));

  const jobSalaryData = [
    { name: 'Physician', value: 2800000, secondaryValue: 220000 },
    { name: 'Investment Banker', value: 1500000, secondaryValue: 185000 },
    { name: 'ML Engineer', value: 2200000, secondaryValue: 165000 },
    { name: 'Product Manager', value: 3500000, secondaryValue: 155000 },
    { name: 'Data Scientist', value: 4200000, secondaryValue: 145000 },
    { name: 'DevOps Engineer', value: 2800000, secondaryValue: 140000 },
    { name: 'Software Engineer', value: 8500000, secondaryValue: 135000 },
    { name: 'UX Designer', value: 3200000, secondaryValue: 115000 },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header with Search */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight">
              Salary & <span className="gradient-text">Employment</span>
            </h1>
            <p className="mt-1 text-muted-foreground">
              Compare compensation and employment across industries and roles
            </p>
          </div>
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search by industry or job..."
              className="pl-10 bg-secondary/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Key Metrics */}
        <MetricsGrid metrics={metrics} />

        {/* Tabs for Industry vs Job View */}
        <Tabs defaultValue="industries" className="space-y-6">
          <TabsList className="bg-secondary/50">
            <TabsTrigger value="industries">By Industry</TabsTrigger>
            <TabsTrigger value="jobs">By Job Title</TabsTrigger>
          </TabsList>

          <TabsContent value="industries" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Salary & Employment for Industries */}
              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Salary & Employment by Industry"
                    subtitle="Employment count with median salary overlay"
                  />
                </CardHeader>
                <CardContent>
                  <HorizontalBarChart
                    data={industryData}
                    showSecondary
                    primaryLabel="Employment"
                    secondaryLabel="Median Salary"
                    formatValue={(v) => `${(v / 1000000).toFixed(1)}M`}
                  />
                </CardContent>
              </Card>

              {/* Salary Over Time */}
              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Salary Distribution Over Time"
                    subtitle="Historical salary trends by industry"
                  />
                </CardHeader>
                <CardContent>
                  <MultiLineChart
                    data={salaryTimeSeries}
                    xAxisKey="year"
                    lines={[
                      { key: 'tech', name: 'Technology', color: 'hsl(186 100% 50%)' },
                      { key: 'healthcare', name: 'Healthcare', color: 'hsl(0 100% 71%)' },
                      { key: 'finance', name: 'Finance', color: 'hsl(258 90% 76%)' },
                    ]}
                    height={350}
                    formatYAxis={(v) => `$${v / 1000}K`}
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="jobs" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Salary & Employment for Jobs */}
              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Salary & Employment by Job"
                    subtitle="Top paying jobs with employment numbers"
                  />
                </CardHeader>
                <CardContent>
                  <HorizontalBarChart
                    data={jobSalaryData}
                    showSecondary
                    primaryLabel="Employment"
                    secondaryLabel="Median Salary"
                    formatValue={(v) => `${(v / 1000000).toFixed(1)}M`}
                  />
                </CardContent>
              </Card>

              {/* Employment Over Time for Jobs */}
              <Card className="glass-card">
                <CardHeader>
                  <SectionHeader
                    title="Employment per Job Over Time"
                    subtitle="Historical employment trends for top roles"
                  />
                </CardHeader>
                <CardContent>
                  <MultiLineChart
                    data={[
                      { year: 2019, sweng: 6500000, ds: 2500000, rn: 7500000 },
                      { year: 2020, sweng: 7000000, ds: 3000000, rn: 8000000 },
                      { year: 2021, sweng: 7500000, ds: 3500000, rn: 8500000 },
                      { year: 2022, sweng: 8000000, ds: 3800000, rn: 9000000 },
                      { year: 2023, sweng: 8200000, ds: 4000000, rn: 9200000 },
                      { year: 2024, sweng: 8500000, ds: 4200000, rn: 9500000 },
                    ]}
                    xAxisKey="year"
                    lines={[
                      { key: 'sweng', name: 'Software Engineer', color: 'hsl(186 100% 50%)' },
                      { key: 'ds', name: 'Data Scientist', color: 'hsl(0 100% 71%)' },
                      { key: 'rn', name: 'Registered Nurse', color: 'hsl(258 90% 76%)' },
                    ]}
                    height={350}
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Industry/Job Comparison Table */}
        <Card className="glass-card">
          <CardHeader>
            <SectionHeader
              title="Detailed Comparison"
              subtitle="Full breakdown of salary and employment data"
            />
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Industry
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                      Employment
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                      Median Salary
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                      Trend
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {industries.map((ind) => (
                    <tr
                      key={ind.id}
                      className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                    >
                      <td className="py-3 px-4 font-medium">{ind.name}</td>
                      <td className="py-3 px-4 text-right text-muted-foreground">
                        {(ind.employment / 1000000).toFixed(1)}M
                      </td>
                      <td className="py-3 px-4 text-right text-cyan">
                        ${ind.medianSalary.toLocaleString()}
                      </td>
                      <td
                        className={`py-3 px-4 text-right font-medium ${
                          ind.trend >= 0 ? 'text-green-500' : 'text-coral'
                        }`}
                      >
                        {ind.trend >= 0 ? '+' : ''}
                        {ind.trend}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        
      </div>
    </DashboardLayout>
  );
};

export default SalaryEmployment;

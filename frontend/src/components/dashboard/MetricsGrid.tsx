import { MetricCard } from './MetricCard';

interface MetricsGridProps {
  metrics: {
    title: string;
    value: number | string;
    prefix?: string;
    suffix?: string;
    trend?: { value: number; direction: 'up' | 'down' | 'neutral' };
    color?: 'cyan' | 'coral' | 'purple' | 'green' | 'amber';
  }[];
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {metrics.map((metric, index) => (
        <MetricCard
          key={metric.title}
          {...metric}
          delay={index * 100}
        />
      ))}
    </div>
  );
}

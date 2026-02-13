import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

const tickerItems = [
  { name: 'Tech Industry', value: '+18.5%', trend: 'up' },
  { name: 'Software Engineer', value: '85,000 openings', trend: 'up' },
  { name: 'Healthcare', value: '+12.3%', trend: 'up' },
  { name: 'Data Scientist', value: '$145K median', trend: 'up' },
  { name: 'Manufacturing', value: '-2.5%', trend: 'down' },
  { name: 'AI/ML Jobs', value: '+35.2%', trend: 'up' },
  { name: 'Remote Work', value: '+42%', trend: 'up' },
  { name: 'Finance Sector', value: '+8.2%', trend: 'up' },
  { name: 'Median Salary', value: '$78,500', trend: 'neutral' },
  { name: 'Total Openings', value: '1.26M', trend: 'up' },
];

export function MarketTicker() {
  return (
    <div className="w-full border-b border-border/40 bg-secondary/30 py-2 overflow-hidden">
      <div className="ticker">
        <div className="ticker-content flex items-center gap-8">
          {/* Duplicate items for seamless loop */}
          {[...tickerItems, ...tickerItems].map((item, index) => (
            <div key={index} className="flex items-center gap-2 whitespace-nowrap">
              <span className="text-sm text-muted-foreground">{item.name}</span>
              <span
                className={cn(
                  'text-sm font-medium flex items-center gap-1',
                  item.trend === 'up' && 'text-green-500',
                  item.trend === 'down' && 'text-coral',
                  item.trend === 'neutral' && 'text-foreground'
                )}
              >
                {item.trend === 'up' && <TrendingUp className="h-3 w-3" />}
                {item.trend === 'down' && <TrendingDown className="h-3 w-3" />}
                {item.trend === 'neutral' && <Minus className="h-3 w-3" />}
                {item.value}
              </span>
              <span className="text-muted-foreground/30">•</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

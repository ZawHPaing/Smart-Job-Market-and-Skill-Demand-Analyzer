import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { HomeAPI, MarketTickerItem } from '@/lib/home';
import { useYear } from './YearContext';

const fallbackItems: MarketTickerItem[] = [
  { name: 'Median Salary', value: '$0', trend: 'neutral' },
  { name: 'Salary YoY', value: '0.0%', trend: 'neutral' },
  { name: 'Top Growing Industry', value: '0.0%', trend: 'neutral' },
  { name: 'Top Growing Occupation', value: '0.0%', trend: 'neutral' },
  { name: 'Top Tech Skill', value: 'N/A', trend: 'neutral' },
  { name: 'Highest Employment Occupation', value: '0', trend: 'neutral' },
  { name: 'Hot Tech Count', value: '0', trend: 'neutral' },
];

const formatCompact = (n: number) => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toString();
};

const formatValue = (value: string) => {
  if (!value) return value;
  if (value.includes('%') || value.includes('(')) return value;
  if (value.startsWith('$')) {
    const num = Number(value.replace(/[^0-9.-]/g, ''));
    if (!Number.isFinite(num)) return value;
    return `$${formatCompact(num)}`;
  }
  if (/^[+-]?\d+(\.\d+)?$/.test(value)) {
    const num = Number(value);
    if (!Number.isFinite(num)) return value;
    return formatCompact(num);
  }
  return value;
};

export function MarketTicker() {
  const { year } = useYear();
  const [items, setItems] = useState<MarketTickerItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await HomeAPI.marketTicker(year);
        if (cancelled) return;
        setItems(res.items || []);
      } catch {
        if (cancelled) return;
        setItems([]);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [year]);

  const tickerItems = items.length ? items : fallbackItems;

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
                {formatValue(item.value)}
              </span>
              <span className="text-muted-foreground/30">•</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

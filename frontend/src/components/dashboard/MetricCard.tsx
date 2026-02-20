import { useEffect, useState, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MetricCard as MetricCardType } from '@/types';

interface MetricCardProps extends Omit<MetricCardType, 'id'> {
  animateValue?: boolean;
  delay?: number;
  showTrend?: boolean;
}

function toNumber(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return Number.isFinite(val) ? val : null;

  // handle strings like "$78,500", "+8.5%", "131.8M", etc.
  const s = String(val).trim();
  if (!s) return null;

  const cleaned = s.replace(/[^0-9.-]/g, '');
  const n = parseFloat(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function MetricCard({
  title,
  value,
  prefix = '',
  suffix = '',
  trend,
  color = 'cyan',
  animateValue = true,
  delay = 0,
  showTrend = true,
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const numericValue = toNumber(value);
  const isNumeric = numericValue !== null;

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (cardRef.current) observer.observe(cardRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isVisible || !animateValue || !isNumeric) return;

    const timeout = setTimeout(() => {
      const duration = 1500;
      const steps = 60;
      const stepValue = (numericValue as number) / steps;
      let current = 0;

      const interval = setInterval(() => {
        current += stepValue;
        if (current >= (numericValue as number)) {
          setDisplayValue(numericValue as number);
          clearInterval(interval);
        } else {
          setDisplayValue(current);
        }
      }, duration / steps);

      return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(timeout);
  }, [isVisible, animateValue, isNumeric, numericValue, delay]);

  const formatValue = (val: number) => {
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M';
    if (val >= 1_000) return (val / 1_000).toFixed(val >= 10_000 ? 0 : 1) + 'K';
    return val.toLocaleString('en-US', { maximumFractionDigits: 0 });
  };

  const glowClass = {
    cyan: 'hover-glow-cyan',
    coral: 'hover-glow-coral',
    purple: 'hover-glow-purple',
    green: 'hover-glow-cyan',
    amber: 'hover-glow-coral',
  }[color];

  const accentClass = {
    cyan: 'text-cyan',
    coral: 'text-coral',
    purple: 'text-purple',
    green: 'text-green-500',
    amber: 'text-amber',
  }[color];

  const safeText =
    value === null || value === undefined || String(value).trim() === '' ? '—' : String(value);

  return (
    <div
      ref={cardRef}
      className={cn('metric-card', glowClass, isVisible && 'animate-fade-in')}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>

          <div className="flex items-baseline gap-1">
            {prefix && <span className="text-xl text-muted-foreground">{prefix}</span>}

            <span className={cn('counter-value', accentClass)}>
              {isNumeric
                ? formatValue(animateValue ? displayValue : (numericValue as number))
                : safeText}
            </span>

            {suffix && <span className="text-xl text-muted-foreground">{suffix}</span>}
          </div>
        </div>

        {showTrend && trend && (
          <div
            className={cn(
              'flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium',
              trend.direction === 'up' && 'bg-green-500/10 text-green-500',
              trend.direction === 'down' && 'bg-coral/10 text-coral',
              trend.direction === 'neutral' && 'bg-muted text-muted-foreground'
            )}
          >
            {trend.direction === 'up' && <TrendingUp className="h-3 w-3" />}
            {trend.direction === 'down' && <TrendingDown className="h-3 w-3" />}
            {trend.direction === 'neutral' && <Minus className="h-3 w-3" />}
            {Math.abs(trend.value)}%
          </div>
        )}
      </div>

      <div
        className={cn(
          'absolute bottom-0 left-0 h-1 w-0 rounded-full transition-all duration-500',
          isVisible && 'w-full',
          color === 'cyan' && 'bg-gradient-to-r from-cyan to-cyan/50',
          color === 'coral' && 'bg-gradient-to-r from-coral to-coral/50',
          color === 'purple' && 'bg-gradient-to-r from-purple to-purple/50',
          color === 'green' && 'bg-gradient-to-r from-green-500 to-green-500/50',
          color === 'amber' && 'bg-gradient-to-r from-amber to-amber/50'
        )}
      />
    </div>
  );
}

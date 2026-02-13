import { ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: {
    label: string;
    href: string;
  };
  children?: ReactNode;
  className?: string;
}

export function SectionHeader({
  title,
  subtitle,
  action,
  children,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cn('flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between', className)}>
      <div className="space-y-1">
        <h2 className="font-display text-xl font-semibold tracking-tight">{title}</h2>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-3">
        {children}
        {action && (
          <Link
            to={action.href}
            className="group flex items-center gap-1 text-sm font-medium text-cyan hover:text-cyan/80 transition-colors"
          >
            {action.label}
            <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        )}
      </div>
    </div>
  );
}

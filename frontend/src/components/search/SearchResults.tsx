// frontend/src/components/search/SearchResults.tsx
import { SearchResult } from '@/hooks/useSearch';
import { cn } from '@/lib/utils';

interface SearchResultsProps {
  results: SearchResult[];
  loading: boolean;
  onSelect: (result: SearchResult) => void;
  className?: string;
}

export function SearchResults({ results, loading, onSelect, className }: SearchResultsProps) {
  if (loading) {
    return (
      <div className={cn(
        "absolute top-full left-0 right-0 mt-2 p-4 rounded-lg border border-border/50 bg-popover shadow-lg z-50",
        className
      )}>
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-cyan"></div>
          <span className="ml-2 text-sm text-muted-foreground">Searching...</span>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className={cn(
        "absolute top-full left-0 right-0 mt-2 p-8 rounded-lg border border-border/50 bg-popover shadow-lg z-50 text-center",
        className
      )}>
        <p className="text-sm text-muted-foreground">No results found</p>
      </div>
    );
  }

  return (
    <div className={cn(
      "absolute top-full left-0 right-0 mt-2 rounded-lg border border-border/50 bg-popover shadow-lg overflow-hidden z-50",
      className
    )}>
      <div className="max-h-96 overflow-y-auto divide-y divide-border/50">
        {results.map((result) => (
          <button
            key={`${result.type}-${result.id}`}
            onClick={() => onSelect(result)}
            className="w-full px-4 py-3 flex items-start gap-3 hover:bg-accent/50 transition-colors text-left group"
          >
            <span className="text-lg mt-0.5">{result.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium group-hover:text-cyan transition-colors">
                  {result.name}
                </span>
                <span className={cn(
                  "text-xs px-1.5 py-0.5 rounded-full",
                  result.type === 'job' && "bg-blue-500/10 text-blue-500",
                  result.type === 'industry' && "bg-purple-500/10 text-purple-500",
                  result.type === 'skill' && "bg-green-500/10 text-green-500",
                )}>
                  {result.type}
                </span>
              </div>
              {result.subtitle && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {result.subtitle}
                </p>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
// frontend/src/components/layout/TopNavigation.tsx
import { Link, useLocation } from 'react-router-dom';
import { Search, ChevronDown, Menu, X, Loader2 } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { useYear } from './YearContext';
import { useSearch } from '@/hooks/useSearch';
import { SearchResults } from '@/components/search/SearchResults';

const navItems = [
  { name: 'Home', path: '/' },
  { name: 'Industries', path: '/industries' },
  { name: 'Jobs', path: '/jobs' },
  { name: 'Salary & Employment', path: '/salary-employment' },
  { name: 'Trends', path: '/trends' },
];

export function TopNavigation() {
  const location = useLocation();
  const { year: selectedYear, setYear: setSelectedYear, years } = useYear();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  
  const {
    query,
    setQuery,
    results,
    loading,
    isOpen,
    setIsOpen,
    handleSelect,
    clearSearch
  } = useSearch();

  // Close search results when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [setIsOpen]);

  // Close mobile menu on navigation
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Handle search result selection
  const onSelectResult = (result: any) => {
    handleSelect(result);
    setIsOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan to-purple">
            <span className="font-display text-lg font-bold text-background">JM</span>
          </div>
          <span className="hidden font-display text-xl font-semibold tracking-tight md:block">
            Job Market Analytics
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden items-center gap-1 lg:flex">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'relative px-4 py-2 text-sm font-medium transition-colors hover:text-foreground',
                location.pathname === item.path
                  ? 'text-foreground'
                  : 'text-muted-foreground'
              )}
            >
              {item.name}
              {location.pathname === item.path && (
                <span className="absolute bottom-0 left-4 right-4 h-0.5 rounded-full bg-green-500" />
              )}
            </Link>
          ))}
        </nav>

        {/* Search & Year Selector */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div ref={searchRef} className="relative hidden w-80 md:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search jobs, industries, skills..."
              className="pl-10 pr-8 bg-secondary/50 border-border/50 focus:bg-secondary"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => {
                if (results.length > 0) {
                  setIsOpen(true);
                }
              }}
            />
            {query && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                ) : (
                  <button
                    onClick={clearSearch}
                    className="text-muted-foreground hover:text-foreground"
                    type="button"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}
            
            {/* Search Results Dropdown */}
            {isOpen && (
              <SearchResults
                results={results}
                loading={loading}
                onSelect={onSelectResult}
                className="w-full"
              />
            )}
          </div>

          {/* Year Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="gap-2 bg-secondary/50 border-border/50 hover:bg-secondary"
              >
                <span className="font-medium">{selectedYear}</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-24">
              {years.map((year) => (
                <DropdownMenuItem
                  key={year}
                  onClick={() => setSelectedYear(year)}
                  className={cn(
                    'cursor-pointer',
                    year === selectedYear && 'bg-accent text-accent-foreground'
                  )}
                >
                  {year}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="border-t border-border/40 bg-background lg:hidden">
          <nav className="container flex flex-col gap-1 px-4 py-3">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsMobileMenuOpen(false)}
                className={cn(
                  'px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                  location.pathname === item.path
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:bg-accent/50'
                )}
              >
                {item.name}
              </Link>
            ))}
            {/* Mobile Search */}
            <div className="relative mt-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search jobs, industries, skills..."
                className="pl-10 pr-8 bg-secondary/50"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => {
                  if (results.length > 0) {
                    setIsOpen(true);
                  }
                }}
              />
              {query && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  ) : (
                    <button
                      onClick={clearSearch}
                      className="text-muted-foreground hover:text-foreground"
                      type="button"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              )}
            </div>
            
            {/* Mobile Search Results */}
            {isOpen && (
              <div className="mt-2">
                <SearchResults
                  results={results}
                  loading={loading}
                  onSelect={onSelectResult}
                  className="static shadow-none border"
                />
              </div>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
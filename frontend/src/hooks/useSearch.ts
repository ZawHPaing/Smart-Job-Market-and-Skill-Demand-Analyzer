// frontend/src/hooks/useSearch.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { JobsAPI } from '@/lib/jobs';
import { SkillsAPI } from '@/lib/skills';
import { IndustriesAPI } from '@/lib/industries';
import { useDebounce } from '@/hooks/useDebounce';

export type SearchResult = {
  id: string;
  name: string;
  type: 'job' | 'industry' | 'skill';
  subtitle?: string;
  route: string;
  icon?: string;
};

export function useSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const navigate = useNavigate();
  const searchCache = useRef<Map<string, SearchResult[]>>(new Map());

  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setResults([]);
      return;
    }

    // Check cache first
    if (searchCache.current.has(searchQuery)) {
      setResults(searchCache.current.get(searchQuery) || []);
      return;
    }

    setLoading(true);
    
    try {
      // Search in parallel across all sources
      const [jobsResult, skillsResult, industriesResult] = await Promise.allSettled([
        JobsAPI.search(searchQuery, 2024, 5).catch(() => []),
        SkillsAPI.search(searchQuery, 5).catch(() => []),
        IndustriesAPI.list(2024).then(res => {
          const industries = res.industries || [];
          const queryLower = searchQuery.toLowerCase();
          return industries
            .filter(ind => 
              ind.naics_title.toLowerCase().includes(queryLower) || 
              ind.naics.includes(searchQuery)
            )
            .slice(0, 5);
        }).catch(() => [])
      ]);

      const allResults: SearchResult[] = [];

      // Process jobs
      if (jobsResult.status === 'fulfilled' && jobsResult.value) {
        const jobs = Array.isArray(jobsResult.value) ? jobsResult.value : [];
        const jobResults = jobs.map((job: any) => ({
          id: job.occ_code,
          name: job.occ_title,
          type: 'job' as const,
          subtitle: job.total_employment 
            ? `${job.total_employment.toLocaleString()} employed` 
            : undefined,
          route: `/jobs/${encodeURIComponent(job.occ_code)}`,
          icon: '💼'
        }));
        allResults.push(...jobResults);
      }

      // Process skills
      if (skillsResult.status === 'fulfilled' && skillsResult.value) {
        const skills = Array.isArray(skillsResult.value) ? skillsResult.value : [];
        const skillResults = skills.map((skill: any) => ({
          id: skill.id,
          name: skill.name,
          type: 'skill' as const,
          subtitle: skill.job_count ? `${skill.job_count} related jobs` : undefined,
          route: `/skills/${encodeURIComponent(skill.id)}`,
          icon: skill.type === 'tech' ? '⚙️' : '🧠'
        }));
        allResults.push(...skillResults);
      }

      // Process industries
      if (industriesResult.status === 'fulfilled' && industriesResult.value) {
        const industries = Array.isArray(industriesResult.value) ? industriesResult.value : [];
        const industryResults = industries.map((ind: any) => ({
          id: ind.naics,
          name: ind.naics_title,
          type: 'industry' as const,
          subtitle: `NAICS: ${ind.naics}`,
          route: `/industries/${encodeURIComponent(ind.naics)}`,
          icon: '🏭'
        }));
        allResults.push(...industryResults);
      }

      // Sort results by relevance
      allResults.sort((a, b) => {
        const aLower = a.name.toLowerCase();
        const bLower = b.name.toLowerCase();
        const queryLower = searchQuery.toLowerCase();
        
        // Exact matches first
        if (aLower === queryLower && bLower !== queryLower) return -1;
        if (bLower === queryLower && aLower !== queryLower) return 1;
        
        // Starts with query next
        if (aLower.startsWith(queryLower) && !bLower.startsWith(queryLower)) return -1;
        if (bLower.startsWith(queryLower) && !aLower.startsWith(queryLower)) return 1;
        
        // Then by length
        return a.name.length - b.name.length;
      });

      const limitedResults = allResults.slice(0, 8);
      
      // Cache results
      searchCache.current.set(searchQuery, limitedResults);
      setResults(limitedResults);
      setIsOpen(true);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debouncedQuery) {
      performSearch(debouncedQuery);
    } else {
      setResults([]);
      setIsOpen(false);
    }
  }, [debouncedQuery, performSearch]);

  const handleSelect = useCallback((result: SearchResult) => {
    navigate(result.route);
    setQuery('');
    setIsOpen(false);
  }, [navigate]);

  const clearSearch = useCallback(() => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
  }, []);

  return {
    query,
    setQuery,
    results,
    loading,
    isOpen,
    setIsOpen,
    handleSelect,
    clearSearch
  };
}
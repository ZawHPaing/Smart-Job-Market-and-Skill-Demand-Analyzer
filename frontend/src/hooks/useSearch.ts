// frontend/src/hooks/useSearch.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDebounce } from '@/hooks/useDebounce';

export type SearchResult = {
  id: string;
  name: string;
  type: 'job' | 'industry' | 'skill';
  subtitle?: string;
  route: string;
  icon?: string;
  metadata?: {
    employment?: number;
    salary?: number;
    job_count?: number;
    naics?: string;
  };
};

type UseSearchProps = {
  year: number;
};

export function useSearch({ year }: UseSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const navigate = useNavigate();
  const searchCache = useRef<Map<string, SearchResult[]>>(new Map());
  const abortControllerRef = useRef<AbortController | null>(null);

  const performSearch = useCallback(async (searchQuery: string) => {
    console.log(`🔍 Performing search for: "${searchQuery}" with year: ${year}`);
    
    if (!searchQuery.trim() || searchQuery.length < 2) {
      console.log('❌ Search query too short, clearing results');
      setResults([]);
      return;
    }

    // Create cache key that includes the year
    const cacheKey = `${searchQuery}_${year}`;
    
    // Check cache first
    if (searchCache.current.has(cacheKey)) {
      console.log(`✅ Using cached results for: "${searchQuery}" (${year})`);
      setResults(searchCache.current.get(cacheKey) || []);
      setIsOpen(true);
      return;
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      console.log('🛑 Aborting previous search request');
      abortControllerRef.current.abort();
    }
    
    // Create new abort controller
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    setLoading(true);
    
    try {
      // Construct URLs with the selected year
      const API_BASE_URL = 'http://localhost:8000/api';
      
      const jobsUrl = `${API_BASE_URL}/jobs/search?q=${encodeURIComponent(searchQuery)}&limit=5&year=${year}`;
      const skillsUrl = `${API_BASE_URL}/skills/search?q=${encodeURIComponent(searchQuery)}&limit=5`;
      const industriesUrl = `${API_BASE_URL}/industries/?year=${year}`;
      
      console.log('📡 Fetching from URLs:');
      console.log(`   Jobs: ${jobsUrl}`);
      console.log(`   Skills: ${skillsUrl}`);
      console.log(`   Industries: ${industriesUrl}`);

      const [jobsResult, skillsResult, industriesResult] = await Promise.allSettled([
        // Search jobs
        fetch(jobsUrl, {
          signal,
          headers: { 
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        }).then(async res => {
          console.log(`📥 Jobs response status: ${res.status} ${res.statusText}`);
          if (!res.ok) {
            const text = await res.text();
            console.log(`❌ Jobs error body:`, text.substring(0, 200));
            return [];
          }
          const data = await res.json();
          console.log(`✅ Jobs received:`, data);
          return data.jobs || data || [];
        }),
        
        // Search skills
        fetch(skillsUrl, {
          signal,
          headers: { 
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        }).then(async res => {
          console.log(`📥 Skills response status: ${res.status} ${res.statusText}`);
          if (!res.ok) {
            const text = await res.text();
            console.log(`❌ Skills error body:`, text.substring(0, 200));
            return [];
          }
          const data = await res.json();
          console.log(`✅ Skills received:`, data);
          return Array.isArray(data) ? data : [];
        }),
        
        // Get all industries
        fetch(industriesUrl, {
          signal,
          headers: { 
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        }).then(async res => {
          console.log(`📥 Industries response status: ${res.status} ${res.statusText}`);
          if (!res.ok) {
            const text = await res.text();
            console.log(`❌ Industries error body:`, text.substring(0, 200));
            return { industries: [] };
          }
          const data = await res.json();
          console.log(`✅ Industries received:`, data);
          return data;
        })
      ]);

      console.log('📊 Promise.allSettled results:', {
        jobs: jobsResult.status,
        skills: skillsResult.status,
        industries: industriesResult.status
      });

      const allResults: SearchResult[] = [];

      // Process jobs
      if (jobsResult.status === 'fulfilled' && Array.isArray(jobsResult.value)) {
        console.log(`📋 Processing ${jobsResult.value.length} jobs`);
        jobsResult.value.forEach((job: any) => {
          allResults.push({
            id: job.occ_code,
            name: job.occ_title,
            type: 'job',
            subtitle: job.total_employment ? `${job.total_employment.toLocaleString()} employed` : undefined,
            route: `/jobs/${encodeURIComponent(job.occ_code)}`,
            icon: '💼',
            metadata: { 
              employment: job.total_employment, 
              salary: job.a_median 
            }
          });
        });
      } else if (jobsResult.status === 'rejected') {
        console.error('❌ Jobs promise rejected:', jobsResult.reason);
      }

      // Process skills
      if (skillsResult.status === 'fulfilled' && Array.isArray(skillsResult.value)) {
        console.log(`📋 Processing ${skillsResult.value.length} skills`);
        skillsResult.value.forEach((skill: any) => {
          allResults.push({
            id: skill.id,
            name: skill.name,
            type: 'skill',
            subtitle: skill.job_count ? `${skill.job_count.toLocaleString()} related jobs` : undefined,
            route: `/skills/${encodeURIComponent(skill.id)}`,
            icon: skill.type === 'tech' ? '⚙️' : '🧠',
            metadata: { 
              job_count: skill.job_count 
            }
          });
        });
      } else if (skillsResult.status === 'rejected') {
        console.error('❌ Skills promise rejected:', skillsResult.reason);
      }

      // Process industries (filter client-side)
      if (industriesResult.status === 'fulfilled' && industriesResult.value?.industries) {
        const industries = industriesResult.value.industries;
        console.log(`📋 Processing ${industries.length} total industries`);
        
        const qLower = searchQuery.toLowerCase();
        const filteredIndustries = industries.filter((ind: any) => 
          ind.naics_title?.toLowerCase().includes(qLower) || 
          ind.naics?.includes(searchQuery)
        );
        
        console.log(`📋 Found ${filteredIndustries.length} matching industries`);
        
        filteredIndustries.slice(0, 5).forEach((ind: any) => {
          allResults.push({
            id: ind.naics,
            name: ind.naics_title,
            type: 'industry',
            subtitle: `NAICS: ${ind.naics}`,
            route: `/industries/${encodeURIComponent(ind.naics)}`,
            icon: '🏭',
            metadata: { 
              naics: ind.naics,
              employment: ind.total_employment 
            }
          });
        });
      } else if (industriesResult.status === 'rejected') {
        console.error('❌ Industries promise rejected:', industriesResult.reason);
      }

      console.log(`📊 Total results before sorting: ${allResults.length}`);

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
        
        // Then by length (shorter names are usually more relevant)
        return a.name.length - b.name.length;
      });

      const limitedResults = allResults.slice(0, 8);
      console.log(`✅ Final results: ${limitedResults.length} items`, limitedResults);
      
      // Cache results with year in cache key
      searchCache.current.set(cacheKey, limitedResults);
      setResults(limitedResults);
      setIsOpen(true);
    } catch (error: any) {
      console.error('💥 Search error caught:', error);
      
      // Don't show errors for aborted requests
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED' || error.message?.includes('abort')) {
        console.log('🛑 Request was aborted');
        return;
      }
      
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, [year]); // Add year to dependency array

  useEffect(() => {
    console.log(`🔍 Query changed: "${query}" (debounced: "${debouncedQuery}") with year: ${year}`);
    if (debouncedQuery) {
      performSearch(debouncedQuery);
    } else {
      setResults([]);
      setIsOpen(false);
    }
    
    // Cleanup function
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [debouncedQuery, performSearch, year]); // Add year to dependencies

  const handleSelect = useCallback((result: SearchResult) => {
    console.log(`👉 Selected:`, result);
    navigate(result.route);
    setQuery('');
    setIsOpen(false);
  }, [navigate]);

  const clearSearch = useCallback(() => {
    console.log('🧹 Clearing search');
    setQuery('');
    setResults([]);
    setIsOpen(false);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
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
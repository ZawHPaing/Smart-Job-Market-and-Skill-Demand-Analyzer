import { createContext, useContext, useMemo, useState, useEffect } from "react";

const YEARS = [2024, 2023, 2022, 2021, 2020, 2019];
const STORAGE_KEY = "selected_year";

type YearContextValue = {
  year: number;
  setYear: (year: number) => void;
  years: number[];
};

const YearContext = createContext<YearContextValue | undefined>(undefined);

export function YearProvider({ children }: { children: React.ReactNode }) {
  const [year, setYearState] = useState<number>(YEARS[0]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? Number(raw) : NaN;
      if (Number.isFinite(parsed) && YEARS.includes(parsed)) {
        setYearState(parsed);
      }
    } catch {
      // ignore storage errors
    }
  }, []);

  const setYear = (next: number) => {
    if (!YEARS.includes(next)) return;
    setYearState(next);
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      // ignore storage errors
    }
  };

  const value = useMemo(() => ({ year, setYear, years: YEARS }), [year]);

  return <YearContext.Provider value={value}>{children}</YearContext.Provider>;
}

export function useYear() {
  const ctx = useContext(YearContext);
  if (!ctx) {
    throw new Error("useYear must be used within YearProvider");
  }
  return ctx;
}

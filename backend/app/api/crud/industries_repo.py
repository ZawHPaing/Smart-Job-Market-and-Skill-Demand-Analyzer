# app/api/crud/industries_repo.py
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase


# -------------------------
# helpers
# -------------------------
def _to_float(v: Any) -> float:
    """
    Robust numeric parser for BLS fields that can contain:
      - "1,234"
      - "*", "#", "**"
      - None / NaN-like
    """
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip()
    if not s or s in ("*", "#", "**", "nan", "NaN", "None"):
        return 0.0

    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def _median(nums: List[float]) -> float:
    nums = [x for x in nums if x and x > 0]
    if not nums:
        return 0.0
    nums.sort()
    n = len(nums)
    mid = n // 2
    if n % 2 == 1:
        return float(nums[mid])
    return float((nums[mid - 1] + nums[mid]) / 2.0)


def _quantile(sorted_vals: List[float], q: float) -> float:
    """
    Linear interpolation quantile. Input must be sorted.
    """
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])

    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


# -------------------------
# repo
# -------------------------
class IndustryRepo:
    """
    Uses bls_oews only.

    Your dataset reality:
      - You may have "o_group" or not. So we ALWAYS fall back safely.

    IMPORTANT:
      - Industry total employment + median salary come from the industry's
        "All Occupations" row:
            occ_code == "00-0000"
        If o_group exists, we prefer o_group == "total" but don't require it.

      - Jobs list excludes occ_code == "00-0000"
    """

    def __init__(self, db: "AgnosticDatabase"):
        self.db = db
        self._onet_bls_codes_cache: Optional[set[str]] = None
        self._onet_bls_codes_cache_time: float = 0.0

    async def _get_onet_bls_codes(self, force_refresh: bool = False) -> set[str]:
        """
        Build cached set of BLS occ_code values that have O*NET detail.
        Reads onet_soc from core O*NET collections and converts *.00 -> BLS format.
        """
        now = time.time()
        if (
            self._onet_bls_codes_cache is None
            or force_refresh
            or (now - self._onet_bls_codes_cache_time) > 300
        ):
            collections = ["skills", "technology_skills", "abilities", "knowledge", "work_activities"]
            tasks = [self.db[c].distinct("onet_soc") for c in collections]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            codes: set[str] = set()
            for res in results:
                if isinstance(res, Exception):
                    continue
                for soc in res:
                    if not isinstance(soc, str):
                        continue
                    code = soc.replace(".00", "").strip()
                    if code:
                        codes.add(code)

            self._onet_bls_codes_cache = codes
            self._onet_bls_codes_cache_time = now

        return self._onet_bls_codes_cache or set()

    async def _latest_year(self) -> Optional[int]:
        doc = (
            await self.db["bls_oews"]
            .find({}, {"year": 1, "_id": 0})
            .sort("year", -1)
            .limit(1)
            .to_list(length=1)
        )
        return int(doc[0]["year"]) if doc else None

    # -------------------------
    # industries list
    # -------------------------
    async def list_industries(self, year: Optional[int]) -> Tuple[int, List[Dict[str, str]]]:
        if year is None:
            year = await self._latest_year()
            if year is None:
                return 0, []

        # Prefer using All-Occupations rows to reduce duplicates
        pipeline = [
            {
                "$match": {
                    "year": int(year),
                    "naics": {"$ne": None},
                    "naics_title": {"$ne": None},
                    "occ_code": "00-0000",
                }
            },
            {"$group": {"_id": {"naics": "$naics", "naics_title": "$naics_title"}}},
            {"$project": {"_id": 0, "naics": "$_id.naics", "naics_title": "$_id.naics_title"}},
            {"$sort": {"naics_title": 1}},
        ]

        out: List[Dict[str, str]] = []
        async for row in self.db["bls_oews"].aggregate(pipeline):
            naics = str(row.get("naics", "")).strip()
            title = str(row.get("naics_title", "")).strip()
            if naics and title:
                out.append({"naics": naics, "naics_title": title})

        # Fallback if dataset doesn't have 00-0000 rows
        if not out:
            pipeline2 = [
                {"$match": {"year": int(year), "naics": {"$ne": None}, "naics_title": {"$ne": None}}},
                {"$group": {"_id": {"naics": "$naics", "naics_title": "$naics_title"}}},
                {"$project": {"_id": 0, "naics": "$_id.naics", "naics_title": "$_id.naics_title"}},
                {"$sort": {"naics_title": 1}},
            ]
            async for row in self.db["bls_oews"].aggregate(pipeline2):
                naics = str(row.get("naics", "")).strip()
                title = str(row.get("naics_title", "")).strip()
                if naics and title:
                    out.append({"naics": naics, "naics_title": title})

        # Unique guard
        uniq: Dict[Tuple[str, str], Dict[str, str]] = {}
        for r in out:
            uniq[(r["naics"], r["naics_title"])] = r

        industries = list(uniq.values())
        industries.sort(key=lambda x: x["naics_title"].lower())
        return int(year), industries

    async def get_naics_title(self, naics: str, year: Optional[int] = None) -> str:
        q: Dict[str, Any] = {"naics": naics}
        if year is not None:
            q["year"] = int(year)
        doc = await self.db["bls_oews"].find_one(q, {"naics_title": 1, "_id": 0})
        return str(doc.get("naics_title", "")).strip() if doc else ""

    # -------------------------
    # jobs (exclude 00-0000)
    # -------------------------
    async def jobs_in_industry(self, naics: str, year: int) -> List[Dict[str, Any]]:
        onet_codes = await self._get_onet_bls_codes()
        if not onet_codes:
            return []

        cursor = self.db["bls_oews"].find(
            {"year": int(year), "naics": naics, "occ_code": {"$in": list(onet_codes)}},
            {"occ_code": 1, "occ_title": 1, "tot_emp": 1, "a_median": 1, "naics_title": 1, "_id": 0},
        )

        rows: List[Dict[str, Any]] = []
        async for doc in cursor:
            emp = _to_float(doc.get("tot_emp"))
            sal = _to_float(doc.get("a_median"))
            rows.append(
                {
                    "occ_code": str(doc.get("occ_code", "")).strip(),
                    "occ_title": str(doc.get("occ_title", "")).strip(),
                    "employment": emp,
                    "median_salary": sal if sal > 0 else None,
                    "naics_title": str(doc.get("naics_title", "")).strip(),
                }
            )

        rows.sort(key=lambda x: x["employment"], reverse=True)
        return rows

    async def top_jobs_in_industry(self, naics: str, year: int, limit: int) -> Tuple[str, List[Dict[str, Any]]]:
        rows = await self.jobs_in_industry(naics, year)
        naics_title = rows[0]["naics_title"] if rows else await self.get_naics_title(naics, year)
        return naics_title, rows[: max(1, int(limit))]

    async def top_job_in_industry(self, naics: str, year: int) -> Tuple[str, Optional[Dict[str, Any]]]:
        title, rows = await self.top_jobs_in_industry(naics, year, limit=1)
        return title, (rows[0] if rows else None)

    # -------------------------
    # industry metrics from all-occupations row
    # -------------------------
    async def _industry_total_row(self, naics: str, year: int) -> Optional[Dict[str, Any]]:
        # Prefer strict if o_group exists and equals "total"
        doc = await self.db["bls_oews"].find_one(
            {"year": int(year), "naics": naics, "occ_code": "00-0000", "o_group": "total"},
            {"_id": 0, "naics": 1, "naics_title": 1, "year": 1, "tot_emp": 1, "a_median": 1},
        )
        if doc:
            return doc

        # Fallback if no o_group in DB
        doc2 = await self.db["bls_oews"].find_one(
            {"year": int(year), "naics": naics, "occ_code": "00-0000"},
            {"_id": 0, "naics": 1, "naics_title": 1, "year": 1, "tot_emp": 1, "a_median": 1},
        )
        return doc2

    async def industry_metrics(self, naics: str, year: int) -> Tuple[str, float, float]:
        doc = await self._industry_total_row(naics, year)
        if not doc:
            title = await self.get_naics_title(naics, year)
            return title, 0.0, 0.0

        naics_title = str(doc.get("naics_title", "")).strip() or await self.get_naics_title(naics, year)
        total_emp = _to_float(doc.get("tot_emp"))
        med_sal = _to_float(doc.get("a_median"))

        return naics_title, round(total_emp, 2), round(med_sal, 2)

    async def industry_summary(self, naics: str, year_from: int, year_to: int) -> Tuple[str, List[Dict[str, Any]]]:
        if year_to < year_from:
            year_from, year_to = year_to, year_from

        naics_title = ""
        series: List[Dict[str, Any]] = []

        for y in range(int(year_from), int(year_to) + 1):
            title, total_emp, med_sal = await self.industry_metrics(naics, y)
            if not naics_title and title:
                naics_title = title
            series.append({"year": y, "total_employment": total_emp, "median_salary": med_sal})

        if not naics_title:
            naics_title = await self.get_naics_title(naics, year_to)

        return naics_title, series

    # -------------------------
    # dashboard metrics
    # -------------------------
    async def dashboard_metrics(self, year: int) -> Dict[str, Any]:
        """
        Uses each industry's All Occupations row (occ_code=00-0000)
        If o_group exists, prefers o_group=total.
        """
        # Cross-industry totals drive overall employment + median salary.
        cross_doc = await self.db["bls_oews"].find_one(
            {
                "year": int(year),
                "naics": "000000",
                "occ_code": "00-0000",
                "occ_title": "All Occupations",
                "naics_title": {"$regex": "^Cross-industry$", "$options": "i"},
            },
            {"_id": 0, "tot_emp": 1, "a_median": 1},
        ) or {}
        cross_total_employment = _to_float(cross_doc.get("tot_emp"))
        cross_median_salary = _to_float(cross_doc.get("a_median"))

        cursor = self.db["bls_oews"].find(
            {"year": int(year), "occ_code": "00-0000"},
            {"naics": 1, "naics_title": 1, "tot_emp": 1, "a_median": 1, "o_group": 1, "_id": 0},
        )

        emp_by_naics: Dict[str, float] = defaultdict(float)
        title_by_naics: Dict[str, str] = {}
        med_sal_by_naics: Dict[str, float] = {}

        async for doc in cursor:
            # prefer only total rows if o_group exists
            if "o_group" in doc and str(doc.get("o_group", "")).strip().lower() not in ("", "total"):
                continue

            naics = str(doc.get("naics", "")).strip()
            title = str(doc.get("naics_title", "")).strip()
            title_lc = title.lower()
            if naics == "000000" or "cross-industry" in title_lc:
                continue
            if not naics:
                continue

            title_by_naics[naics] = title or title_by_naics.get(naics, "")
            emp_by_naics[naics] = _to_float(doc.get("tot_emp"))
            med_sal_by_naics[naics] = _to_float(doc.get("a_median"))

        # Count unique industries by title (case-insensitive), excluding blanks.
        unique_titles = {
            str(title).strip().lower()
            for title in title_by_naics.values()
            if str(title).strip()
        }
        total_industries = len(unique_titles)
        total_employment = cross_total_employment
        median_industry_salary = cross_median_salary if cross_median_salary > 0 else _median(
            [v for v in med_sal_by_naics.values() if v > 0]
        )

        # growth vs previous year
        avg_growth = 0.0
        top_growing = None

        if int(year) > 2011:
            prev_year = int(year) - 1
            prev_cursor = self.db["bls_oews"].find(
                {"year": prev_year, "occ_code": "00-0000"},
                {"naics": 1, "tot_emp": 1, "o_group": 1, "naics_title": 1, "_id": 0},
            )

            prev_emp: Dict[str, float] = {}
            prev_title: Dict[str, str] = {}

            async for doc in prev_cursor:
                if "o_group" in doc and str(doc.get("o_group", "")).strip().lower() not in ("", "total"):
                    continue

                naics = str(doc.get("naics", "")).strip()
                title = str(doc.get("naics_title", "")).strip()
                if naics == "000000" or "cross-industry" in title.lower():
                    continue
                if not naics:
                    continue
                prev_emp[naics] = _to_float(doc.get("tot_emp"))
                prev_title[naics] = title

            growths: List[float] = []
            best = float("-inf")
            best_naics = ""
            best_title = ""

            for naics, cur_emp in emp_by_naics.items():
                p = prev_emp.get(naics, 0.0)
                if p > 0:
                    g = ((cur_emp - p) / p) * 100.0
                    growths.append(g)
                    if g > best:
                        best = g
                        best_naics = naics
                        best_title = title_by_naics.get(naics, "") or prev_title.get(naics, "")

            avg_growth = float(sum(growths) / len(growths)) if growths else 0.0
            if best_naics:
                top_growing = {"naics": best_naics, "naics_title": best_title, "growth_pct": round(best, 2)}

        return {
            "year": int(year),
            "total_industries": int(total_industries),
            "total_employment": round(total_employment, 2),
            "avg_industry_growth_pct": round(avg_growth, 2),
            "top_growing_industry": top_growing,
            "median_industry_salary": round(median_industry_salary, 2),
        }

    # -------------------------
    # top industries + growth
    # -------------------------
    async def top_industries(
        self,
        year: int,
        limit: int = 6,
        by: Literal["employment", "salary"] = "employment",
        exclude_cross_industry: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Uses only occ_code == "00-0000" per industry.
        IMPORTANT: We sort in Python because tot_emp may be stored as strings with commas.
        """
        q: Dict[str, Any] = {"year": int(year), "occ_code": "00-0000"}
        if exclude_cross_industry:
            q["naics"] = {"$ne": "000000"}
            q["naics_title"] = {"$not": {"$regex": "Cross-industry", "$options": "i"}}

        proj = {"_id": 0, "naics": 1, "naics_title": 1, "tot_emp": 1, "a_median": 1}
        cursor = self.db["bls_oews"].find(q, proj)

        rows: List[Dict[str, Any]] = []
        async for doc in cursor:
            rows.append(
                {
                    "naics": str(doc.get("naics", "")).strip(),
                    "naics_title": str(doc.get("naics_title", "")).strip(),
                    "total_employment": _to_float(doc.get("tot_emp")),
                    "median_salary": _to_float(doc.get("a_median")),
                }
            )

        key = "total_employment" if by == "employment" else "median_salary"
        rows.sort(key=lambda r: r.get(key, 0.0), reverse=True)

        # De-dupe by industry title (case-insensitive) after sorting, then limit.
        seen_titles: set[str] = set()
        unique: List[Dict[str, Any]] = []
        for r in rows:
            title = str(r.get("naics_title", "")).strip()
            if not title:
                continue
            tkey = title.lower()
            if tkey in seen_titles:
                continue
            seen_titles.add(tkey)
            unique.append(r)
            if len(unique) >= max(1, int(limit)):
                break

        return unique

    async def top_industries_with_growth(self, year: int, limit: int = 6) -> List[Dict[str, Any]]:
        top = await self.top_industries(year=year, limit=limit, by="employment")
        if not top:
            return []

        prev_map: Dict[str, float] = {}
        if int(year) > 2011:
            prev_cursor = self.db["bls_oews"].find(
                {"year": int(year) - 1, "occ_code": "00-0000", "naics": {"$ne": "000000"}},
                {"_id": 0, "naics": 1, "tot_emp": 1},
            )
            async for doc in prev_cursor:
                prev_map[str(doc.get("naics", "")).strip()] = _to_float(doc.get("tot_emp"))

        for r in top:
            p = prev_map.get(r["naics"], 0.0)
            c = r["total_employment"]
            r["growth_pct"] = round(((c - p) / p) * 100.0, 2) if p > 0 else None

        return top

    # -------------------------
    # trends: top industries time series
    # -------------------------
    async def top_industries_trends(self, year_from: int, year_to: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get time series data for top industries by employment.
        
        Args:
            year_from: Start year
            year_to: End year
            limit: Number of top industries to return (default: 10)
        
        Returns:
            List of industry trend data with points for each year
        """
        if year_to < year_from:
            year_from, year_to = year_to, year_from

        # Get top industries by employment for the latest year in the range
        top = await self.top_industries(year=year_to, limit=limit, by="employment")
        naics_list = [t["naics"] for t in top if t.get("naics")]
        
        if not naics_list:
            return []

        # Query data for all these industries across the year range
        q = {
            "year": {"$gte": int(year_from), "$lte": int(year_to)},
            "occ_code": "00-0000",
            "naics": {"$in": naics_list},
        }
        proj = {"_id": 0, "naics": 1, "naics_title": 1, "year": 1, "tot_emp": 1}
        cursor = self.db["bls_oews"].find(q, proj)

        # Organize by NAICS code
        by_naics: Dict[str, Dict[str, Any]] = {}
        async for doc in cursor:
            naics = str(doc.get("naics", "")).strip()
            title = str(doc.get("naics_title", "")).strip()
            y = int(doc.get("year"))
            emp = _to_float(doc.get("tot_emp"))
            
            if naics not in by_naics:
                by_naics[naics] = {"naics": naics, "naics_title": title, "points": []}
            by_naics[naics]["points"].append({"year": y, "employment": emp})

        # Build output in the same order as top industries
        out: List[Dict[str, Any]] = []
        for t in top:
            naics = t["naics"]
            if naics in by_naics:
                # Sort points by year ascending
                by_naics[naics]["points"].sort(key=lambda p: p["year"])
                out.append(by_naics[naics])

        return out

    # -------------------------
    # composition: junior/mid/senior by salary bands
    # -------------------------
    async def composition_by_industry(self, year: int, limit: int = 6) -> List[Dict[str, Any]]:
        top = await self.top_industries(year=year, limit=limit, by="employment")
        naics_list = [t["naics"] for t in top if t.get("naics")]
        title_map = {t["naics"]: t["naics_title"] for t in top}
        if not naics_list:
            return []

        q = {"year": int(year), "naics": {"$in": naics_list}, "occ_code": {"$ne": "00-0000"}}
        proj = {"_id": 0, "naics": 1, "tot_emp": 1, "a_median": 1}
        cursor = self.db["bls_oews"].find(q, proj)

        per_naics_rows: Dict[str, List[Dict[str, float]]] = {}
        per_naics_salaries: Dict[str, List[float]] = {}

        async for doc in cursor:
            naics = str(doc.get("naics", "")).strip()
            emp = _to_float(doc.get("tot_emp"))
            sal = _to_float(doc.get("a_median"))
            if not naics:
                continue
            per_naics_rows.setdefault(naics, []).append({"emp": emp, "sal": sal})
            if sal > 0:
                per_naics_salaries.setdefault(naics, []).append(sal)

        out: List[Dict[str, Any]] = []
        for naics in naics_list:
            salaries = sorted(per_naics_salaries.get(naics, []))
            q1 = _quantile(salaries, 0.25)
            q3 = _quantile(salaries, 0.75)

            jr = mid = sr = 0.0
            for r in per_naics_rows.get(naics, []):
                emp = r["emp"]
                sal = r["sal"]
                if sal <= 0:
                    mid += emp
                elif sal <= q1:
                    jr += emp
                elif sal <= q3:
                    mid += emp
                else:
                    sr += emp

            out.append(
                {
                    "industry": title_map.get(naics, naics),
                    "juniorRoles": round(jr, 2),
                    "midRoles": round(mid, 2),
                    "seniorRoles": round(sr, 2),
                }
            )

        return out

    # -------------------------
    # ✅ FIXED: top occupations composition (NO mongo sorting on string tot_emp)
    # -------------------------
    async def top_occupations_composition(
    self,
    year: int,
    industries_limit: int = 6,
    top_n_occ: int = 3,
) -> Dict[str, Any]:
     """
    For top N industries (by total employment), return stacked-bar rows of top N occupations
    (by employment) inside each industry.

    Adds:
      - occ{i}_title for each top occupation i
    """
     top_inds = await self.top_industries(year=year, limit=industries_limit, by="employment")
     naics_list = [t["naics"] for t in top_inds if t.get("naics")]
     title_map = {t["naics"]: t.get("naics_title", t["naics"]) for t in top_inds}

     if not naics_list:
        return {
            "year": int(year),
            "industries_limit": int(industries_limit),
            "top_n_occ": int(top_n_occ),
            "rows": [],
            "legend": [],
        }

    # For each industry, fetch occupations and pick top N by parsed employment.
     per_naics_top: Dict[str, List[Dict[str, Any]]] = {}

     for naics in naics_list:
        cur = self.db["bls_oews"].find(
            {"year": int(year), "naics": naics, "occ_code": {"$ne": "00-0000"}},
            {"_id": 0, "occ_title": 1, "tot_emp": 1},
        )

        occs: List[Dict[str, Any]] = []
        async for d in cur:
            emp = _to_float(d.get("tot_emp"))
            if emp <= 0:
                continue
            occs.append(
                {
                    "occ_title": str(d.get("occ_title", "")).strip(),
                    "emp": emp,
                }
            )

        occs.sort(key=lambda x: x["emp"], reverse=True)
        per_naics_top[naics] = occs[: max(1, int(top_n_occ))]

    # legend: “Top Occupation #1/#2/#3” (stable across industries)
     legend = [{"key": f"occ{i}_emp", "name": f"Top Occupation #{i}"} for i in range(1, int(top_n_occ) + 1)]

     rows: List[Dict[str, Any]] = []
     for naics in naics_list:
        occs = per_naics_top.get(naics, [])
        row: Dict[str, Any] = {
            "industry": title_map.get(naics, naics),
            "industry_naics": naics,  # optional, handy for debugging/frontend
        }

        for i in range(1, int(top_n_occ) + 1):
            idx = i - 1
            if idx < len(occs):
                row[f"occ{i}_emp"] = round(float(occs[idx]["emp"]), 2)
                row[f"occ{i}_title"] = occs[idx]["occ_title"]
            else:
                row[f"occ{i}_emp"] = 0.0
                row[f"occ{i}_title"] = ""

        rows.append(row)

     return {
        "year": int(year),
        "industries_limit": int(industries_limit),
        "top_n_occ": int(top_n_occ),
        "rows": rows,
        "legend": legend,
    }

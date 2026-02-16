from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from motor.core import AgnosticDatabase


class SalaryRepo:
    def __init__(self, db: AgnosticDatabase):
        self.col = db["bls_oews"]

    async def latest_year(self) -> int:
        doc = await self.col.find({}, {"year": 1}).sort("year", -1).limit(1).to_list(1)
        if not doc:
            raise ValueError("bls_oews is empty")
        return int(doc[0]["year"])

    # ---------------------------
    # Helpers
    # ---------------------------
    @staticmethod
    def _num(field: str) -> Dict[str, Any]:
        """
        Safely convert numeric fields that may be stored as int/float/string into a number.
        """
        return {
            "$convert": {
                "input": f"${field}",
                "to": "double",
                "onError": 0,
                "onNull": 0,
            }
        }

    @staticmethod
    def _not_cross_industry_match() -> Dict[str, Any]:
        # excludes titles containing "Cross-industry" (case-insensitive)
        return {"naics_title": {"$not": {"$regex": "Cross-industry", "$options": "i"}}}

    # ---------------------------
    # METRICS
    # ---------------------------
    async def dashboard_metrics(self, year: int) -> dict:
        prev_year = year - 1

        async def read_cross_allocc(y: int) -> Dict[str, Any]:
            pipeline = [
                {
                    "$match": {
                        "year": y,
                        "naics_title": {"$regex": "^Cross-industry$", "$options": "i"},
                        "occ_title": "All Occupations",
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "totalEmployment": {"$max": self._num("tot_emp")},
                        "medianSalary": {"$max": self._num("a_median")},
                    }
                },
                {"$project": {"_id": 0, "totalEmployment": 1, "medianSalary": 1}},
            ]
            rows = await self.col.aggregate(pipeline).to_list(1)
            if not rows:
                return {"totalEmployment": 0, "medianSalary": 0}
            return rows[0]

        cur = await read_cross_allocc(year)
        prev = await read_cross_allocc(prev_year) if prev_year >= 0 else {"totalEmployment": 0, "medianSalary": 0}

        total_emp_cur = int(cur.get("totalEmployment") or 0)
        med_sal_cur = int(cur.get("medianSalary") or 0)
        total_emp_prev = int(prev.get("totalEmployment") or 0)
        med_sal_prev = int(prev.get("medianSalary") or 0)

        def yoy(cur_v: int, prev_v: int) -> float:
            return 0.0 if prev_v <= 0 else round(((cur_v - prev_v) / prev_v) * 100.0, 2)

        emp_trend = yoy(total_emp_cur, total_emp_prev)
        sal_trend = yoy(med_sal_cur, med_sal_prev)

        # Highest paying industry (All Occupations only, exclude Cross-industry)
        top_pay_pipeline = [
            {"$match": {"year": year, "occ_title": "All Occupations", **self._not_cross_industry_match()}},
            {"$match": {"naics_title": {"$type": "string"}}},
            {
                "$group": {
                    "_id": "$naics_title",
                    "medianSalary": {"$max": self._num("a_median")},
                }
            },
            {"$project": {"_id": 0, "name": "$_id", "medianSalary": 1}},
            {"$sort": {"medianSalary": -1}},
            {"$limit": 1},
        ]
        top_pay = await self.col.aggregate(top_pay_pipeline).to_list(1)
        top_industry = top_pay[0]["name"] if top_pay else "N/A"

        return {
            "totalEmployment": total_emp_cur,
            "medianSalary": med_sal_cur,
            "employmentTrendPct": emp_trend,
            "salaryTrendPct": sal_trend,
            "topIndustry": top_industry,
        }

    # ---------------------------
    # INDUSTRY BAR (✅ UNIQUE by title, top salary)
    # ---------------------------
    async def industry_bar(self, year: int, search: Optional[str], limit: int) -> List[dict]:
        match: Dict[str, Any] = {
            "year": year,
            "occ_title": "All Occupations",
            **self._not_cross_industry_match(),
            "naics_title": {"$type": "string"},
        }

        if search:
            match["naics_title"] = {"$type": "string", "$regex": search, "$options": "i"}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$naics_title",  # ✅ unique
                    "employment": {"$max": self._num("tot_emp")},
                    "medianSalary": {"$max": self._num("a_median")},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "name": "$_id",
                    "value": "$employment",
                    "secondaryValue": "$medianSalary",
                }
            },
            {"$sort": {"secondaryValue": -1}},
            {"$limit": min(limit, 50)},
        ]

        rows = await self.col.aggregate(pipeline).to_list(length=min(limit, 50))
        out: List[dict] = []
        for r in rows:
            name = str(r.get("name") or "").strip()
            if not name:
                continue
            out.append(
                {
                    "name": name,
                    "value": int(r.get("value") or 0),
                    "secondaryValue": int(r.get("secondaryValue") or 0),
                }
            )
        return out

    # ---------------------------
    # ✅ TOP CROSS-INDUSTRY JOBS (for the Job chart)
    # ---------------------------
    async def top_cross_industry_jobs(self, year: int, limit: int = 10) -> List[dict]:
        """
        Returns top N job titles from Cross-industry, sorted by median salary DESC.
        Uses Cross-industry rows in bls_oews (naics_title == 'Cross-industry').
        """
        pipeline = [
            {
                "$match": {
                    "year": year,
                    "naics_title": {"$regex": "^Cross-industry$", "$options": "i"},
                    "occ_title": {"$nin": ["All Occupations", "Industry Total"]},
                }
            },
            {
                "$group": {
                    "_id": {"code": "$occ_code", "title": "$occ_title"},
                    "employment": {"$max": self._num("tot_emp")},
                    "medianSalary": {"$max": self._num("a_median")},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "name": "$_id.title",
                    "value": "$employment",
                    "secondaryValue": "$medianSalary",
                }
            },
            {"$sort": {"secondaryValue": -1}},
            {"$limit": min(max(limit, 1), 50)},
        ]

        rows = await self.col.aggregate(pipeline).to_list(length=min(max(limit, 1), 50))
        out: List[dict] = []
        for r in rows:
            nm = str(r.get("name") or "").strip()
            if not nm:
                continue
            out.append(
                {
                    "name": nm,
                    "value": int(r.get("value") or 0),
                    "secondaryValue": int(r.get("secondaryValue") or 0),
                }
            )
        return out

    # ---------------------------
    # INDUSTRIES TABLE (paged)
    # ---------------------------
    async def industries_paged(
        self,
        year: int,
        search: Optional[str],
        page: int,
        page_size: int,
        sort_by: str = "employment",
        sort_dir: int = -1,
    ) -> Tuple[int, List[dict]]:
        match: Dict[str, Any] = {
            "year": year,
            "occ_title": "All Occupations",
            **self._not_cross_industry_match(),
        }
        if search:
            match["naics_title"] = {"$regex": search, "$options": "i"}

        sort_field = {"employment": "employment", "salary": "medianSalary", "name": "name"}.get(sort_by, "employment")

        base_pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"naics": "$naics", "title": "$naics_title"},
                    "employment": {"$max": self._num("tot_emp")},
                    "medianSalary": {"$max": self._num("a_median")},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "id": "$_id.naics",
                    "name": "$_id.title",
                    "employment": 1,
                    "medianSalary": 1,
                }
            },
        ]

        total_doc = await self.col.aggregate(base_pipeline + [{"$count": "total"}]).to_list(1)
        total = int(total_doc[0]["total"]) if total_doc else 0

        skip = max(page - 1, 0) * page_size
        items = await self.col.aggregate(
            base_pipeline
            + [
                {"$sort": {sort_field: sort_dir}},
                {"$skip": skip},
                {"$limit": page_size},
            ]
        ).to_list(page_size)

        for it in items:
            it["employment"] = int(it.get("employment") or 0)
            it["medianSalary"] = int(it.get("medianSalary") or 0)

        # YoY trend based on employment
        prev_year = year - 1
        if prev_year >= 0 and items:
            ids = [it["id"] for it in items if it.get("id")]
            prev_map = await self._industry_employment_map(prev_year, ids)
            for it in items:
                prev = prev_map.get(it["id"], 0)
                cur = it["employment"]
                it["trend"] = 0.0 if prev <= 0 else round(((cur - prev) / prev) * 100.0, 2)
        else:
            for it in items:
                it["trend"] = 0.0

        return total, items

    async def _industry_employment_map(self, year: int, naics_ids: List[str]) -> Dict[str, int]:
        pipeline = [
            {
                "$match": {
                    "year": year,
                    "occ_title": "All Occupations",
                    "naics": {"$in": naics_ids},
                    **self._not_cross_industry_match(),
                }
            },
            {"$group": {"_id": "$naics", "employment": {"$max": self._num("tot_emp")}}},
            {"$project": {"_id": 0, "id": "$_id", "employment": 1}},
        ]
        rows = await self.col.aggregate(pipeline).to_list(length=max(10, len(naics_ids)))
        return {r["id"]: int(r.get("employment") or 0) for r in rows}

    # ---------------------------
    # JOBS TABLE (paged)
    # ---------------------------
    async def jobs_paged(
        self,
        year: int,
        search: Optional[str],
        page: int,
        page_size: int,
        sort_by: str = "salary",
        sort_dir: int = -1,
    ) -> Tuple[int, List[dict]]:
        match: Dict[str, Any] = {"year": year}
        if search:
            match["occ_title"] = {"$regex": search, "$options": "i"}

        # exclude Industry Total rows
        match["occ_title"] = match.get("occ_title", {})
        if isinstance(match["occ_title"], dict):
            match["occ_title"]["$ne"] = "Industry Total"
        else:
            match["occ_title"] = {"$regex": match["occ_title"], "$options": "i", "$ne": "Industry Total"}

        sort_field = {
            "employment": "employment",
            "salary": "medianSalary",
            "name": "occ_title",
        }.get(sort_by, "medianSalary")

        base_pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"code": "$occ_code", "title": "$occ_title"},
                    "employment": {"$max": self._num("tot_emp")},
                    "medianSalary": {"$max": self._num("a_median")},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "occ_code": "$_id.code",
                    "occ_title": "$_id.title",
                    "employment": 1,
                    "medianSalary": 1,
                }
            },
        ]

        total_doc = await self.col.aggregate(base_pipeline + [{"$count": "total"}]).to_list(1)
        total = int(total_doc[0]["total"]) if total_doc else 0

        skip = max(page - 1, 0) * page_size
        items = await self.col.aggregate(
            base_pipeline
            + [
                {"$sort": {sort_field: sort_dir}},
                {"$skip": skip},
                {"$limit": page_size},
            ]
        ).to_list(page_size)

        for it in items:
            it["employment"] = int(it.get("employment") or 0)
            it["medianSalary"] = int(it.get("medianSalary") or 0)

        prev_year = year - 1
        if prev_year >= 0 and items:
            codes = [it["occ_code"] for it in items if it.get("occ_code")]
            prev_map = await self._job_employment_map(prev_year, codes)
            for it in items:
                prev = prev_map.get(it["occ_code"], 0)
                cur = it["employment"]
                it["trend"] = 0.0 if prev <= 0 else round(((cur - prev) / prev) * 100.0, 2)
        else:
            for it in items:
                it["trend"] = 0.0

        return total, items

    async def _job_employment_map(self, year: int, occ_codes: List[str]) -> Dict[str, int]:
        pipeline = [
            {"$match": {"year": year, "occ_code": {"$in": occ_codes}, "occ_title": {"$ne": "Industry Total"}}},
            {"$group": {"_id": "$occ_code", "employment": {"$max": self._num("tot_emp")}}},
            {"$project": {"_id": 0, "occ_code": "$_id", "employment": 1}},
        ]
        rows = await self.col.aggregate(pipeline).to_list(length=max(10, len(occ_codes)))
        return {r["occ_code"]: int(r.get("employment") or 0) for r in rows}

    # ---------------------------
    # INDUSTRY SALARY TIME SERIES
    # ---------------------------
    async def industry_salary_timeseries(
        self,
        names: List[str],
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> List[dict]:
        match: Dict[str, Any] = {
            "naics_title": {"$in": names, "$type": "string"},
            "occ_title": "All Occupations",
            **self._not_cross_industry_match(),
        }

        if start_year is not None or end_year is not None:
            yr: Dict[str, Any] = {}
            if start_year is not None:
                yr["$gte"] = start_year
            if end_year is not None:
                yr["$lte"] = end_year
            match["year"] = yr

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"name": "$naics_title", "year": "$year"},
                    "value": {"$max": self._num("a_median")},
                }
            },
            {"$project": {"_id": 0, "name": "$_id.name", "year": "$_id.year", "value": "$value"}},
            {"$sort": {"name": 1, "year": 1}},
        ]

        rows = await self.col.aggregate(pipeline).to_list(length=5000)
        for r in rows:
            r["year"] = int(r["year"])
            r["value"] = int(r.get("value") or 0)
        return rows

    # ---------------------------
    # JOB EMPLOYMENT TIME SERIES
    # ---------------------------
    async def job_employment_timeseries(
        self,
        year: int,
        limit: int = 6,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> List[dict]:
        top_limit = min(max(limit, 1), 20)

        # Pick top jobs by employment in the selected anchor year (cross-industry only).
        top_pipeline = [
            {
                "$match": {
                    "year": year,
                    "naics_title": {"$regex": "^Cross-industry$", "$options": "i"},
                    "occ_title": {"$nin": ["All Occupations", "Industry Total"]},
                }
            },
            {
                "$group": {
                    "_id": {"occ_code": "$occ_code", "occ_title": "$occ_title"},
                    "employment": {"$max": self._num("tot_emp")},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "occ_code": "$_id.occ_code",
                    "occ_title": "$_id.occ_title",
                    "employment": 1,
                }
            },
            {"$sort": {"employment": -1}},
            {"$limit": top_limit},
        ]
        top_rows = await self.col.aggregate(top_pipeline).to_list(length=top_limit)
        if not top_rows:
            return []

        order: List[str] = []
        title_by_code: Dict[str, str] = {}
        for r in top_rows:
            code = str(r.get("occ_code") or "").strip()
            title = str(r.get("occ_title") or "").strip()
            if not code or not title:
                continue
            if code in title_by_code:
                continue
            order.append(code)
            title_by_code[code] = title

        if not order:
            return []

        match: Dict[str, Any] = {
            "naics_title": {"$regex": "^Cross-industry$", "$options": "i"},
            "occ_code": {"$in": order},
            "occ_title": {"$nin": ["All Occupations", "Industry Total"]},
        }
        if start_year is not None or end_year is not None:
            yr: Dict[str, Any] = {}
            if start_year is not None:
                yr["$gte"] = start_year
            if end_year is not None:
                yr["$lte"] = end_year
            match["year"] = yr

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"occ_code": "$occ_code", "year": "$year"},
                    "employment": {"$max": self._num("tot_emp")},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "occ_code": "$_id.occ_code",
                    "year": "$_id.year",
                    "value": "$employment",
                }
            },
            {"$sort": {"occ_code": 1, "year": 1}},
        ]

        rows = await self.col.aggregate(pipeline).to_list(length=10000)
        by_code: Dict[str, List[dict]] = {code: [] for code in order}
        for r in rows:
            code = str(r.get("occ_code") or "").strip()
            if code not in by_code:
                continue
            by_code[code].append(
                {
                    "year": int(r.get("year") or 0),
                    "value": int(r.get("value") or 0),
                }
            )

        series: List[dict] = []
        for code in order:
            points = sorted(by_code.get(code, []), key=lambda p: p["year"])
            if not points:
                continue
            series.append(
                {
                    "occ_code": code,
                    "name": title_by_code.get(code, code),
                    "points": points,
                }
            )
        return series

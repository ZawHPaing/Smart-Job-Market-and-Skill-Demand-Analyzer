from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from motor.core import AgnosticDatabase


def _to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip().replace(",", "")
    if s in ("", "*", "#", "**", "nan", "NaN", "None"):
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


class OccupationsRepo:
    """
    Works with your bls_oews schema:
      fields: naics, occ_code, occ_title, group, tot_emp, a_median, year
    """

    CROSS_INDUSTRY_NAICS = "000000"

    def __init__(self, db: "AgnosticDatabase"):
        self.db = db

    # -----------------------------
    # Cross-industry (naics=000000)
    # -----------------------------
    async def metrics_for_year_cross(
        self,
        year: int,
        *,
        group: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
        exclude_all_occupations: bool = True,
    ) -> List[Dict[str, Any]]:
        return await self.metrics_for_year_in_naics(
            naics=self.CROSS_INDUSTRY_NAICS,
            year=year,
            group=group,
            limit=limit,
            offset=offset,
            exclude_all_occupations=exclude_all_occupations,
        )

    async def summary_for_occ_cross(
        self,
        occ_code: str,
        *,
        year_from: int,
        year_to: int,
        group: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.summary_for_occ_in_naics(
            naics=self.CROSS_INDUSTRY_NAICS,
            occ_code=occ_code,
            year_from=year_from,
            year_to=year_to,
            group=group,
        )

    # -----------------------------------------
    # ✅ Industry-specific (naics = specific)
    # -----------------------------------------
    async def metrics_for_year_in_naics(
        self,
        *,
        naics: str,
        year: int,
        group: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
        exclude_all_occupations: bool = True,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {"year": year, "naics": naics}
        if exclude_all_occupations:
            q["occ_code"] = {"$ne": "00-0000"}  # All Occupations row
        if group:
            q["group"] = group

        cursor = self.db["bls_oews"].find(
            q,
            {"_id": 0, "occ_code": 1, "occ_title": 1, "tot_emp": 1, "a_median": 1, "group": 1, "year": 1},
        )

        rows: List[Dict[str, Any]] = []
        async for doc in cursor:
            emp = _to_float(doc.get("tot_emp"))
            sal = _to_float(doc.get("a_median"))
            rows.append(
                {
                    "occ_code": str(doc.get("occ_code", "")).strip(),
                    "occ_title": str(doc.get("occ_title", "")).strip(),
                    "total_employment": emp,
                    "median_salary": sal if sal > 0 else None,
                    "group": str(doc.get("group", "")).strip() or None,
                }
            )

        rows.sort(key=lambda x: x["total_employment"], reverse=True)
        return rows[offset : offset + limit]

    async def summary_for_occ_in_naics(
        self,
        *,
        naics: str,
        occ_code: str,
        year_from: int,
        year_to: int,
        group: Optional[str] = None,
    ) -> Dict[str, Any]:
        if year_to < year_from:
            year_from, year_to = year_to, year_from

        q: Dict[str, Any] = {
            "occ_code": occ_code,
            "naics": naics,
            "year": {"$gte": year_from, "$lte": year_to},
        }
        if group:
            q["group"] = group

        cursor = self.db["bls_oews"].find(
            q,
            {"_id": 0, "year": 1, "tot_emp": 1, "a_median": 1, "occ_title": 1, "group": 1},
        ).sort("year", 1)

        series: List[Dict[str, Any]] = []
        occ_title = ""
        detected_group = group

        async for doc in cursor:
            if not occ_title:
                occ_title = str(doc.get("occ_title", "")).strip()
            if detected_group is None:
                g = str(doc.get("group", "")).strip()
                detected_group = g or None

            series.append(
                {
                    "year": int(doc.get("year")),
                    "total_employment": _to_float(doc.get("tot_emp")),
                    "median_salary": (_to_float(doc.get("a_median")) or None),
                }
            )

        return {
            "naics": naics,
            "occ_code": occ_code,
            "occ_title": occ_title,
            "year_from": year_from,
            "year_to": year_to,
            "group": detected_group,
            "series": series,
        }

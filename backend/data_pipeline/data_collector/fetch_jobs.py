import re
import pandas as pd
from datetime import datetime
from pymongo import MongoClient, UpdateOne
from typing import Dict, Any, List, Optional
from pathlib import Path
from skills_keywords import SKILL_KEYWORDS

# =============================
# CONFIG
# =============================
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
CSV_FILE = BASE_DIR / "data_pipeline" / "data" / "postings.csv"

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "jobdb"
COLLECTION_NAME = "jobs"

LIMIT_ROWS = 10  



# =============================
# HELPERS
# =============================
def clean_str(x: Any, default: str = "Unknown") -> str:
    if x is None:
        return default
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return default
    return s

def clean_number(x: Any, default: float = 0.0) -> float:
    if x is None:
        return default
    try:
        if isinstance(x, str):
            x = x.replace(",", "").strip()
        val = float(x)
        if pd.isna(val):
            return default
        return val
    except Exception:
        return default

def ms_to_datetime(ms: Any) -> Optional[datetime]:
    """Convert epoch milliseconds (e.g., 1713397508000.0) to UTC datetime."""
    if ms is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(float(ms)) / 1000)
    except Exception:
        return None


# =============================
# SKILL EXTRACTION
# =============================
def extract_skills_from_skills_desc(text: str) -> List[str]:
    """
    Extract skills from skills_desc ONLY if it looks like a skill list.
    Prevents sentence fragments from being stored.
    """
    if not text or text == "Unknown":
        return []

    t = str(text).strip()
    if t.lower() in {"nan", "none", ""}:
        return []

    # If it's too long, it's probably not a skills list
    if len(t) > 400:
        return []

    parts = re.split(r"[,\|;/\n•]+", t)
    out, seen = [], set()

    for p in parts:
        s = p.strip().lower().strip(" \"'`•.-:()[]{}")
        if not s:
            continue

        # Filter: avoid sentence chunks
        if len(s) > 40:
            continue
        if s.count(" ") > 3:
            continue

        # Basic allowed characters
        if not re.match(r"^[a-z0-9\+\#\.\-\s]+$", s):
            continue

        if s not in seen:
            seen.add(s)
            out.append(s)

    return out


def extract_skills_keyword_match(title: str, desc: str) -> List[str]:
    """
    Keyword match against a large SKILL_KEYWORDS dictionary.
    This is the fallback when skills_desc is missing/bad.
    """
    text = f"{title}\n{desc}".lower()
    found = []

    for canonical, variants in SKILL_KEYWORDS.items():
        for v in variants:
            if re.search(rf"(?<!\w){re.escape(v.lower())}(?!\w)", text):
                found.append(canonical)
                break

    # dedupe keep order
    seen = set()
    out = []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# =============================
# NORMALIZE + ENRICH
# =============================
def normalize_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    title = clean_str(row.get("title"))
    desc = clean_str(row.get("description"))

    doc: Dict[str, Any] = {}

    # important: job_id always stored as string (avoid float)
    job_id_raw = row.get("job_id")
    doc["job_id"] = clean_str(job_id_raw)

    doc["title"] = title
    doc["company"] = clean_str(row.get("company_name"))
    doc["location"] = clean_str(row.get("location"))
    doc["description"] = desc

    # salary = normalized_salary
    doc["salary"] = clean_number(row.get("normalized_salary"), 0.0)

    # job_type from work_type
    doc["job_type"] = clean_str(row.get("work_type"))

    # source from job_posting_url 
    doc["source"] = clean_str(row.get("job_posting_url"))

    # posted_date from listed_time (ms), fallback original_listed_time
    doc["posted_date"] = (
        ms_to_datetime(row.get("listed_time"))
        or ms_to_datetime(row.get("original_listed_time"))
    )

    #  skills:
    # 1) try skills_desc (only if it looks like skills)
    skills_desc = row.get("skills_desc")
    skills = extract_skills_from_skills_desc(skills_desc)

    # 2) fallback to keyword match (NOT splitting description)
    if not skills:
        skills = extract_skills_keyword_match(title, desc)

    doc["skills"] = skills

    # ingestion timestamp
    doc["date_collected"] = datetime.utcnow()

    return doc


def enrich_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.setdefault("missing_fields", [])
    doc.setdefault("derived_fields", [])
    doc.setdefault("data_quality", {})

    for f in ["job_id", "title", "company", "location", "description", "job_type", "source"]:
        if not doc.get(f) or doc.get(f) == "Unknown":
            doc["missing_fields"].append(f)

    if doc.get("salary", 0) == 0:
        doc["missing_fields"].append("salary")

    if doc.get("posted_date") is None:
        doc["missing_fields"].append("posted_date")

    if not doc.get("skills"):
        doc["missing_fields"].append("skills")

    doc["data_quality"]["missing_count"] = len(doc["missing_fields"])
    doc["data_quality"]["skills_count"] = len(doc.get("skills", []))
    doc["data_quality"]["has_salary"] = doc.get("salary", 0) > 0

    return doc


# =============================
# MAIN INSERT
# =============================
def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col = db[COLLECTION_NAME]
    col.create_index("job_id", unique=True)

    print("Reading CSV:", CSV_FILE)

    # ✅ make reading more robust (handles BOM + messy headers)
    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.replace("\ufeff", "", regex=False).str.strip()

    # ensure job_id stays as string (avoid pandas turning it into float)
    if "job_id" in df.columns:
        df["job_id"] = df["job_id"].astype(str).str.strip()
        df.loc[df["job_id"].isin(["nan", "None", ""]), "job_id"] = None

    df = df.head(LIMIT_ROWS)
    records = df.to_dict(orient="records")

    ops = []
    now = datetime.utcnow()

    for row in records:
        doc = enrich_doc(normalize_doc(row))

        if not doc.get("job_id") or doc["job_id"] == "Unknown":
            print("Skipping row (missing job_id):", row)
            continue

        doc["updated_at"] = now
        set_doc = dict(doc)

        ops.append(
            UpdateOne(
                {"job_id": doc["job_id"]},
                {"$set": set_doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )

    if not ops:
        print("No valid documents to insert.")
        return

    result = col.bulk_write(ops, ordered=False)
    upserted = len(result.upserted_ids) if result.upserted_ids else 0

    print(" Insert test completed (first 10 rows)")
    print(f"Upserted (new): {upserted}")
    print(f"Modified: {result.modified_count}")
    print(f"Matched: {result.matched_count}")

    print("\nSample docs in Mongo:")
    for d in col.find({}, {"_id": 0}).limit(10):
        print(d)


if __name__ == "__main__":
    main()

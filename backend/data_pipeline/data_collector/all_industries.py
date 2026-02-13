import pandas as pd
from pymongo import MongoClient
from pathlib import Path

# ---------- MongoDB ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]
collection = db["all_industries"]

# ---------- File path ----------

BASE_DIR = Path(__file__).resolve().parent.parent 
FILE_PATH = BASE_DIR / "data" /  "onet" / "All_industries.xlsx" 

# ---------- Load (auto-detect Excel vs CSV) ----------
if FILE_PATH.suffix.lower() == ".csv":
    df = pd.read_csv(FILE_PATH)
else:
    df = pd.read_excel(FILE_PATH)

# ---------- Normalize headers ----------
df.columns = [c.strip().lower() for c in df.columns]

# ---------- Map columns (handles your header names) ----------
# Your file shows: Code, Occupation, Projected Growth (2024-2034), Projected Job Openings (2024-2034), Industries
col_map = {
    "code": "code",
    "occupation": "occupation",
    "projected growth (2024-2034)": "projected_growth",
    "projected job openings (2024-2034)": "projected_job_openings",
    "industries": "industries",
}

missing = [c for c in col_map.keys() if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in {FILE_PATH.name}: {missing}")

df = df[list(col_map.keys())].rename(columns=col_map)

# ---------- Clean types ----------
# Ensure openings is numeric (may be string in Excel)
df["projected_job_openings"] = pd.to_numeric(df["projected_job_openings"], errors="coerce")

# Drop rows missing code or occupation
df = df.dropna(subset=["code", "occupation"])

# NaN -> None
df = df.where(pd.notnull(df), None)

# ---------- Insert ----------
records = df.to_dict("records")
BATCH_SIZE = 5000

for i in range(0, len(records), BATCH_SIZE):
    collection.insert_many(records[i:i + BATCH_SIZE])

print(" Inserted projections/industries data into:", collection.name)

import pandas as pd
from pymongo import MongoClient
from pathlib import Path

# ---------- MongoDB ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]


collection = db["abilities"]

# ---------- Path ----------

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/data_pipeline
EXCEL_FILE = BASE_DIR / "data" / "onet" / "Abilities.xlsx"  

# ---------- Read ----------
df = pd.read_excel(EXCEL_FILE)
df.columns = [c.strip().lower() for c in df.columns]

# ---------- Keep + rename ----------
KEEP_RENAME = {
    "o*net-soc code": "onet_soc",
    "title": "title",
    "element id": "element_id",
    "element name": "element_name",
    "scale id": "scale_id",
    "scale name": "scale_name",
    "data value": "data_value",
    "n": "n",
    "date": "date",
}

missing = [c for c in KEEP_RENAME.keys() if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in {EXCEL_FILE.name}: {missing}")

df = df[list(KEEP_RENAME.keys())].rename(columns=KEEP_RENAME)

# ---------- Clean ----------
df = df.where(pd.notnull(df), None)

# Optional: normalize types
# df["data_value"] = pd.to_numeric(df["data_value"], errors="coerce")
# df["n"] = pd.to_numeric(df["n"], errors="coerce")

# ---------- Insert (batch) ----------
records = df.to_dict("records")
BATCH_SIZE = 5000

for i in range(0, len(records), BATCH_SIZE):
    collection.insert_many(records[i:i + BATCH_SIZE])

print(" Inserted successfully into MongoDB:", collection.name)

import pandas as pd
from pymongo import MongoClient
from pathlib import Path

# ---------- MongoDB ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]
collection = db["onet_content_model"]

# ---------- Path ----------

BASE_DIR = Path(__file__).resolve().parent.parent  
EXCEL_FILE = BASE_DIR / "data" / "onet" / "Content Model Reference.xlsx"  
# ---------- Read Excel ----------
df = pd.read_excel(EXCEL_FILE)
df.columns = [c.strip().lower() for c in df.columns]

# ---------- Keep + rename ----------
KEEP_RENAME = {
    "element id": "element_id",
    "element name": "element_name",
    "description": "description",
}

missing = [c for c in KEEP_RENAME if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in {EXCEL_FILE.name}: {missing}")

df = df[list(KEEP_RENAME.keys())].rename(columns=KEEP_RENAME)

# ---------- Clean ----------
df = df.dropna(subset=["element_id"])
df = df.where(pd.notnull(df), None)

# ---------- Insert ----------
records = df.to_dict("records")
collection.insert_many(records)

print("Content model reference inserted successfully.")

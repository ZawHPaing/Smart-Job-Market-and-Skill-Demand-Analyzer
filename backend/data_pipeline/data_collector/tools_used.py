import pandas as pd
from pymongo import MongoClient
from pathlib import Path

# ---------- MongoDB ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]
collection = db["tools_used"]

# ---------- Path ----------

BASE_DIR = Path(__file__).resolve().parent.parent   
EXCEL_FILE = BASE_DIR / "data" / "onet" / "Tools Used.xlsx"  

# ---------- Read Excel ----------
df = pd.read_excel(EXCEL_FILE)
df.columns = [c.strip().lower() for c in df.columns]

# ---------- Keep + rename ----------
KEEP_RENAME = {
    "o*net-soc code": "onet_soc",
    "title": "title",
    "example": "example",
    "commodity code": "commodity_code",
    "commodity title": "commodity_title",
}

missing = [c for c in KEEP_RENAME if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in {EXCEL_FILE.name}: {missing}")

df = df[list(KEEP_RENAME.keys())].rename(columns=KEEP_RENAME)

# ---------- Clean ----------
df = df.where(pd.notnull(df), None)

# ---------- Insert in batches ----------
records = df.to_dict("records")
BATCH_SIZE = 5000

for i in range(0, len(records), BATCH_SIZE):
    collection.insert_many(records[i:i + BATCH_SIZE])

print("Tools used inserted successfully into MongoDB:", collection.name)

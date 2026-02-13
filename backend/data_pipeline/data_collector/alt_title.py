from pathlib import Path
import pandas as pd
from pymongo import MongoClient

# ---------- MongoDB connection ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]
collection = db["onet_alternate_titles"]

# ---------- Correct path handling ----------
BASE_DIR = Path(__file__).resolve().parent.parent
# now BASE_DIR = backend/data_pipeline

EXCEL_FILE = BASE_DIR / "data" / "onet" / "Alternate Titles.xlsx"

# ---------- Read Excel ----------
df = pd.read_excel(EXCEL_FILE)

# ---------- Normalize column names ----------
df.columns = [c.strip().lower() for c in df.columns]

# ---------- Keep only required columns ----------
KEEP_COLS = {
    "o*net-soc code": "onet_soc",
    "title": "title",
    "alternate title": "alternate_title"
}

df = df[list(KEEP_COLS.keys())].rename(columns=KEEP_COLS)

# ---------- Drop empty alternate titles ----------
df = df.dropna(subset=["alternate_title"])

# ---------- Replace NaN with None ----------
df = df.where(pd.notnull(df), None)

# ---------- Insert into MongoDB ----------
records = df.to_dict("records")

BATCH_SIZE = 5000
for i in range(0, len(records), BATCH_SIZE):
    collection.insert_many(records[i:i + BATCH_SIZE])

print(" Alternate titles inserted successfully.")


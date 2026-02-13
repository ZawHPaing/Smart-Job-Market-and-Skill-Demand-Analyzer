import pandas as pd
from pymongo import MongoClient
from pathlib import Path
import re


# ---------- MongoDB connection ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]
collection = db["bls_oews"]


# ---------- Folder containing ALL Excel files ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "bls_excel"


# ---------- Columns to keep ----------
KEEP_COLS = [
    "naics",
    "naics_title",
    "own_code",
    "occ_code",
    "occ_title",
    "tot_emp",
    "emp_prse",
    "h_mean",
    "a_mean",
    "mean_prse",
    "h_median",
    "a_median",
]


YEAR_PATTERN = re.compile(r"(20\d{2})")
BATCH_SIZE = 5_000


# ---------- Normalize columns ----------
def normalize_columns(cols):
    return (
        pd.Index(cols)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)        # spaces → _
        .str.replace(r"[^a-z0-9_]", "", regex=True)  # remove symbols
    )


# ---------- Load & insert ----------
excel_files = sorted(DATA_DIR.glob("*.xlsx"))

if not excel_files:
    raise FileNotFoundError(f"No Excel files found in: {DATA_DIR}")


for excel_file in excel_files:

    print(f"\n Processing: {excel_file.name}")


    # ---------- Extract year ----------
    m = YEAR_PATTERN.search(excel_file.name)

    if not m:
        raise ValueError(f"Year not found in filename: {excel_file.name}")

    year = int(m.group(1))


    # ---------- Read Excel ----------
    df = pd.read_excel(excel_file)


    # ---------- Normalize column names ----------
    df.columns = normalize_columns(df.columns)


    # ---------- Validate required columns ----------
    missing = [c for c in KEEP_COLS if c not in df.columns]

    if missing:
        print(" Found columns:", df.columns.tolist())
        raise ValueError(f"{excel_file.name} missing columns: {missing}")


    # ---------- Select columns + add year ----------
    df = df[KEEP_COLS].copy()
    df["year"] = year


    # ---------- NaN → None ----------
    df = df.where(pd.notnull(df), None)


    # ---------- Convert to records ----------
    records = df.to_dict("records")


    # ---------- Batch insert ----------
    total = 0

    for i in range(0, len(records), BATCH_SIZE):

        batch = records[i:i + BATCH_SIZE]

        if batch:
            collection.insert_many(batch)
            total += len(batch)


    print(f" Inserted {total:,} records from {excel_file.name}")


print("\n All Excel files inserted successfully.")

import pandas as pd
from pymongo import MongoClient, UpdateOne
from pathlib import Path
import re

# ---------- MongoDB ----------
client = MongoClient("mongodb://localhost:27017/")
db = client["jobdb"]
collection = db["bls_oews"]

# ---------- Excel folder ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "bls_excel"

YEAR_PATTERN = re.compile(r"(20\d{2})")
BATCH_SIZE = 10000

YEAR_FROM = 2011
YEAR_TO = 2024


def normalize_columns(cols):
    return (
        pd.Index(cols)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )


excel_files = sorted(DATA_DIR.glob("*.xlsx"))
if not excel_files:
    raise FileNotFoundError(f"No Excel files found in: {DATA_DIR}")

total_modified = 0
total_matched = 0

for excel_file in excel_files:
    m = YEAR_PATTERN.search(excel_file.name)
    if not m:
        print(f"⏭️ Skipping (no year): {excel_file.name}")
        continue

    year = int(m.group(1))

    #  only 2011–2024
    if year < YEAR_FROM or year > YEAR_TO:
        print(f"⏭️ Skipping year {year}: {excel_file.name}")
        continue

    print(f"\n Processing {excel_file.name} (year={year})")

    df = pd.read_excel(excel_file)
    df.columns = normalize_columns(df.columns)

    # accept o_group or group
    if "group" not in df.columns and "o_group" in df.columns:
        df = df.rename(columns={"o_group": "group"})

    if "group" not in df.columns:
        print(" Columns found:", df.columns.tolist())
        raise ValueError(f"{excel_file.name} missing 'group' or 'o_group' column")

    df = df[["naics", "occ_code", "group"]].copy()
    df["year"] = year

    # normalize values
    df["naics"] = df["naics"].astype(str).str.strip()
    df["occ_code"] = df["occ_code"].astype(str).str.strip()
    df["group"] = df["group"].astype(str).str.strip().str.lower()

    df = df[(df["naics"] != "") & (df["occ_code"] != "") & (df["group"] != "")]

    ops = []

    for _, r in df.iterrows():
        ops.append(
            UpdateOne(
                {"year": year, "naics": r["naics"], "occ_code": r["occ_code"]},
                {"$set": {"group": r["group"]}},
                upsert=False,
            )
        )

        if len(ops) >= BATCH_SIZE:
            res = collection.bulk_write(ops, ordered=False)
            total_matched += res.matched_count
            total_modified += res.modified_count
            print(f"matched: {total_matched:,} | modified: {total_modified:,}")
            ops = []

    if ops:
        res = collection.bulk_write(ops, ordered=False)
        total_matched += res.matched_count
        total_modified += res.modified_count
        print(f" matched: {total_matched:,} | modified: {total_modified:,}")

print(f"\n DONE (2011–2024). matched: {total_matched:,} | modified: {total_modified:,}")

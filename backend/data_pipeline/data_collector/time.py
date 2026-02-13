import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
CSV_FILE = BASE_DIR / "data_pipeline" / "data" / "postings.csv"

df = pd.read_csv(
    CSV_FILE,
    encoding="latin1",
    on_bad_lines="skip"
)

dates = pd.to_datetime(df["listed_time"], unit="ms", errors="coerce")

print(dates.min(), "→", dates.max())
print("Months covered:", (dates.max() - dates.min()).days // 30)

months = dates.dt.to_period("M").nunique()
print("Distinct months covered:", months)

print(
    dates
    .dt.to_period("M")
    .value_counts()
    .sort_index()
)


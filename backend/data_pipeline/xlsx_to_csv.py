import pandas as pd
from pathlib import Path
import re

# Folder where xlsx_to_csv.py is located
BASE_DIR = Path(__file__).resolve().parent

#inputFolder = BASE_DIR / "data" / "db_30_1_excel"
#outputFolder = BASE_DIR / "data" / "db_30_1_excel"

inputFolder = BASE_DIR / "data" / "Employment&Salary"
outputFolder = BASE_DIR / "data" / "Employment&Salary"

outputFolder.mkdir(parents=True, exist_ok=True)

excelFiles = list(inputFolder.glob("*.xlsx"))
print(f"Found {len(excelFiles)} Excel files in {inputFolder}")

for excelFile in excelFiles:
    try:
        sheets = pd.read_excel(excelFile, sheet_name=None, engine="openpyxl")

        for sheetName, df in sheets.items():
            safeSheetName = re.sub(r'[\\/:*?"<>|]', "_", sheetName)
            
            if safeSheetName.lower() == excelFile.stem.lower():
                csvName = excelFile.stem

            else:
                csvName = f"{excelFile.stem}_{safeSheetName}"

            csvFile = outputFolder / f"{csvName}.csv"
            df.to_csv(csvFile, index=False, encoding="utf-8")
            print(f"Converted {excelFile.name} [{sheetName}] {csvFile.name}")

    except Exception as e:
        print(f"Failed to process {excelFile.name}: {e}")

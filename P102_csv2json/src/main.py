import csv
import json
from pathlib import Path

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = ACTIVITY_DIR / "data" / "drivers.csv"
OUTPUT_FILE = ACTIVITY_DIR / "submission" / "drivers.json"
FIELDS = ["driverId", "name", "certified", "wage-plan"]


def main():
    with open(INPUT_FILE, encoding="utf-8", newline="") as f:
        records = [{field: row[field] for field in FIELDS} for row in csv.DictReader(f)]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(records, indent=4, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

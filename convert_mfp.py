#!/usr/bin/env python3
"""
Convert Samsung Health food_intake CSV → simple daily calorie CSV for the dashboard.

Input:  com.samsung.health.food_intake.*.csv  (from Samsung Health export)
Output: mfp_daily_calories.csv  (Date,Calories)

The Samsung Health CSV has per-meal rows with dates and calorie totals,
synced from MyFitnessPal. This script sums all meals per day.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime


def convert(input_path: str, output_path: str = None):
    inp = Path(input_path)
    if output_path is None:
        output_path = str(inp.parent / "mfp_daily_calories.csv")

    daily = defaultdict(float)

    with open(inp, "r", encoding="utf-8") as f:
        # Skip the first metadata line (e.g. "com.samsung.health.food_intake,6307003,6")
        first_line = f.readline()
        if not first_line.startswith("com.samsung.health"):
            f.seek(0)  # not a metadata line, rewind

        reader = csv.DictReader(f)
        for row in reader:
            try:
                date_str = row.get("start_time", "").strip()
                cal_str = row.get("calorie", "").strip()
                if not date_str or not cal_str:
                    continue
                # Parse date — format is "2021-10-30 04:00:00.000"
                dt = datetime.strptime(date_str.split(" ")[0], "%Y-%m-%d")
                cal = float(cal_str)
                daily[dt.strftime("%Y-%m-%d")] += cal
            except (ValueError, KeyError):
                continue

    # Sort by date and write
    sorted_days = sorted(daily.items())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Calories"])
        for date, cals in sorted_days:
            writer.writerow([date, round(cals)])

    print(f"✅ Wrote {len(sorted_days)} days to {output_path}")
    print(f"   Date range: {sorted_days[0][0]} → {sorted_days[-1][0]}")
    print(f"   Avg daily:  {sum(c for _, c in sorted_days) / len(sorted_days):.0f} kcal")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Auto-detect the food_intake CSV
        candidates = list(Path("/mnt/wdc/MFP/health_data").glob("com.samsung.health.food_intake.*.csv"))
        if candidates:
            convert(str(candidates[0]))
        else:
            print("Usage: python3 convert_mfp.py <food_intake.csv> [output.csv]")
            sys.exit(1)
    else:
        out = sys.argv[2] if len(sys.argv) > 2 else None
        convert(sys.argv[1], out)

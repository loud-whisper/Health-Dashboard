#!/usr/bin/env python3
"""
Parse MFP diary CSV and Samsung Health data into a merged daily health CSV.

Input:
  - /mnt/wdc/MFP/mfp_diary.csv (user-converted MFP printable diary)
  - Samsung Health CSVs in /mnt/wdc/MFP/health_data/

Output:
  - /mnt/wdc/MFP/health_data/mfp_daily_calories.csv (MFP daily aggregates)
  - /mnt/wdc/MFP/health_data/merged_health_data.csv (combined with Samsung)

Notes:
  - Steps data is EXCLUDED per user preference
  - Meditation tracked separately (Samsung misclassifies as exercise)
"""

import pandas as pd
import os
import glob
import sys

# ─── MFP Diary Parsing ───────────────────────────────────────────────

def parse_mfp_diary(csv_path):
    """Parse the user-converted mfp_diary.csv into daily nutrition totals."""
    if not os.path.exists(csv_path):
        print(f"MFP diary not found: {csv_path}")
        return pd.DataFrame()
    
    df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='warn')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    
    # Food entries (exclude Generic summary rows)
    food = df[(df['entry_type'] == 'food') & ~df['food'].str.startswith('Generic', na=False)].copy()
    for col in ['calories','carbs_g','fat_g','protein_g','sugar_g','fiber_g','sodium_mg','cholesterol_mg']:
        food[col] = pd.to_numeric(food[col], errors='coerce').fillna(0)
    
    daily_food = food.groupby('date').agg(
        MFP_Calories=('calories', 'sum'),
        Carbs_g=('carbs_g', 'sum'),
        Fat_g=('fat_g', 'sum'),
        Protein_g=('protein_g', 'sum'),
        Sugar_g=('sugar_g', 'sum'),
        Fiber_g=('fiber_g', 'sum'),
        Sodium_mg=('sodium_mg', 'sum'),
        Cholesterol_mg=('cholesterol_mg', 'sum'),
        Food_Items=('food', 'count'),
    ).reset_index()
    
    # Exercise entries (exclude Generic)
    ex = df[(df['entry_type'] == 'exercise') & ~df['food'].str.startswith('Generic', na=False)].copy()
    ex['calories'] = pd.to_numeric(ex['calories'], errors='coerce').fillna(0)
    ex['duration_min'] = pd.to_numeric(ex['duration_min'], errors='coerce').fillna(0)
    
    if not ex.empty:
        daily_ex = ex.groupby('date').agg(
            MFP_Exercise_Calories=('calories', 'sum'),
            MFP_Exercise_Minutes=('duration_min', 'sum'),
        ).reset_index()
    else:
        daily_ex = pd.DataFrame(columns=['date', 'MFP_Exercise_Calories', 'MFP_Exercise_Minutes'])
    
    daily = pd.merge(daily_food, daily_ex, on='date', how='outer').fillna(0)
    daily = daily.rename(columns={'date': 'Date'})
    daily['Date'] = daily['Date'].dt.normalize()
    return daily.sort_values('Date')


# ─── Samsung Health Parsing (using known column structure) ───────────

def parse_samsung_weight(directory):
    """
    Parse Samsung weight CSV.
    Known structure: skiprows=1, columns include 'start_time' and 'weight'.
    Leading comma may cause column shift.
    """
    files = glob.glob(os.path.join(directory, "com.samsung.health.weight.*.csv"))
    if not files:
        print("  Weight file not found.")
        return pd.DataFrame(columns=['Date', 'Weight_kg'])
    
    # Read with index_col=False to handle leading commas
    df = pd.read_csv(files[0], skiprows=1, low_memory=False, encoding='utf-8-sig', index_col=False)
    
    # If first column is unnamed/empty (from leading comma), drop it
    first_col = df.columns[0]
    if 'Unnamed' in str(first_col) or first_col == '':
        df = df.drop(columns=[first_col])
    
    if 'start_time' not in df.columns or 'weight' not in df.columns:
        print(f"  Weight: expected columns not found. Got: {df.columns.tolist()[:8]}")
        return pd.DataFrame(columns=['Date', 'Weight_kg'])
    
    df['Date'] = pd.to_datetime(df['start_time'], errors='coerce').dt.normalize()
    df['Weight_kg'] = pd.to_numeric(df['weight'], errors='coerce')
    result = df[['Date', 'Weight_kg']].dropna()
    
    # Keep last measurement per day
    result = result.groupby('Date').last().reset_index()
    return result


def parse_samsung_exercise(directory):
    """
    Parse Samsung exercise CSV. Separates real exercise from meditation.
    
    Exercise type codes (from Samsung Health data):
      0     = Auto-detected/passive activity (EXCLUDED - inflates minutes)
      1001  = Walking
      1002  = Running
      9002  = Swimming
      10007 = Rowing
      10026 = Elliptical
      11007 = Hiking
      13001 = Strength Training
      14001 = Yoga
      15002 = Guided Breathing  → MEDITATION
      15005 = Mindfulness       → MEDITATION
      15006 = Mindfulness var   → MEDITATION
    """
    MEDITATION_TYPES = {15002, 15003, 15005, 15006}
    AUTO_DETECTED = {0}  # Passive auto-detected, excluded from totals
    
    files = [f for f in glob.glob(os.path.join(directory, "com.samsung.shealth.exercise.*.csv"))
             if not any(x in f for x in ['weather','custom_exercise','hr_zone',
                'max_heart_rate','recovery_heart_rate','routine','periodization'])]
    
    if not files:
        print("  Exercise file not found.")
        empty_ex = pd.DataFrame(columns=['Date', 'Exercise_Calories', 'Exercise_Minutes'])
        empty_med = pd.DataFrame(columns=['Date', 'Meditation_Minutes'])
        return empty_ex, empty_med
    
    main_file = max(files, key=os.path.getsize)
    df = pd.read_csv(main_file, skiprows=1, low_memory=False, encoding='utf-8-sig', index_col=False)
    
    # Drop unnamed first column if present
    first_col = df.columns[0]
    if 'Unnamed' in str(first_col) or first_col == '':
        df = df.drop(columns=[first_col])
    
    # Map columns
    start_col = 'com.samsung.health.exercise.start_time'
    type_col = 'com.samsung.health.exercise.exercise_type'
    dur_col = 'com.samsung.health.exercise.duration'
    cal_col = 'com.samsung.health.exercise.calorie'
    
    if start_col not in df.columns:
        print(f"  Exercise: {start_col} not found.")
        return pd.DataFrame(columns=['Date','Exercise_Calories','Exercise_Minutes']), \
               pd.DataFrame(columns=['Date','Meditation_Minutes'])
    
    df['Date'] = pd.to_datetime(df[start_col], errors='coerce').dt.normalize()
    df = df.dropna(subset=['Date'])
    
    # Duration: ms → minutes
    if dur_col in df.columns:
        df['Duration_min'] = pd.to_numeric(df[dur_col], errors='coerce').fillna(0) / 60000
    else:
        df['Duration_min'] = 0
    
    # Calories
    if cal_col in df.columns:
        df['Cal'] = pd.to_numeric(df[cal_col], errors='coerce').fillna(0)
    else:
        df['Cal'] = 0
    
    # Classify by type
    if type_col in df.columns:
        df[type_col] = pd.to_numeric(df[type_col], errors='coerce')
    
    is_meditation = df[type_col].isin(MEDITATION_TYPES) if type_col in df.columns else pd.Series(False, index=df.index)
    is_auto = df[type_col].isin(AUTO_DETECTED) if type_col in df.columns else pd.Series(False, index=df.index)
    is_real_exercise = ~is_meditation & ~is_auto
    
    auto_count = is_auto.sum()
    print(f"    Excluded {auto_count} auto-detected entries (type 0)")
    
    # Meditation daily summary
    med_df = df[is_meditation]
    if not med_df.empty:
        daily_med = med_df.groupby('Date').agg(Meditation_Minutes=('Duration_min', 'sum')).reset_index()
    else:
        daily_med = pd.DataFrame(columns=['Date', 'Meditation_Minutes'])
    
    # Real exercise daily summary
    ex_df = df[is_real_exercise]
    if not ex_df.empty:
        daily_ex = ex_df.groupby('Date').agg(
            Exercise_Calories=('Cal', 'sum'),
            Exercise_Minutes=('Duration_min', 'sum'),
        ).reset_index()
    else:
        daily_ex = pd.DataFrame(columns=['Date', 'Exercise_Calories', 'Exercise_Minutes'])
    
    return daily_ex, daily_med


# ─── Strength Workouts ───────────────────────────────────────────────

def parse_strength_workouts(csv_path):
    """
    Parse strength_workouts.csv (from workout tracking app).
    Each row = one set: Date, Title, Exercise, Set#, Reps, Weight, Time.
    Aggregates daily: total sets, total volume (reps × weight), exercises performed.
    """
    if not os.path.exists(csv_path):
        print("  Strength file not found.")
        return pd.DataFrame(columns=['Date', 'Strength_Sets', 'Strength_Volume_lbs', 'Strength_Exercises'])
    
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()
    df = df.dropna(subset=['Date'])
    
    df['Reps'] = pd.to_numeric(df['Reps'], errors='coerce').fillna(0)
    df['Weight'] = pd.to_numeric(df['Weight'], errors='coerce').fillna(0)
    df['Volume'] = df['Reps'] * df['Weight']
    
    daily = df.groupby('Date').agg(
        Strength_Sets=('Set #', 'count'),
        Strength_Volume_lbs=('Volume', 'sum'),
        Strength_Exercises=('Exercise', 'nunique'),
    ).reset_index()
    
    return daily.sort_values('Date')


# ─── Main ────────────────────────────────────────────────────────────

def main():
    mfp_csv = "/mnt/wdc/MFP/mfp_diary.csv"
    data_dir = "/mnt/wdc/MFP/health_data/"
    mfp_output = os.path.join(data_dir, "mfp_daily_calories.csv")
    merged_output = os.path.join(data_dir, "merged_health_data.csv")
    
    # ── Parse MFP ────────────────────────────────────
    print("=" * 60)
    print("Parsing MFP Diary")
    print("=" * 60)
    mfp = parse_mfp_diary(mfp_csv)
    
    if not mfp.empty:
        print(f"  Days: {len(mfp)} | Range: {mfp['Date'].min().date()} → {mfp['Date'].max().date()}")
        print(f"  Avg cal: {mfp['MFP_Calories'].mean():.0f} | P: {mfp['Protein_g'].mean():.0f}g C: {mfp['Carbs_g'].mean():.0f}g F: {mfp['Fat_g'].mean():.0f}g")
        mfp.to_csv(mfp_output, index=False)
        print(f"  Saved → {mfp_output}")
    
    # ── Parse Samsung ────────────────────────────────
    print("\n" + "=" * 60)
    print("Parsing Samsung Health")
    print("=" * 60)
    
    weight = parse_samsung_weight(data_dir)
    print(f"  Weight: {len(weight)} measurements", end="")
    if not weight.empty:
        print(f" ({weight['Date'].min().date()} → {weight['Date'].max().date()})")
        print(f"    Latest: {weight.iloc[-1]['Weight_kg']:.1f} kg")
    else:
        print()
    
    exercise, meditation = parse_samsung_exercise(data_dir)
    print(f"  Exercise: {len(exercise)} days")
    print(f"  Meditation: {len(meditation)} days")
    
    # ── Parse Strength ───────────────────────────────
    print("\n" + "=" * 60)
    print("Parsing Strength Workouts")
    print("=" * 60)
    strength_csv = "/mnt/wdc/MFP/strength_workouts.csv"
    strength = parse_strength_workouts(strength_csv)
    if not strength.empty:
        print(f"  Days: {len(strength)} | Range: {strength['Date'].min().date()} → {strength['Date'].max().date()}")
        print(f"  Avg sets/day: {strength['Strength_Sets'].mean():.0f} | Avg volume: {strength['Strength_Volume_lbs'].mean():,.0f} lbs")
    
    # ── Merge ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Merging")
    print("=" * 60)
    
    merged = mfp.copy() if not mfp.empty else pd.DataFrame(columns=['Date'])
    for extra in [weight, exercise, meditation, strength]:
        if not extra.empty:
            merged = pd.merge(merged, extra, on='Date', how='outer')
    
    # Filter to relevant range
    merged = merged[(merged['Date'] >= '2024-12-01') & (merged['Date'] <= '2026-02-21')]
    merged = merged.sort_values('Date')
    merged = merged.fillna(0)
    
    # Summary
    print(f"  Total days: {len(merged)}")
    for col, label in [('MFP_Calories','MFP data'), ('Weight_kg','Weight'), 
                        ('Exercise_Minutes','Cardio/Exercise'), ('Meditation_Minutes','Meditation'),
                        ('Strength_Sets','Strength workouts')]:
        if col in merged.columns:
            print(f"  Days with {label}: {(merged[col] > 0).sum()}")
    
    merged.to_csv(merged_output, index=False)
    print(f"\n  Saved → {merged_output}")
    
    # Sample output
    print("\n  Last 10 days:")
    show = [c for c in ['Date','MFP_Calories','Protein_g','Strength_Sets','Strength_Volume_lbs','Exercise_Minutes','Meditation_Minutes'] if c in merged.columns]
    print(merged[show].tail(10).to_string(index=False))


if __name__ == "__main__":
    main()

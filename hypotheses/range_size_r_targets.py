import pandas as pd
from pathlib import Path
from datetime import time


# =========================
# Data Loader (TZ SAFE)
# =========================
def load_data():
    root = Path(__file__).resolve().parent.parent
    matches = list(root.rglob("nq_5m_clean.csv"))

    if not matches:
        raise FileNotFoundError("Could not find nq_5m_clean.csv.")

    path = matches[0]
    print(f"Loaded: {path}")

    df = pd.read_csv(path)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce"
    )

    df = df.dropna(subset=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df.tz_convert("America/New_York")

    return df


# =========================
# Hypothesis Test
# =========================
def run_range_r_test(df):
    buckets = {
        "<50": {"samples": 0, "1R": 0, "1.25R": 0, "1.5R": 0},
        "50-75": {"samples": 0, "1R": 0, "1.25R": 0, "1.5R": 0},
        "75-100": {"samples": 0, "1R": 0, "1.25R": 0, "1.5R": 0},
        ">100": {"samples": 0, "1R": 0, "1.25R": 0, "1.5R": 0},
    }

    df = df.copy()
    df["day"] = df.index.date

    for _, day_df in df.groupby("day"):
        day_df = day_df.between_time("09:30", "12:00")

        range_window = day_df.between_time("09:50", "10:10")
        if range_window.empty:
            continue

        range_high = range_window["high"].max()
        range_low = range_window["low"].min()
        R = range_high - range_low

        if R <= 50:
            bucket = "<50"
        elif R <= 75:
            bucket = "50-75"
        elif R <= 100:
            bucket = "75-100"
        else:
            bucket = ">100"

        after_range = day_df[day_df.index.time > time(10, 10)]
        if after_range.empty:
            continue

        breakout_time = None
        direction = None

        for idx, row in after_range.iterrows():
            if row["close"] > range_high:
                direction = "up"
                breakout_time = idx
                break
            if row["close"] < range_low:
                direction = "down"
                breakout_time = idx
                break

        if breakout_time is None:
            continue

        buckets[bucket]["samples"] += 1

        post = after_range.loc[breakout_time:]

        max_fav = 0

        for _, row in post.iterrows():
            if direction == "up":
                move = row["high"] - range_high
            else:
                move = range_low - row["low"]

            max_fav = max(max_fav, move)

        if max_fav >= R:
            buckets[bucket]["1R"] += 1
        if max_fav >= 1.25 * R:
            buckets[bucket]["1.25R"] += 1
        if max_fav >= 1.5 * R:
            buckets[bucket]["1.5R"] += 1

    return buckets


# =========================
# Output
# =========================
def print_results(buckets):
    print("\n=== Hypothesis 3: Range Size vs R Targets ===\n")

    for k, v in buckets.items():
        s = v["samples"]
        if s == 0:
            continue

        print(f"RANGE {k} POINTS")
        print(f"Samples: {s}")
        print(f"Hit 1R: {v['1R'] / s:.2%}")
        print(f"Hit 1.25R: {v['1.25R'] / s:.2%}")
        print(f"Hit 1.5R: {v['1.5R'] / s:.2%}")
        print("-" * 40)


# =========================
# Run
# =========================
if __name__ == "__main__":
    df = load_data()
    results = run_range_r_test(df)
    print_results(results)

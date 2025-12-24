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
        raise FileNotFoundError("Could not find nq_5m_clean.csv")

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
def run_midpoint_test(df):
    stats = {
        "samples": 0,
        "midpoint_first": 0,
        "boundary_first": 0,
        "neither": 0,
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
        range_size = range_high - range_low

        # Guard rail
        if range_size > 75:
            continue

        midpoint = (range_high + range_low) / 2

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

        stats["samples"] += 1

        post = after_range.loc[breakout_time:]

        midpoint_hit = False
        boundary_hit = False

        for _, row in post.iterrows():
            if direction == "up":
                if row["low"] <= midpoint:
                    midpoint_hit = True
                    break
                if row["low"] <= range_low:
                    boundary_hit = True
                    break
            else:
                if row["high"] >= midpoint:
                    midpoint_hit = True
                    break
                if row["high"] >= range_high:
                    boundary_hit = True
                    break

        if midpoint_hit:
            stats["midpoint_first"] += 1
        elif boundary_hit:
            stats["boundary_first"] += 1
        else:
            stats["neither"] += 1

    return stats


# =========================
# Output
# =========================
def print_results(stats):
    s = stats["samples"]
    print("\n=== Hypothesis: Midpoint Revisit After Acceptance ===\n")

    if s == 0:
        print("No valid samples.")
        return

    print(f"Samples: {s}")
    print(f"Midpoint Revisited First: {stats['midpoint_first'] / s:.2%}")
    print(f"Protected Boundary Hit First: {stats['boundary_first'] / s:.2%}")
    print(f"Neither by 12:00: {stats['neither'] / s:.2%}")
    print("-" * 40)


# =========================
# Run
# =========================
if __name__ == "__main__":
    df = load_data()
    stats = run_midpoint_test(df)
    print_results(stats)

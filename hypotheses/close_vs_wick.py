import pandas as pd
from pathlib import Path
from datetime import time


# =========================
# Data Loader (FIXED FOR TZ)
# =========================
def load_data():
    root = Path(__file__).resolve().parent.parent
    matches = list(root.rglob("nq_5m_clean.csv"))

    if not matches:
        raise FileNotFoundError("Could not find nq_5m_clean.csv in project.")

    path = matches[0]
    print(f"Loaded: {path}")

    df = pd.read_csv(path)

    # FORCE UTC → then convert to NY
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce"
    )

    df = df.dropna(subset=["timestamp"])
    df = df.set_index("timestamp").sort_index()

    # Convert to NY time (critical for session logic)
    df = df.tz_convert("America/New_York")

    # HARD ASSERT
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Index is not DatetimeIndex after timezone conversion.")

    return df


# =========================
# Hypothesis Test
# =========================
def run_close_vs_wick_test(df):
    results = {
        "wick": {"samples": 0, "held_11": 0, "held_12": 0},
        "close": {"samples": 0, "held_11": 0, "held_12": 0},
    }

    # Explicit day column (safe)
    df = df.copy()
    df["day"] = df.index.date

    for _, day_df in df.groupby("day"):
        day_df = day_df.between_time("09:30", "12:00")

        range_window = day_df.between_time("09:50", "10:10")
        if range_window.empty:
            continue

        range_high = range_window["high"].max()
        range_low = range_window["low"].min()

        after_range = day_df[day_df.index.time > time(10, 10)]
        if after_range.empty:
            continue

        breakout_type = None
        direction = None
        breakout_time = None

        for idx, row in after_range.iterrows():
            if row["high"] > range_high:
                direction = "up"
                breakout_type = "close" if row["close"] > range_high else "wick"
                breakout_time = idx
                break

            if row["low"] < range_low:
                direction = "down"
                breakout_type = "close" if row["close"] < range_low else "wick"
                breakout_time = idx
                break

        if breakout_time is None:
            continue

        results[breakout_type]["samples"] += 1

        post = after_range.loc[breakout_time:]

        held_11 = True
        held_12 = True

        for idx, row in post.iterrows():
            if idx.time() <= time(11, 0):
                if direction == "up" and row["low"] <= range_low:
                    held_11 = False
                if direction == "down" and row["high"] >= range_high:
                    held_11 = False

            if idx.time() <= time(12, 0):
                if direction == "up" and row["low"] <= range_low:
                    held_12 = False
                if direction == "down" and row["high"] >= range_high:
                    held_12 = False

        if held_11:
            results[breakout_type]["held_11"] += 1
        if held_12:
            results[breakout_type]["held_12"] += 1

    return results


# =========================
# Output
# =========================
def print_results(results):
    print("\n=== Hypothesis 2: Close vs Wick ===\n")

    for k in ["wick", "close"]:
        s = results[k]["samples"]
        if s == 0:
            print(f"{k.upper()} BREAKOUTS: No samples\n")
            continue

        print(f"{k.upper()} BREAKOUTS")
        print(f"Samples: {s}")
        print(f"Held Opposite Side until 11:00: {results[k]['held_11'] / s:.2%}")
        print(f"Held Opposite Side until 12:00: {results[k]['held_12'] / s:.2%}")
        print("-" * 40)


# =========================
# Run
# =========================
if __name__ == "__main__":
    df = load_data()
    results = run_close_vs_wick_test(df)
    print_results(results)

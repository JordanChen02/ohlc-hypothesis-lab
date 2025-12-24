import pandas as pd
from pathlib import Path
from datetime import time


def load_data():
    root = Path(__file__).resolve().parent.parent
    matches = list(root.rglob("nq_5m_clean.csv"))
    if not matches:
        raise FileNotFoundError("Could not find nq_5m_clean.csv")

    path = matches[0]
    print(f"Loaded: {path}")

    df = pd.read_csv(path)

    # Force UTC then convert to NY for session slicing
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df.tz_convert("America/New_York")

    return df


def run_next_candle_breach_test(df):
    out = {
        "up": {"samples": 0, "next_breached": 0, "next_held": 0},
        "down": {"samples": 0, "next_breached": 0, "next_held": 0},
        "meta": {"no_breakout": 0, "no_next_candle": 0},
    }

    df = df.copy()
    df["day"] = df.index.date

    for _, day_df in df.groupby("day"):
        day_df = day_df.between_time("09:30", "12:00")

        rw = day_df.between_time("09:50", "10:10")
        if rw.empty:
            continue

        r_high = rw["high"].max()
        r_low = rw["low"].min()

        after = day_df[day_df.index.time > time(10, 10)]
        if after.empty:
            continue

        breakout_idx = None
        direction = None

        # close-confirmed breakout only
        for idx, row in after.iterrows():
            if row["close"] > r_high:
                breakout_idx = idx
                direction = "up"
                break
            if row["close"] < r_low:
                breakout_idx = idx
                direction = "down"
                break

        if breakout_idx is None:
            out["meta"]["no_breakout"] += 1
            continue

        # Need the NEXT 5m candle
        after_idx = after.index
        pos = after_idx.get_loc(breakout_idx)
        if isinstance(pos, slice) or pos >= len(after_idx) - 1:
            out["meta"]["no_next_candle"] += 1
            continue

        next_idx = after_idx[pos + 1]

        br = after.loc[breakout_idx]
        nx = after.loc[next_idx]

        if direction == "up":
            out["up"]["samples"] += 1
            breached = nx["low"] <= br["low"]          # took out breakout low
            if breached:
                out["up"]["next_breached"] += 1
            else:
                out["up"]["next_held"] += 1

        else:
            out["down"]["samples"] += 1
            breached = nx["high"] >= br["high"]        # took out breakout high
            if breached:
                out["down"]["next_breached"] += 1
            else:
                out["down"]["next_held"] += 1

    return out


def print_results(out):
    print("\n=== Hypothesis: Next Candle Breach After Close-Confirmed Breakout ===\n")

    for side in ["up", "down"]:
        s = out[side]["samples"]
        if s == 0:
            print(f"{side.upper()} breakouts: no samples\n")
            continue

        p_breach = out[side]["next_breached"] / s
        p_hold = out[side]["next_held"] / s

        print(f"{side.upper()} BREAKOUTS")
        print(f"Samples: {s}")
        print(f"Next candle BREACHES breakout candle {'low' if side=='up' else 'high'}: {p_breach:.2%}")
        print(f"Next candle DOES NOT breach (acceptance): {p_hold:.2%}")
        print("-" * 40)

    print("DEBUG")
    print(f"No breakout days: {out['meta']['no_breakout']}")
    print(f"No next candle available: {out['meta']['no_next_candle']}")
    print("-" * 40)


if __name__ == "__main__":
    df = load_data()
    out = run_next_candle_breach_test(df)
    print_results(out)

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
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df.tz_convert("America/New_York")
    return df


def run_stairstep_acceptance(df, steps=4):
    # Conditional step stats:
    # denom[n] = count of breakouts where steps 1..(n-1) held AND candle n exists
    # numer[n] = of those, step n held
    out = {
        "up": {"denom": [0] * (steps + 1), "numer": [0] * (steps + 1)},
        "down": {"denom": [0] * (steps + 1), "numer": [0] * (steps + 1)},
        "meta": {"no_breakout": 0, "insufficient_bars": 0},
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

        # close-confirmed breakout candle = candle 0
        b0_idx = None
        direction = None

        for idx, row in after.iterrows():
            if row["close"] > r_high:
                b0_idx = idx
                direction = "up"
                break
            if row["close"] < r_low:
                b0_idx = idx
                direction = "down"
                break

        if b0_idx is None:
            out["meta"]["no_breakout"] += 1
            continue

        idxs = after.index
        pos0 = idxs.get_loc(b0_idx)
        if isinstance(pos0, slice):
            pos0 = pos0.start

        # Need candle 1..steps
        if pos0 + steps >= len(idxs):
            out["meta"]["insufficient_bars"] += 1
            # Still can contribute to earlier steps if some bars exist:
            # We'll handle per-step existence below.
        # Build candle list [c0, c1, ..., c_steps] where available
        candles = []
        for k in range(0, steps + 1):
            p = pos0 + k
            if p < len(idxs):
                candles.append(after.loc[idxs[p]])
            else:
                candles.append(None)

        # Evaluate steps sequentially with conditional denominators
        held_all_prior = True
        for n in range(1, steps + 1):
            if not held_all_prior:
                break  # conditional chain breaks

            c_prev = candles[n - 1]
            c_cur = candles[n]

            if c_cur is None:
                break  # no candle n, can't evaluate further

            out[direction]["denom"][n] += 1

            if direction == "up":
                step_holds = c_cur["low"] > c_prev["low"]
            else:
                step_holds = c_cur["high"] < c_prev["high"]

            if step_holds:
                out[direction]["numer"][n] += 1
            else:
                held_all_prior = False

    return out


def print_results(out, steps=4):
    print("\n=== Stairstep Acceptance Test (Conditional) ===")
    print("Candle 0 = close-confirmed breakout candle")
    print("UP: step holds if candle[n].low  > candle[n-1].low")
    print("DOWN: step holds if candle[n].high < candle[n-1].high")
    print("-" * 48)

    for side in ["up", "down"]:
        print(f"\n{side.upper()} BREAKOUTS")
        for n in range(1, steps + 1):
            d = out[side]["denom"][n]
            if d == 0:
                print(f"Step {n}: no samples")
                continue
            p = out[side]["numer"][n] / d
            print(f"Step {n} (c{n} vs c{n-1}) holds: {p:.2%}   (samples={d})")

    print("\nDEBUG")
    print(f"No breakout days: {out['meta']['no_breakout']}")
    print(f"Days with insufficient bars for full chain: {out['meta']['insufficient_bars']}")
    print("-" * 48)


if __name__ == "__main__":
    df = load_data()
    steps = 4
    out = run_stairstep_acceptance(df, steps=steps)
    print_results(out, steps=steps)

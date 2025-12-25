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


def run_stairstep(df, steps=4):
    """
    TRUE STAIRSTEP (CUMULATIVE ONLY)

    Candle 0 = close-confirmed breakout candle

    UP:
      Step n holds if candle[n].low  > candle[n-1].low

    DOWN:
      Step n holds if candle[n].high < candle[n-1].high

    Once a step fails, the chain is DEAD.
    """

    out = {
        "up": {"base": 0, "survivors": [0] * (steps + 1)},
        "down": {"base": 0, "survivors": [0] * (steps + 1)},
        "meta": {"no_breakout": 0},
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

        # Find close-confirmed breakout (candle 0)
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

        # Need at least candle 1 to evaluate stairstep at all
        if pos0 + 1 >= len(idxs):
            continue

        # Build candles c0..cN
        candles = []
        for k in range(0, steps + 1):
            p = pos0 + k
            candles.append(after.loc[idxs[p]] if p < len(idxs) else None)

        out[direction]["base"] += 1

        chain_alive = True
        for n in range(1, steps + 1):
            if not chain_alive:
                break
            if candles[n] is None:
                break

            c_prev = candles[n - 1]
            c_cur = candles[n]

            if direction == "up":
                holds = c_cur["low"] > c_prev["low"]
            else:
                holds = c_cur["high"] < c_prev["high"]

            if holds:
                out[direction]["survivors"][n] += 1
            else:
                chain_alive = False

    return out


def print_results(out, steps=4):
    print("\n=== STAIRSTEP ACCEPTANCE (CUMULATIVE SURVIVAL) ===")
    print("Candle 0 = close-confirmed breakout candle")
    print("Once a step fails, the stairstep is DEAD.")
    print("-" * 52)

    for side in ["up", "down"]:
        base = out[side]["base"]
        print(f"\n{side.upper()} BREAKOUTS")
        print(f"Base samples: {base}")

        if base == 0:
            continue

        for n in range(1, steps + 1):
            surv = out[side]["survivors"][n]
            p = surv / base
            print(f"Survives through Step {n}: {p:.2%}")

    print("\nDEBUG")
    print(f"No breakout days: {out['meta']['no_breakout']}")
    print("-" * 52)


if __name__ == "__main__":
    df = load_data()
    steps = 4
    out = run_stairstep(df, steps=steps)
    print_results(out, steps=steps)

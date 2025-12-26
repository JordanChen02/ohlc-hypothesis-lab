import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# CONFIG (matches your 10AM logic)
# ============================================================
DATA_5M = Path("data/processed/nq_5m_clean.csv")

SESSION_START = "09:30"
SESSION_END   = "12:00"
RANGE_START   = "09:50"
RANGE_END     = "10:10"

R_TARGETS = [1.0, 1.5, 2.0]   # report win/pf/exp for each


# ============================================================
# LOAD
# ============================================================
def load_5m() -> pd.DataFrame:
    if not DATA_5M.exists():
        raise FileNotFoundError(f"Missing file: {DATA_5M.resolve()}")

    df = pd.read_csv(DATA_5M)

    if "timestamp" not in df.columns:
        raise ValueError("Expected a 'timestamp' column in nq_5m_clean.csv")

    # Fix mixed timezone warning + guarantee tz-aware index
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Index is not a DatetimeIndex after parsing timestamp.")

    # Work in NY time for your session windows
    df = df.tz_convert("America/New_York")

    needed = {"open", "high", "low", "close"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print(f"Loaded 5m: {DATA_5M.resolve()}")
    return df


# ============================================================
# STRATEGY: 50% retrace entry, stop at breakout extreme
# R is defined by entry->stop (i.e., half the breakout candle risk)
# ============================================================
def run_strategy(df: pd.DataFrame):
    results = {rt: [] for rt in R_TARGETS}

    debug = {
        "days_total": 0,
        "no_range": 0,
        "no_breakout": 0,
        "no_entry_fill": 0,
        "ambiguous_stop_tp_same_bar": {rt: 0 for rt in R_TARGETS},
        "trades": 0,
    }

    # Group by trading day robustly
    for _, day in df.groupby(df.index.normalize()):
        debug["days_total"] += 1

        day = day.between_time(SESSION_START, SESSION_END)
        if day.empty:
            debug["no_range"] += 1
            continue

        rng = day.between_time(RANGE_START, RANGE_END)
        if rng.empty:
            debug["no_range"] += 1
            continue

        range_high = float(rng["high"].max())
        range_low  = float(rng["low"].min())

        after = day[day.index > rng.index[-1]]
        if after.empty:
            debug["no_breakout"] += 1
            continue

        # Find first close-confirmed breakout candle (c0)
        c0 = None
        direction = None  # "long" or "short"
        ts0 = None

        for ts, row in after.iterrows():
            if row["close"] > range_high:
                c0 = row
                ts0 = ts
                direction = "long"
                break
            if row["close"] < range_low:
                c0 = row
                ts0 = ts
                direction = "short"
                break

        if c0 is None:
            debug["no_breakout"] += 1
            continue

        # Forward bars AFTER breakout candle close
        fwd = after[after.index > ts0]
        if fwd.empty:
            debug["no_entry_fill"] += 1
            continue

        # 50% retrace entry and stop at breakout extreme
        if direction == "long":
            full = float(c0["close"] - c0["low"])
            if full <= 0:
                debug["no_entry_fill"] += 1
                continue
            entry = float(c0["close"] - 0.5 * full)
            stop  = float(c0["low"])
        else:
            full = float(c0["high"] - c0["close"])
            if full <= 0:
                debug["no_entry_fill"] += 1
                continue
            entry = float(c0["close"] + 0.5 * full)
            stop  = float(c0["high"])

        # True risk after limit entry
        risk = abs(entry - stop)
        if risk <= 0:
            debug["no_entry_fill"] += 1
            continue

        # Wait for entry fill
        entry_ts = None
        for ts, bar in fwd.iterrows():
            if direction == "long" and float(bar["low"]) <= entry:
                entry_ts = ts
                break
            if direction == "short" and float(bar["high"]) >= entry:
                entry_ts = ts
                break

        if entry_ts is None:
            debug["no_entry_fill"] += 1
            continue

        # From entry forward, resolve each target independently
        # Conservative ambiguity: if stop & TP in same bar -> count as stop
        for rt in R_TARGETS:
            tp = entry + rt * risk if direction == "long" else entry - rt * risk
            outcome = 0.0  # unresolved if neither hit by session end

            for _, bar in fwd.loc[entry_ts:].iterrows():
                hi = float(bar["high"])
                lo = float(bar["low"])

                if direction == "long":
                    hit_stop = lo <= stop
                    hit_tp   = hi >= tp
                else:
                    hit_stop = hi >= stop
                    hit_tp   = lo <= tp

                if hit_stop and hit_tp:
                    debug["ambiguous_stop_tp_same_bar"][rt] += 1
                    outcome = -1.0
                    break
                if hit_stop:
                    outcome = -1.0
                    break
                if hit_tp:
                    outcome = float(rt)
                    break

            results[rt].append(outcome)

        debug["trades"] += 1

    return results, debug


# ============================================================
# METRICS
# ============================================================
def summarize(results, debug):
    print("\n=== STRATEGY: 10AM Breakout → 50% Retrace Entry → Stop @ Breakout Extreme ===")
    print("R is based on (entry → stop). Targets: 1R / 1.5R / 2R\n")

    for rt in R_TARGETS:
        arr = np.array(results[rt], dtype=float)
        n = len(arr)
        wins = int((arr > 0).sum())
        losses = int((arr < 0).sum())
        unresolved = int((arr == 0).sum())

        resolved = wins + losses
        wr_resolved = (wins / resolved) if resolved else 0.0

        gross_win = arr[arr > 0].sum()
        gross_loss = abs(arr[arr < 0].sum())
        pf = (gross_win / gross_loss) if gross_loss > 0 else np.nan

        exp = arr.mean() if n else 0.0

        print(f"Target {rt:.2f}R")
        print(f"Trades: {n} | Wins: {wins} | Losses: {losses} | Unresolved: {unresolved}")
        print(f"Resolved WR: {wr_resolved:.2%}")
        print(f"Profit factor: {pf:.3f}")
        print(f"Expectancy: {exp:+.3f}R")
        print(f"Ambiguous (stop & TP same bar, stop assumed): {debug['ambiguous_stop_tp_same_bar'][rt]}\n")

    print("--- DEBUG ---")
    for k, v in debug.items():
        if k == "ambiguous_stop_tp_same_bar":
            continue
        print(f"{k}: {v}")


def main():
    df = load_5m()
    results, debug = run_strategy(df)
    summarize(results, debug)


if __name__ == "__main__":
    main()


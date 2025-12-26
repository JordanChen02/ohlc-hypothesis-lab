import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# CONFIG
# =========================
DATA_REL = Path("data/processed/nq_5m_clean.csv")  # your working path
SESSION_START = "09:30"
SESSION_END   = "12:00"
RANGE_START   = "09:50"
RANGE_END     = "10:10"

RETRACE_LEVELS = [0.50, 0.75]   # test -0.5R and -0.75R
TARGET_R = 1.00                # compare vs +1R
AMBIGUOUS_RULE = "retrace_first"  # or "target_first"


# =========================
# LOADING
# =========================
def load_data() -> pd.DataFrame:
    # robust path find (works even if you move repo)
    if DATA_REL.exists():
        path = DATA_REL
    else:
        root = Path(__file__).resolve().parent.parent
        hits = list(root.rglob("nq_5m_clean.csv"))
        if not hits:
            raise FileNotFoundError("Could not find nq_5m_clean.csv (expected in data/processed/)")
        path = hits[0]

    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError("Expected a 'timestamp' column")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
    df = df.tz_convert("America/New_York")

    need = {"open", "high", "low", "close"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    print(f"Loaded: {path}")
    return df


# =========================
# CORE TEST
# =========================
def first_hit_up(bar, retrace_px, target_px):
    """
    For UP direction: retrace hit if low <= retrace_px, target hit if high >= target_px
    Returns: "retrace", "target", "both", or None
    """
    hit_r = bar["low"] <= retrace_px
    hit_t = bar["high"] >= target_px
    if hit_r and hit_t:
        return "both"
    if hit_r:
        return "retrace"
    if hit_t:
        return "target"
    return None


def first_hit_down(bar, retrace_px, target_px):
    """
    For DOWN direction:
    - retrace is upward retrace (adverse move) to entry + retrace_frac*R => high >= retrace_px
    - target is favorable move to entry - 1R => low <= target_px
    """
    hit_r = bar["high"] >= retrace_px
    hit_t = bar["low"] <= target_px
    if hit_r and hit_t:
        return "both"
    if hit_r:
        return "retrace"
    if hit_t:
        return "target"
    return None


def run_test(df: pd.DataFrame):
    out = {
        "up": {f: {"n": 0, "retrace_first": 0, "target_first": 0, "neither": 0, "ambiguous": 0} for f in RETRACE_LEVELS},
        "down": {f: {"n": 0, "retrace_first": 0, "target_first": 0, "neither": 0, "ambiguous": 0} for f in RETRACE_LEVELS},
        "debug": {"days_total": 0, "no_range": 0, "no_breakout": 0, "no_forward": 0, "bad_risk": 0},
    }

    for _, day in df.groupby(df.index.date):
        out["debug"]["days_total"] += 1

        day = day.between_time(SESSION_START, SESSION_END)
        if day.empty:
            out["debug"]["no_range"] += 1
            continue

        rng = day.between_time(RANGE_START, RANGE_END)
        if rng.empty:
            out["debug"]["no_range"] += 1
            continue

        range_high = float(rng["high"].max())
        range_low  = float(rng["low"].min())

        after = day[day.index > rng.index[-1]]
        if after.empty:
            out["debug"]["no_breakout"] += 1
            continue

        # Close-confirmed breakout candle (c0)
        c0 = None
        direction = None
        for ts, row in after.iterrows():
            if row["close"] > range_high:
                c0 = row
                direction = "up"
                break
            if row["close"] < range_low:
                c0 = row
                direction = "down"
                break

        if c0 is None:
            out["debug"]["no_breakout"] += 1
            continue

        ts0 = c0.name
        forward = after[after.index > ts0]
        if forward.empty:
            out["debug"]["no_forward"] += 1
            continue

        entry = float(c0["close"])

        if direction == "up":
            stop = float(c0["low"])
            R = entry - stop
            if R <= 0:
                out["debug"]["bad_risk"] += 1
                continue

            target = entry + TARGET_R * R

            for frac in RETRACE_LEVELS:
                retrace = entry - frac * R
                out["up"][frac]["n"] += 1

                decided = False
                for _, bar in forward.iterrows():
                    hit = first_hit_up(bar, retrace, target)
                    if hit is None:
                        continue

                    if hit == "both":
                        out["up"][frac]["ambiguous"] += 1
                        out["up"][frac][AMBIGUOUS_RULE] += 1
                    elif hit == "retrace":
                        out["up"][frac]["retrace_first"] += 1
                    else:
                        out["up"][frac]["target_first"] += 1

                    decided = True
                    break

                if not decided:
                    out["up"][frac]["neither"] += 1

        else:
            stop = float(c0["high"])
            R = stop - entry
            if R <= 0:
                out["debug"]["bad_risk"] += 1
                continue

            target = entry - TARGET_R * R

            for frac in RETRACE_LEVELS:
                retrace = entry + frac * R  # adverse move upward
                out["down"][frac]["n"] += 1

                decided = False
                for _, bar in forward.iterrows():
                    hit = first_hit_down(bar, retrace, target)
                    if hit is None:
                        continue

                    if hit == "both":
                        out["down"][frac]["ambiguous"] += 1
                        out["down"][frac][AMBIGUOUS_RULE] += 1
                    elif hit == "retrace":
                        out["down"][frac]["retrace_first"] += 1
                    else:
                        out["down"][frac]["target_first"] += 1

                    decided = True
                    break

                if not decided:
                    out["down"][frac]["neither"] += 1

    return out


def pct(x, n):
    return 0.0 if n == 0 else 100.0 * x / n


def print_results(res):
    print("\n=== Hypothesis: Retrace X% of breakout risk BEFORE +1R (close-confirmed breakouts) ===")
    print(f"Compare: retrace (adverse) vs target (+{TARGET_R:.2f}R)")
    print(f"Ambiguous bar rule: {AMBIGUOUS_RULE}\n")

    for side in ["up", "down"]:
        label = "UP BREAKOUTS" if side == "up" else "DOWN BREAKOUTS"
        print(label)

        for frac in RETRACE_LEVELS:
            d = res[side][frac]
            n = d["n"]
            print(f"  Retrace {int(frac*100)}% BEFORE +1R:")
            print(f"    Samples: {n}")
            print(f"    Retrace-first: {pct(d['retrace_first'], n):.2f}%")
            print(f"    Target-first:  {pct(d['target_first'], n):.2f}%")
            print(f"    Neither by 12:00: {pct(d['neither'], n):.2f}%")
            print(f"    Ambiguous (both same candle): {d['ambiguous']}")

        print("-" * 44)

    print("\nDEBUG")
    for k, v in res["debug"].items():
        print(f"  {k}: {v}")


def main():
    df = load_data()
    res = run_test(df)
    print_results(res)


if __name__ == "__main__":
    main()

import pandas as pd

NY_TZ = "America/New_York"

# -----------------------------------
# CONFIG
# -----------------------------------
RANGE_START = "09:50"
RANGE_END   = "10:10"

CUTOFF_1 = "11:00"
CUTOFF_2 = "12:00"


def run_am_macro_range(df):
    """
    Hypothesis:
    The 9:50–10:10 window forms a macro range.
    After 10:10, whichever side breaks first,
    the opposite side is unlikely to be revisited
    until 11:00 or 12:00.
    """

    df = df.copy()
    df["date"] = df.index.date

    stats = {
        "break_high_first": {"samples": 0, "held_11": 0, "held_12": 0},
        "break_low_first":  {"samples": 0, "held_11": 0, "held_12": 0},
    }

    no_range = 0
    no_break = 0
    ambiguous = 0

    for d, day in df.groupby("date"):
        day = day.sort_index()

        # -----------------------------
        # Define macro range (9:50–10:10)
        # -----------------------------
        macro = day.between_time(RANGE_START, RANGE_END, inclusive="left")

        if macro.empty:
            no_range += 1
            continue

        range_high = float(macro["high"].max())
        range_low  = float(macro["low"].min())

        # -----------------------------
        # Look for first break AFTER 10:10
        # -----------------------------
        post = day[day.index > macro.index[-1]]

        first_side = None
        first_ts = None

        for ts, row in post.iterrows():
            hit_high = row["high"] > range_high
            hit_low  = row["low"] < range_low

            if hit_high and hit_low:
                ambiguous += 1
                first_side = "ambiguous"
                break

            if hit_high:
                first_side = "break_high_first"
                first_ts = ts
                break

            if hit_low:
                first_side = "break_low_first"
                first_ts = ts
                break

        if first_side is None:
            no_break += 1
            continue

        if first_side == "ambiguous":
            continue

        stats[first_side]["samples"] += 1

        # -----------------------------
        # Evaluate opposite-side revisit
        # -----------------------------
        rem_11 = day.loc[first_ts:].between_time(RANGE_END, CUTOFF_1, inclusive="left")
        rem_12 = day.loc[first_ts:].between_time(RANGE_END, CUTOFF_2, inclusive="left")

        if first_side == "break_high_first":
            # Opposite side = range LOW
            if not (rem_11["low"] <= range_low).any():
                stats["break_high_first"]["held_11"] += 1
            if not (rem_12["low"] <= range_low).any():
                stats["break_high_first"]["held_12"] += 1

        if first_side == "break_low_first":
            # Opposite side = range HIGH
            if not (rem_11["high"] >= range_high).any():
                stats["break_low_first"]["held_11"] += 1
            if not (rem_12["high"] >= range_high).any():
                stats["break_low_first"]["held_12"] += 1

    def pct(x, n):
        return round(x / n, 4) if n > 0 else float("nan")

    return {
        "meta": {
            "range_window": f"{RANGE_START}–{RANGE_END}",
            "evaluation_cutoffs": ["11:00", "12:00"],
        },
        "break_high_first": {
            "samples": stats["break_high_first"]["samples"],
            "held_11": pct(
                stats["break_high_first"]["held_11"],
                stats["break_high_first"]["samples"],
            ),
            "held_12": pct(
                stats["break_high_first"]["held_12"],
                stats["break_high_first"]["samples"],
            ),
        },
        "break_low_first": {
            "samples": stats["break_low_first"]["samples"],
            "held_11": pct(
                stats["break_low_first"]["held_11"],
                stats["break_low_first"]["samples"],
            ),
            "held_12": pct(
                stats["break_low_first"]["held_12"],
                stats["break_low_first"]["samples"],
            ),
        },
        "debug": {
            "no_range": no_range,
            "no_break": no_break,
            "ambiguous": ambiguous,
        },
    }

if __name__ == "__main__":
    # Temporary terminal output for inspection
    import sys
    from pathlib import Path

    # Add project root to Python path
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(ROOT))

    from hypotheses.ten_am_reversal import load_5m

    df = load_5m()
    out = run_am_macro_range(df)

    print("\n=== AM MACRO RANGE TEST ===\n")

    for side in ["break_high_first", "break_low_first"]:
        label = (
            "Break ABOVE 9:50–10:10 range first"
            if side == "break_high_first"
            else "Break BELOW 9:50–10:10 range first"
        )

        s = out[side]
        n = s["samples"]

        print(f"=== {label} ===")
        print("Samples:", n)
        print("Held until 11:00:", s["held_11"])
        print("Held until 12:00:", s["held_12"])
        print()

    print("=== DEBUG ===")
    for k, v in out["debug"].items():
        print(f"{k}: {v}")

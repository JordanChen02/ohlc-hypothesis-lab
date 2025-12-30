
from pathlib import Path
import pandas as pd


THIS_SHOULD_CRASH = (

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "nq_5m_clean.csv"

NY_TZ = "America/New_York"

# Prior range (what can be reversed)
PRIOR_START = "09:30"
PRIOR_END   = "09:50"

# Reversal decision window
EVENT_START = "09:50"
EVENT_END   = "10:10"

# Cutoffs
CUTOFF_1 = "11:00"
CUTOFF_2 = "12:00"
DAY_END  = "16:00"


def load_5m():
    import os

    return {
        "cwd": os.getcwd(),
        "file_location": str(Path(__file__).resolve()),
        "root": str(ROOT),
        "data_path": str(DATA),
        "data_exists": DATA.exists(),
        "root_contents": os.listdir(ROOT),
        "data_contents": os.listdir(ROOT / "data") if (ROOT / "data").exists() else "NO DATA DIR",
        "processed_contents": os.listdir(ROOT / "data" / "processed")
            if (ROOT / "data" / "processed").exists()
            else "NO PROCESSED DIR",
    }


def win(df_day, start, end):
    return df_day.between_time(start, end, inclusive="left")


def run_10am_reversal(df):
    df = df.copy()
    df["date"] = df.index.date

    stats = {
        "reversal_at_high": {"samples": 0, "held_11": 0, "held_12": 0},
        "reversal_at_low":  {"samples": 0, "held_11": 0, "held_12": 0},
    }

    no_prior = 0
    no_event = 0
    no_hit_in_event = 0
    ambiguous = 0

    for d, day in df.groupby("date"):
        day = day.sort_index()

        prior = win(day, PRIOR_START, PRIOR_END)
        event = win(day, EVENT_START, EVENT_END)

        if prior.empty:
            no_prior += 1
            continue
        if event.empty:
            no_event += 1
            continue

        prior_high = float(prior["high"].max())
        prior_low  = float(prior["low"].min())

        first_side = None
        first_ts = None

        for ts, row in event.iterrows():
            hit_high = row["high"] >= prior_high
            hit_low  = row["low"] <= prior_low

            if hit_high and hit_low:
                ambiguous += 1
                first_side = "ambiguous"
                break
            if hit_high:
                first_side = "reversal_at_high"
                first_ts = ts
                break
            if hit_low:
                first_side = "reversal_at_low"
                first_ts = ts
                break

        if first_side is None:
            no_hit_in_event += 1
            continue
        if first_side == "ambiguous":
            continue

        stats[first_side]["samples"] += 1

        rem_11 = win(day.loc[first_ts:], EVENT_START, CUTOFF_1)
        rem_12 = win(day.loc[first_ts:], EVENT_START, CUTOFF_2)

        if first_side == "reversal_at_high":
            if not (rem_11["low"] <= prior_low).any():
                stats["reversal_at_high"]["held_11"] += 1
            if not (rem_12["low"] <= prior_low).any():
                stats["reversal_at_high"]["held_12"] += 1

        if first_side == "reversal_at_low":
            if not (rem_11["high"] >= prior_high).any():
                stats["reversal_at_low"]["held_11"] += 1
            if not (rem_12["high"] >= prior_high).any():
                stats["reversal_at_low"]["held_12"] += 1

    def pct(x, n):
        return round(x / n, 4) if n > 0 else float("nan")

    return {
        "meta": {
            "prior_range": f"{PRIOR_START}–{PRIOR_END}",
            "event_window": f"{EVENT_START}–{EVENT_END}",
        },
        "reversal_at_high": {
            "samples": stats["reversal_at_high"]["samples"],
            "held_11": pct(
                stats["reversal_at_high"]["held_11"],
                stats["reversal_at_high"]["samples"],
            ),
            "held_12": pct(
                stats["reversal_at_high"]["held_12"],
                stats["reversal_at_high"]["samples"],
            ),
        },
        "reversal_at_low": {
            "samples": stats["reversal_at_low"]["samples"],
            "held_11": pct(
                stats["reversal_at_low"]["held_11"],
                stats["reversal_at_low"]["samples"],
            ),
            "held_12": pct(
                stats["reversal_at_low"]["held_12"],
                stats["reversal_at_low"]["samples"],
            ),
        },
        "debug": {
            "no_prior": no_prior,
            "no_event": no_event,
            "no_hit_in_event": no_hit_in_event,
            "ambiguous": ambiguous,
        },
    }


if __name__ == "__main__":
    df = load_5m()
    out = run_10am_reversal(df)
    print(out)

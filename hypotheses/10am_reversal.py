from pathlib import Path
import pandas as pd

DATA = Path("data/processed/nq_5m_clean.csv")
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
    df = pd.read_csv(DATA)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(NY_TZ)
    df = df.set_index("timestamp").sort_index()
    return df[["open", "high", "low", "close"]].dropna()


def win(df_day, start, end):
    return df_day.between_time(start, end, inclusive="left")


def main():
    df = load_5m()
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

        # Find first hit of prior range during 9:50–10:10
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
            # Opposite side = prior LOW
            if not (rem_11["low"] <= prior_low).any():
                stats["reversal_at_high"]["held_11"] += 1
            if not (rem_12["low"] <= prior_low).any():
                stats["reversal_at_high"]["held_12"] += 1

        if first_side == "reversal_at_low":
            # Opposite side = prior HIGH
            if not (rem_11["high"] >= prior_high).any():
                stats["reversal_at_low"]["held_11"] += 1
            if not (rem_12["high"] >= prior_high).any():
                stats["reversal_at_low"]["held_12"] += 1

    def pct(x, n):
        return round(x / n, 4) if n > 0 else float("nan")

    print("\n=== 10AM REVERSAL TEST ===")
    print(f"Prior range: {PRIOR_START}–{PRIOR_END}")
    print(f"Reversal window: {EVENT_START}–{EVENT_END}\n")

    for side in ["reversal_at_high", "reversal_at_low"]:
        label = (
            "Reversal at HIGH (prior high hit in 9:50–10:10)"
            if side == "reversal_at_high"
            else "Reversal at LOW (prior low hit in 9:50–10:10)"
        )
        s = stats[side]
        n = s["samples"]

        print(f"=== {label} ===")
        print("Samples:", n)
        print("Held until 11:00:", pct(s["held_11"], n))
        print("Held until 12:00:", pct(s["held_12"], n))
        print()

    print("=== CONCLUSION (Plain English) ===")

    hi = stats["reversal_at_high"]
    lo = stats["reversal_at_low"]

    if hi["samples"] > 0:
        print(
            f"When a reversal at the HIGH occurs between 9:50–10:10, "
            f"price holds without revisiting the prior LOW until 11:00 "
            f"{pct(hi['held_11'], hi['samples'])*100:.2f}% of the time "
            f"and until 12:00 {pct(hi['held_12'], hi['samples'])*100:.2f}% of the time."
        )

    if lo["samples"] > 0:
        print(
            f"When a reversal at the LOW occurs between 9:50–10:10, "
            f"price holds without revisiting the prior HIGH until 11:00 "
            f"{pct(lo['held_11'], lo['samples'])*100:.2f}% of the time "
            f"and until 12:00 {pct(lo['held_12'], lo['samples'])*100:.2f}% of the time."
        )

    print("\n=== DEBUG ===")
    print("No prior window:", no_prior)
    print("No event window:", no_event)
    print("No hit in event window:", no_hit_in_event)
    print("Ambiguous hits:", ambiguous)


if __name__ == "__main__":
    main()

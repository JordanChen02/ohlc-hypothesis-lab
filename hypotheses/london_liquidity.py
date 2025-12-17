from pathlib import Path
import pandas as pd

DATA = Path("data/processed/nq_5m_clean.csv")
NY_TZ = "America/New_York"

LONDON_START = "02:00"
LONDON_END   = "05:00"

POST_START   = "05:00"
NY_AM_END    = "11:00"
LUNCH_END    = "13:30"
NY_END       = "16:00"


def load_5m():
    df = pd.read_csv(DATA)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(NY_TZ)
    df = df.set_index("timestamp").sort_index()
    return df[["open", "high", "low", "close"]].dropna()


def get_session(df_day, start, end):
    return df_day.between_time(start, end, inclusive="left")


def main():
    df = load_5m()
    df["date"] = df.index.date

    results = {
        "high_first": {
            "samples": 0,
            "am": 0,
            "lunch": 0,
            "pm": 0,
            "full": 0,
        },
        "low_first": {
            "samples": 0,
            "am": 0,
            "lunch": 0,
            "pm": 0,
            "full": 0,
        },
    }

    ambiguous = 0
    no_first_hit = 0

    for d, day in df.groupby("date"):
        day = day.sort_index()

        london = get_session(day, LONDON_START, LONDON_END)
        post   = get_session(day, POST_START, NY_END)

        if london.empty or post.empty:
            continue

        london_high = london["high"].max()
        london_low  = london["low"].min()

        first_side = None
        first_ts = None

        # find first hit after London
        for ts, row in post.iterrows():
            hit_high = row["high"] >= london_high
            hit_low  = row["low"] <= london_low

            if hit_high and hit_low:
                ambiguous += 1
                first_side = "ambiguous"
                break
            if hit_high:
                first_side = "high"
                first_ts = ts
                break
            if hit_low:
                first_side = "low"
                first_ts = ts
                break

        if first_side is None:
            no_first_hit += 1
            continue
        if first_side == "ambiguous":
            continue

        remaining = post.loc[first_ts:]

        am = get_session(remaining, POST_START, NY_AM_END)
        lunch = get_session(remaining, NY_AM_END, LUNCH_END)
        pm = get_session(remaining, LUNCH_END, NY_END)

        if first_side == "high":
            results["high_first"]["samples"] += 1
            if (am["low"] <= london_low).any():
                results["high_first"]["am"] += 1
            if (lunch["low"] <= london_low).any():
                results["high_first"]["lunch"] += 1
            if (pm["low"] <= london_low).any():
                results["high_first"]["pm"] += 1
            if (remaining["low"] <= london_low).any():
                results["high_first"]["full"] += 1

        if first_side == "low":
            results["low_first"]["samples"] += 1
            if (am["high"] >= london_high).any():
                results["low_first"]["am"] += 1
            if (lunch["high"] >= london_high).any():
                results["low_first"]["lunch"] += 1
            if (pm["high"] >= london_high).any():
                results["low_first"]["pm"] += 1
            if (remaining["high"] >= london_high).any():
                results["low_first"]["full"] += 1

    def pct(x, n):
        return round(x / n, 4) if n > 0 else float("nan")

    print("\n=== LONDON LIQUIDITY — TIME OF DAY BREAKDOWN ===\n")

    for side in ["high_first", "low_first"]:
        label = "London HIGH first → NY hits LOW?" if side == "high_first" else "London LOW first → NY hits HIGH?"
        r = results[side]
        n = r["samples"]

        print(f"=== {label} ===")
        print("Samples:", n)
        print("NY AM:", pct(r["am"], n))
        print("Lunch:", pct(r["lunch"], n))
        print("PM:", pct(r["pm"], n))
        print("NY Full:", pct(r["full"], n))
        print()

    print("=== DEBUG ===")
    print("Ambiguous first-hit bars:", ambiguous)
    print("No first hit by EOD:", no_first_hit)


if __name__ == "__main__":
    main()

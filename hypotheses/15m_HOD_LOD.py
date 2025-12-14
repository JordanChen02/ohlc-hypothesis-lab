from pathlib import Path
import pandas as pd

DATA = Path("data/processed/nq_5m_clean.csv")
NY_TZ = "America/New_York"

# -----------------------------------
# CONFIG
# -----------------------------------
RANGE_MINUTES = 60   # set to 15 or 60


def main():
    # -----------------------------
    # Load data with explicit TZ handling
    # -----------------------------
    df = pd.read_csv(DATA)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert(NY_TZ)
    df = df.set_index("timestamp").sort_index()

    df["date"] = df.index.date

    # -----------------------------
    # Define opening range timestamps
    # -----------------------------
    if RANGE_MINUTES == 15:
        range_times = ["09:30", "09:35", "09:40"]
    elif RANGE_MINUTES == 60:
        range_times = [
            "09:30", "09:35", "09:40", "09:45",
            "09:50", "09:55",
            "10:00", "10:05", "10:10", "10:15",
            "10:20", "10:25",
        ]
    else:
        raise ValueError("RANGE_MINUTES must be 15 or 60")

    results = []

    for d, day in df.groupby("date"):
        # -----------------------------
        # Opening range
        # -----------------------------
        opening = day[day.index.strftime("%H:%M").isin(range_times)]

        if len(opening) != len(range_times):
            continue

        R_high = opening["high"].max()
        R_low = opening["low"].min()

        # -----------------------------
        # First break AFTER range
        # -----------------------------
        post = day[day.index > opening.index[-1]]

        break_time = None
        direction = None

        for ts, row in post.iterrows():
            if row["close"] < R_low:
                break_time = ts
                direction = "bear"
                break
            elif row["close"] > R_high:
                break_time = ts
                direction = "bull"
                break

        if break_time is None:
            continue

        # -----------------------------
        # From break → session close
        # -----------------------------
        rest = day.loc[break_time:]

        if direction == "bear":
            opposite_revisited = rest["high"].max() >= R_high
        else:
            opposite_revisited = rest["low"].min() <= R_low

        results.append(
            {
                "date": d,
                "direction": direction,
                "opposite_not_revisited": not opposite_revisited,
            }
        )

    res = pd.DataFrame(results)

    if res.empty:
        print("No valid samples found.")
        return

    print(f"\n=== RANGE: {RANGE_MINUTES} MINUTES ===")

    print("\n=== SAMPLE SIZE ===")
    print(res["direction"].value_counts())

    print("\n=== OPPOSITE SIDE NOT REVISITED RATE (X) ===")
    print(res.groupby("direction")["opposite_not_revisited"].mean())

    print("\n=== OVERALL X RATE ===")
    print(res["opposite_not_revisited"].mean())


if __name__ == "__main__":
    main()

from pathlib import Path
import pandas as pd

DATA = Path("data/processed/nq_5m_clean.csv")
N_FORWARD = 3  # number of 5m bars to define continuation
NY_TZ = "America/New_York"


def main():
    # --- Load CSV explicitly ---
    df = pd.read_csv(DATA)

    # --- Explicit timestamp handling (no guessing) ---
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert(NY_TZ)
    df = df.set_index("timestamp").sort_index()

    # Convenience column
    df["date"] = df.index.date

    results = []

    for d, day in df.groupby("date"):
        # --- Opening range: 9:30–9:35 ---
        or_bar = day[day.index.strftime("%H:%M") == "09:30"]

        if len(or_bar) != 1:
            continue

        or_high = or_bar["high"].iloc[0]
        or_low = or_bar["low"].iloc[0]
        or_time = or_bar.index[0]


        # Bars AFTER the opening range
        post = day[day.index > or_time]

        break_time = None
        direction = None

        # Find first close outside OR
        for ts, row in post.iterrows():
            if row["close"] > or_high:
                break_time = ts
                direction = "bull"
                break
            elif row["close"] < or_low:
                break_time = ts
                direction = "bear"
                break

        if break_time is None:
            continue

        # Look forward N bars after the break
        fwd = post.loc[break_time:].iloc[1 : 1 + N_FORWARD]
        if len(fwd) < N_FORWARD:
            continue

        # Continuation definition
        if direction == "bull":
            continued = fwd["high"].max() > day.loc[break_time, "high"]
        else:
            continued = fwd["low"].min() < day.loc[break_time, "low"]

        results.append(
            {
                "date": d,
                "direction": direction,
                "continued": continued,
            }
        )

    res = pd.DataFrame(results)

    if res.empty:
        print("No valid samples found.")
        return

    print("\n=== SAMPLE SIZE ===")
    print(res["direction"].value_counts())

    print("\n=== CONTINUATION RATE ===")
    print(res.groupby("direction")["continued"].mean())

    print("\n=== OVERALL CONTINUATION ===")
    print(res["continued"].mean())


if __name__ == "__main__":
    main()

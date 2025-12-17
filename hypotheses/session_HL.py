from pathlib import Path
import pandas as pd

DATA = Path("data/processed/nq_5m_clean.csv")
NY_TZ = "America/New_York"

ASIA_START = "20:00"
ASIA_END   = "00:00"

LONDON_START = "02:00"
LONDON_END   = "05:00"

NY_AM_START = "09:30"
NY_AM_END   = "11:00"

NY_START = "09:30"
NY_END   = "16:00"


def assign_trade_date(ts: pd.Series) -> pd.Series:
    """
    Map bars to a 'trade_date' (NY date).
    Any bar at/after 20:00 belongs to the next day's trade_date.
    """
    local = ts.dt.tz_convert(NY_TZ)
    d = local.dt.date
    t = local.dt.strftime("%H:%M")
    return pd.to_datetime(d) + pd.to_timedelta((t >= ASIA_START).astype(int), unit="D")


def session_slice(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """
    between_time cannot handle wrap-around (20:00–00:00) cleanly, so handle both.
    """
    if start < end:
        return df.between_time(start, end, inclusive="left")
    # wrap: e.g., 20:00–00:00
    a = df.between_time(start, "23:59", inclusive="both")
    b = df.between_time("00:00", end, inclusive="left")
    return pd.concat([a, b]).sort_index()


def main():
    df = pd.read_csv(DATA)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[["open", "high", "low", "close"]].dropna()

    # Add trade_date (NY date anchor)
    df = df.copy()
    df["trade_date"] = assign_trade_date(df.index.to_series())

    rows = []

    for trade_date, g in df.groupby("trade_date"):
        g = g.sort_index()

        asia = session_slice(g, ASIA_START, ASIA_END)
        london = session_slice(g, LONDON_START, LONDON_END)
        ny_am = session_slice(g, NY_AM_START, NY_AM_END)
        ny_full = session_slice(g, NY_START, NY_END)

        # Require all sessions present
        if asia.empty or london.empty or ny_am.empty or ny_full.empty:
            continue

        asia_high = float(asia["high"].max())
        asia_low = float(asia["low"].min())

        london_hit_high = bool((london["high"] >= asia_high).any())
        london_hit_low = bool((london["low"] <= asia_low).any())

        nyam_hit_high = bool((ny_am["high"] >= asia_high).any())
        nyam_hit_low = bool((ny_am["low"] <= asia_low).any())

        ny_hit_high = bool((ny_full["high"] >= asia_high).any())
        ny_hit_low = bool((ny_full["low"] <= asia_low).any())

        rows.append(
            {
                "trade_date": trade_date.date(),
                "asia_high": asia_high,
                "asia_low": asia_low,
                "london_hit_high": london_hit_high,
                "london_hit_low": london_hit_low,
                "nyam_hit_high": nyam_hit_high,
                "nyam_hit_low": nyam_hit_low,
                "ny_hit_high": ny_hit_high,
                "ny_hit_low": ny_hit_low,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        print("No valid samples found.")
        return

    def report(name, cond, target_nyam, target_ny):
        sample = out[cond]
        n = len(sample)
        if n == 0:
            print(f"\n=== {name} ===\nNo samples.")
            return
        print(f"\n=== {name} ===")
        print("Samples:", n)
        print("NY AM revisit rate:", round(sample[target_nyam].mean(), 4))
        print("NY full revisit rate:", round(sample[target_ny].mean(), 4))

    # Case A: London hits Asia High, not Asia Low -> does NY revisit Asia Low?
    report(
        "London hits Asia High ONLY -> NY revisits Asia Low?",
        cond=(out["london_hit_high"] & ~out["london_hit_low"]),
        target_nyam="nyam_hit_low",
        target_ny="ny_hit_low",
    )

    # Case B: London hits Asia Low, not Asia High -> does NY revisit Asia High?
    report(
        "London hits Asia Low ONLY -> NY revisits Asia High?",
        cond=(out["london_hit_low"] & ~out["london_hit_high"]),
        target_nyam="nyam_hit_high",
        target_ny="ny_hit_high",
    )

    # Optional: baseline (no London revisit at all)
    report(
        "London hits NEITHER Asia High nor Low -> NY revisits either side?",
        cond=(~out["london_hit_high"] & ~out["london_hit_low"]),
        target_nyam="nyam_hit_high",  # not perfect, but gives one side
        target_ny="ny_hit_high",
    )


if __name__ == "__main__":
    main()

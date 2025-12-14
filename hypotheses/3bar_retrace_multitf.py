from pathlib import Path
import pandas as pd

DATA = Path("data/processed/nq_5m_clean.csv")
NY_TZ = "America/New_York"

TIMEFRAMES = {
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1D": "1D",
}


def run_test(df, label):
    bear_wick = []
    bear_close = []

    bull_wick = []
    bull_close = []

    for i in range(1, len(df) - 1):
        c1 = df.iloc[i - 1]
        c2 = df.iloc[i]
        c3 = df.iloc[i + 1]

        # -------------------------
        # Bearish case
        # -------------------------
        if c2["close"] < c1["low"]:
            bear_wick.append(c3["high"] < c2["high"])
            bear_close.append(c3["close"] < c2["high"])

        # -------------------------
        # Bullish case
        # -------------------------
        if c2["close"] > c1["high"]:
            bull_wick.append(c3["low"] > c2["low"])
            bull_close.append(c3["close"] > c2["low"])

    print(f"\n=== {label} ===")

    if bear_wick:
        print("Bearish:")
        print("  Samples:", len(bear_wick))
        print("  Wick respected: ", round(sum(bear_wick) / len(bear_wick), 4))
        print("  Close respected:", round(sum(bear_close) / len(bear_close), 4))
    else:
        print("Bearish: No samples")

    if bull_wick:
        print("Bullish:")
        print("  Samples:", len(bull_wick))
        print("  Wick respected: ", round(sum(bull_wick) / len(bull_wick), 4))
        print("  Close respected:", round(sum(bull_close) / len(bull_close), 4))
    else:
        print("Bullish: No samples")


def main():
    # -----------------------------
    # Load base 5m data
    # -----------------------------
    df = pd.read_csv(DATA)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert(NY_TZ)
    df = df.set_index("timestamp").sort_index()

    for label, rule in TIMEFRAMES.items():
        ohlc = (
            df[["open", "high", "low", "close"]]
            .resample(rule)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                }
            )
            .dropna()
        )

        # RTH-only for intraday timeframes
        if label in {"5m", "15m"}:
            ohlc = ohlc.between_time("09:30", "16:00")

        run_test(ohlc, label)


if __name__ == "__main__":
    main()

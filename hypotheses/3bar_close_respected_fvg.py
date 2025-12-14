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

FVG_LOOKBACK = 100


def detect_fvgs(df):
    fvgs = []

    for i in range(2, len(df)):
        c0 = df.iloc[i - 2]
        c2 = df.iloc[i]

        # Bullish FVG
        if c2["low"] > c0["high"]:
            fvgs.append(
                {
                    "low": c0["high"],
                    "high": c2["low"],
                    "index": i,
                }
            )

        # Bearish FVG
        if c2["high"] < c0["low"]:
            fvgs.append(
                {
                    "low": c2["high"],
                    "high": c0["low"],
                    "index": i,
                }
            )

    return fvgs


def level_in_prior_fvg(level, fvg_list, current_index):
    for fvg in fvg_list:
        if fvg["index"] < current_index and fvg["index"] >= current_index - FVG_LOOKBACK:
            if fvg["low"] <= level <= fvg["high"]:
                return True
    return False


def run_test(df, label):
    fvgs = detect_fvgs(df)

    bear_with_fvg = []
    bear_without_fvg = []

    bull_with_fvg = []
    bull_without_fvg = []

    for i in range(1, len(df) - 1):
        c1 = df.iloc[i - 1]
        c2 = df.iloc[i]
        c3 = df.iloc[i + 1]

        # -------------------------
        # Bearish case
        # -------------------------
        if c2["close"] < c1["low"] and c3["close"] < c2["high"]:
            level = c2["high"]
            in_fvg = level_in_prior_fvg(level, fvgs, i)

            if in_fvg:
                bear_with_fvg.append(True)
            else:
                bear_without_fvg.append(True)

        # -------------------------
        # Bullish case
        # -------------------------
        if c2["close"] > c1["high"] and c3["close"] > c2["low"]:
            level = c2["low"]
            in_fvg = level_in_prior_fvg(level, fvgs, i)

            if in_fvg:
                bull_with_fvg.append(True)
            else:
                bull_without_fvg.append(True)

    print(f"\n=== {label} ===")

    def report(side, with_fvg, without_fvg):
        total = len(with_fvg) + len(without_fvg)
        if total == 0:
            print(f"{side}: No samples")
            return

        rate_with = len(with_fvg) / total if with_fvg else 0
        rate_without = len(without_fvg) / total if without_fvg else 0

        print(f"{side}:")
        print("  Total samples:", total)
        print("  In FVG:", len(with_fvg))
        print("  Not in FVG:", len(without_fvg))
        print("  Close-respected rate (in FVG):", round(rate_with, 4))
        print("  Close-respected rate (no FVG):", round(rate_without, 4))
        print("  Uplift:", round(rate_with - rate_without, 4))

    report("Bearish", bear_with_fvg, bear_without_fvg)
    report("Bullish", bull_with_fvg, bull_without_fvg)


def main():
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

        if label in {"5m", "15m"}:
            ohlc = ohlc.between_time("09:30", "16:00")

        run_test(ohlc, label)


if __name__ == "__main__":
    main()

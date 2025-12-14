import pandas as pd
from pathlib import Path

NY_TZ = "America/New_York"


def load_tradingview_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # TradingView uses 'time'
    if "time" not in df.columns:
        raise ValueError(f"'time' column not found. Columns: {df.columns.tolist()}")

    # Parse timestamps (TradingView exports in UTC)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True, errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Some timestamps failed to parse")

    # Convert to NY time
    df["timestamp"] = df["timestamp"].dt.tz_convert(NY_TZ)

    # Set index
    df = df.set_index("timestamp").sort_index()

    # Ensure OHLC columns
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop bad rows
    df = df.dropna(subset=["open", "high", "low", "close"])

    return df

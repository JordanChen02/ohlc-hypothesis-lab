import pandas as pd
from pathlib import Path


def detect_timestamp_column(df: pd.DataFrame) -> str:
    """
    Detect a reasonable timestamp column name.
    """
    candidates = [
        "timestamp",
        "datetime",
        "date",
        "time",
        "Date",
        "Time",
        "Datetime",
    ]

    for col in candidates:
        if col in df.columns:
            return col

    raise ValueError(
        f"No timestamp column found. Columns present: {list(df.columns)}"
    )


def main():
    root = Path(__file__).resolve().parents[1]  # project root
    raw_path = root / "data" / "raw" / "nq_1h.csv"
    out_path = root / "data" / "processed" / "nq_1h_clean.csv"

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_path}")

    print(f"Loading: {raw_path}")
    df = pd.read_csv(raw_path)

    # --- Detect timestamp column ---
    ts_col = detect_timestamp_column(df)
    print(f"Using timestamp column: '{ts_col}'")

    # --- Parse timestamps ---
    df[ts_col] = pd.to_datetime(
        df[ts_col],
        errors="coerce",
        utc=True
    )

    before = len(df)
    df = df.dropna(subset=[ts_col])
    dropped = before - len(df)

    # --- Index & ordering ---
    df = df.set_index(ts_col)
    df = df.sort_index()

    # --- Timezone normalization ---
    df = df.tz_convert("America/New_York")

    # --- Deduplication ---
    dupes = df.index.duplicated().sum()
    if dupes > 0:
        df = df[~df.index.duplicated(keep="first")]

    # --- Required OHLC columns ---
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # --- Sanity checks ---
    print("\n=== SANITY CHECKS ===")
    print(f"Rows: {len(df)}")
    print(f"Dropped invalid timestamps: {dropped}")
    print(f"Duplicate timestamps removed: {dupes}")
    print(f"Start: {df.index.min()}")
    print(f"End:   {df.index.max()}")

    # --- Save ---
    df.to_csv(out_path)
    print(f"\nSaved clean file → {out_path}")


if __name__ == "__main__":
    main()

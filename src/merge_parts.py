from pathlib import Path
import pandas as pd
from load_data import load_tradingview_csv

RAW = Path("data/raw")
PROCESSED = Path("data/processed")

FILES = [
    "nq_5m_part4.csv",  # oldest
    "nq_5m_part3.csv",
    "nq_5m_part2.csv",
    "nq_5m_part1.csv",  # newest
]

OUTFILE = PROCESSED / "nq_5m_clean.csv"


def main():
    dfs = []

    for fname in FILES:
        path = RAW / fname
        print(f"Loading {fname}...")
        df = load_tradingview_csv(path)
        print(
            f"  rows={len(df)}, "
            f"start={df.index.min()}, "
            f"end={df.index.max()}, "
            f"dupes={df.index.duplicated().sum()}"
        )
        dfs.append(df)

    print("\nConcatenating...")
    merged = pd.concat(dfs)

    print("Total rows before sort:", len(merged))
    merged = merged.sort_index()

    dupes = merged.index.duplicated().sum()
    print("Duplicate timestamps after concat:", dupes)

    if dupes > 0:
        print("Dropping duplicate timestamps (keeping first)...")
        merged = merged[~merged.index.duplicated(keep="first")]

    print("Total rows after dedupe:", len(merged))

    # sanity checks
    if not merged.index.is_monotonic_increasing:
        raise ValueError("Index is not strictly increasing after merge")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTFILE)

    print("\nSaved:", OUTFILE)
    print("Final range:")
    print("  Start:", merged.index.min())
    print("  End:  ", merged.index.max())


if __name__ == "__main__":
    main()

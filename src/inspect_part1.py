from pathlib import Path
from load_data import load_tradingview_csv


RAW = Path("data/raw")

if __name__ == "__main__":
    path = RAW / "nq_5m_part1.csv"

    df = load_tradingview_csv(path)

    print("FILE:", path.name)
    print("Rows:", len(df))
    print("Start:", df.index.min())
    print("End:", df.index.max())
    print("Duplicate timestamps:", df.index.duplicated().sum())
    print(df.head(3))
    print(df.tail(3))

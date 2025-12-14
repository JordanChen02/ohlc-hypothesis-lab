from pathlib import Path
import pandas as pd

df = pd.read_csv(
    Path("data/processed/nq_5m_clean.csv"),
    parse_dates=["timestamp"],
    index_col="timestamp"
)

print("Rows:", len(df))
print("Start:", df.index.min())
print("End:", df.index.max())
print("Duplicate timestamps:", df.index.duplicated().sum())

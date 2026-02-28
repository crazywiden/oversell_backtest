from pathlib import Path

import pandas as pd

from backtesting.config import BacktestConfig

REQUIRED_COLUMNS = {
    "ticker", "date", "open", "high", "low", "close", "volume",
    "name", "sector", "industry", "is_delisted", "close_ffill", "is_halt",
}


def load_price_data(config: BacktestConfig) -> pd.DataFrame:
    """Load and validate price data (parquet or CSV). Returns DataFrame sorted by ticker+date."""
    path = Path(config.data_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python data/v3/preprocess.py --source fake"
        )

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, parse_dates=["date"])

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    if config.start_date:
        df = df[df["date"] >= pd.Timestamp(config.start_date)]
    if config.end_date:
        df = df[df["date"] <= pd.Timestamp(config.end_date)]

    return df

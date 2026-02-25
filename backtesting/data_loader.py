from pathlib import Path

import pandas as pd

from backtesting.config import BacktestConfig

REQUIRED_COLUMNS = {
    "ticker", "date", "open", "high", "low", "close", "volume",
    "name", "sector", "industry", "is_delisted", "close_ffill", "is_halt",
}


def load_price_data(config: BacktestConfig) -> pd.DataFrame:
    """Load and validate prices.csv. Returns DataFrame sorted by ticker+date."""
    path = Path(config.data_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python data/v1/preprocess.py --source fake"
        )

    df = pd.read_csv(path, parse_dates=["date"])
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"prices.csv is missing columns: {missing}")

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df

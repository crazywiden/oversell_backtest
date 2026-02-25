"""
Preprocess Sharadar SEP + TICKERS CSVs into prices.csv for the backtesting engine.

Usage:
    python data/v1/preprocess.py --source fake
    python data/v1/preprocess.py --source raw

Output: data/v1/prices.csv (14 columns, sorted by ticker+date)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_V1 = REPO_ROOT / "data" / "v1"
FAKE_DIR = REPO_ROOT / "data" / "fake_data"
RAW_DIR = REPO_ROOT / "data" / "raw"

OUTPUT_COLUMNS = [
    "ticker", "date", "open", "high", "low", "close", "volume",
    "dividends", "name", "sector", "industry", "is_delisted",
    "close_ffill", "is_halt",
]


def load_data(source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load SEP prices and TICKERS metadata CSVs."""
    if source == "fake":
        sep_path = FAKE_DIR / "SHARADAR_SEP.csv"
        tickers_path = FAKE_DIR / "SHARADAR_TICKERS.csv"
    else:
        sep_path = RAW_DIR / "SHARADAR_SEP.csv"
        tickers_path = RAW_DIR / "SHARADAR_TICKERS.csv"

    if not sep_path.exists():
        sys.exit(f"Error: {sep_path} not found. Drop Sharadar CSVs into {sep_path.parent}/")
    if not tickers_path.exists():
        sys.exit(f"Error: {tickers_path} not found.")

    prices = pd.read_csv(sep_path, parse_dates=["date"])
    tickers = pd.read_csv(tickers_path)
    return prices, tickers


def filter_tickers(tickers: pd.DataFrame) -> pd.DataFrame:
    """Keep only US common stocks (domestic + ADRs with SEP prices)."""
    mask = tickers["category"].str.contains("Common Stock", na=False)
    return tickers[mask][["ticker", "name", "sector", "industry", "isdelisted"]].copy()


def merge_and_clean(prices: pd.DataFrame, tickers_filtered: pd.DataFrame) -> pd.DataFrame:
    """Merge price data with ticker metadata, rename columns, sort."""
    df = prices.merge(tickers_filtered, on="ticker", how="inner")
    df = df.rename(columns={"isdelisted": "is_delisted"})
    df["is_delisted"] = df["is_delisted"].str.upper() == "Y"
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill close price within each ticker to handle trading halts."""
    df = df.copy()
    # close_ffill: forward-filled close (fills NaN from halts)
    df["close_ffill"] = df.groupby("ticker")["close"].transform(
        lambda x: x.ffill()
    )
    # is_halt: True where original close was NaN (halt day)
    df["is_halt"] = df["close"].isna()
    # Replace NaN opens/highs/lows with close_ffill on halt days
    for col in ["open", "high", "low"]:
        df[col] = df[col].fillna(df["close_ffill"])
    df["close"] = df["close"].fillna(df["close_ffill"])
    # Fill remaining NaN volumes with 0 (no trading on halt day)
    df["volume"] = df["volume"].fillna(0).astype(int)
    df["dividends"] = df["dividends"].fillna(0.0)
    return df


def write_output(df: pd.DataFrame) -> Path:
    """Write final prices.csv to data/v1/."""
    out = df[OUTPUT_COLUMNS].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out = out.sort_values(["ticker", "date"]).reset_index(drop=True)
    out_path = DATA_V1 / "prices.csv"
    out.to_csv(out_path, index=False)
    return out_path


def main(source: str) -> None:
    print(f"Loading {source} data...")
    prices, tickers = load_data(source)
    print(f"  Loaded {len(prices)} price rows, {len(tickers)} ticker rows")

    tickers_filtered = filter_tickers(tickers)
    print(f"  Filtered to {len(tickers_filtered)} common stock tickers")

    df = merge_and_clean(prices, tickers_filtered)
    print(f"  After merge: {len(df)} rows, {df['ticker'].nunique()} tickers")

    df = handle_missing(df)
    n_halts = df["is_halt"].sum()
    print(f"  Forward-filled {n_halts} halt days")

    out_path = write_output(df)
    print(f"  Written: {out_path}")
    print(f"  Shape: {df.shape}, tickers: {sorted(df['ticker'].unique())}")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess Sharadar data to prices.csv")
    parser.add_argument("--source", choices=["fake", "raw"], default="fake",
                        help="'fake' for synthetic data, 'raw' for real Sharadar CSVs")
    args = parser.parse_args()
    main(args.source)

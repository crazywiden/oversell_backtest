"""
Preprocess Sharadar SEP + TICKERS CSVs into prices.csv for the backtesting engine.

Usage:
    python data/v3/preprocess.py --source fake
    python data/v3/preprocess.py --source raw

Output: data/v3/prices.csv (14 columns, sorted by ticker+date)

Changes from v2:
    - Removes Nano, Micro, and Small market cap tickers (scalemarketcap 1-3)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_V3 = REPO_ROOT / "data" / "v3"
FAKE_DIR = REPO_ROOT / "data" / "fake_data"
RAW_DIR = REPO_ROOT / "data" / "raw"

EXCLUDED_TICKERS = {"GBBKW", "GBBKR"}
EXCLUDED_MARKET_CAPS = {"1 - Nano", "2 - Micro", "3 - Small"}

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


def filter_tickers(tickers: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep only US common stocks (domestic + ADRs) with Mid cap or above."""
    mask = tickers["category"].str.contains("Common Stock", na=False)
    common = tickers[mask].drop_duplicates("ticker").copy()

    before = len(common)
    cap_mask = common["scalemarketcap"].isin(EXCLUDED_MARKET_CAPS) | common["scalemarketcap"].isna()
    common = common[~cap_mask]
    removed = before - len(common)

    return common[["ticker", "name", "sector", "industry", "isdelisted"]].copy(), removed


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
    if "dividends" in df.columns:
        df["dividends"] = df["dividends"].fillna(0.0)
    else:
        df["dividends"] = 0.0
    return df


def write_output(df: pd.DataFrame) -> Path:
    """Write final prices.csv to data/v3/."""
    out = df[OUTPUT_COLUMNS].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out = out.sort_values(["ticker", "date"]).reset_index(drop=True)
    out_path = DATA_V3 / "prices.csv"
    out.to_csv(out_path, index=False)
    return out_path


def main(source: str) -> None:
    print(f"Loading {source} data...")
    prices, tickers = load_data(source)
    print(f"  Loaded {len(prices)} price rows, {len(tickers)} ticker rows")

    prices = prices[~prices["ticker"].isin(EXCLUDED_TICKERS)]
    print(f"  Excluded tickers: {sorted(EXCLUDED_TICKERS)}")

    tickers_filtered, cap_removed = filter_tickers(tickers)
    print(f"  Removed {cap_removed} tickers with scalemarketcap in {sorted(EXCLUDED_MARKET_CAPS)} or NaN")
    print(f"  Kept {len(tickers_filtered)} Mid/Large/Mega cap tickers")

    df = merge_and_clean(prices, tickers_filtered)
    print(f"  After merge: {len(df)} rows, {df['ticker'].nunique()} tickers")

    df = handle_missing(df)
    n_halts = df["is_halt"].sum()
    print(f"  Forward-filled {n_halts} halt days")

    out_path = write_output(df)
    print(f"  Written: {out_path}")
    print(f"  Shape: {df.shape}, tickers: {df['ticker'].nunique()}")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess Sharadar data to prices.csv")
    parser.add_argument("--source", choices=["fake", "raw"], default="fake",
                        help="'fake' for synthetic data, 'raw' for real Sharadar CSVs")
    args = parser.parse_args()
    main(args.source)

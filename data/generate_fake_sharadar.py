"""
Generate fake Sharadar-compatible data for development and testing.

Produces two CSV files matching the exact schema of:
  - SHARADAR/SEP  (daily equity prices)
  - SHARADAR/TICKERS (company metadata)

Data covers 3 years (2022-01-03 to 2024-12-31) for 5 stocks.
Includes one delisted stock to test survivorship-bias-free code paths.
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# 1. Define the 5 fake stocks (realistic but clearly synthetic)
# ---------------------------------------------------------------------------
STOCKS = {
    "AAPL": {
        "permaticker": 199059,
        "name": "Apple Inc",
        "exchange": "NASDAQ",
        "isdelisted": "N",
        "category": "Domestic Common Stock",
        "cusips": "037833100",
        "siccode": 3571,
        "sicsector": "Manufacturing",
        "sicindustry": "Electronic Computers",
        "famasector": "Business Equipment",
        "famaindustry": "Computers",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "scalemarketcap": "6 - Mega",
        "scalerevenue": "6 - Mega",
        "relatedtickers": "",
        "currency": "USD",
        "location": "California; U.S.A",
        "companysite": "https://www.apple.com",
        "start_price": 182.0,
        "annual_drift": 0.12,
        "annual_vol": 0.28,
        "avg_volume": 75_000_000,
        "div_per_share": 0.24,  # quarterly dividend
        "div_months": [2, 5, 8, 11],
    },
    "MSFT": {
        "permaticker": 198070,
        "name": "Microsoft Corp",
        "exchange": "NASDAQ",
        "isdelisted": "N",
        "category": "Domestic Common Stock",
        "cusips": "594918104",
        "siccode": 7372,
        "sicsector": "Services",
        "sicindustry": "Prepackaged Software",
        "famasector": "Business Equipment",
        "famaindustry": "Software",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "scalemarketcap": "6 - Mega",
        "scalerevenue": "6 - Mega",
        "relatedtickers": "",
        "currency": "USD",
        "location": "Washington; U.S.A",
        "companysite": "https://www.microsoft.com",
        "start_price": 336.0,
        "annual_drift": 0.15,
        "annual_vol": 0.26,
        "avg_volume": 30_000_000,
        "div_per_share": 0.68,
        "div_months": [3, 6, 9, 12],
    },
    "JPM": {
        "permaticker": 110647,
        "name": "JPMorgan Chase & Co",
        "exchange": "NYSE",
        "isdelisted": "N",
        "category": "Domestic Common Stock",
        "cusips": "46625H100",
        "siccode": 6020,
        "sicsector": "Finance",
        "sicindustry": "State Chartered Banks",
        "famasector": "Other",
        "famaindustry": "Banking",
        "sector": "Financial Services",
        "industry": "Banks - Diversified",
        "scalemarketcap": "6 - Mega",
        "scalerevenue": "6 - Mega",
        "relatedtickers": "",
        "currency": "USD",
        "location": "New York; U.S.A",
        "companysite": "https://www.jpmorganchase.com",
        "start_price": 158.0,
        "annual_drift": 0.08,
        "annual_vol": 0.24,
        "avg_volume": 12_000_000,
        "div_per_share": 1.00,
        "div_months": [1, 4, 7, 10],
    },
    "JNJ": {
        "permaticker": 110427,
        "name": "Johnson & Johnson",
        "exchange": "NYSE",
        "isdelisted": "N",
        "category": "Domestic Common Stock",
        "cusips": "478160104",
        "siccode": 2834,
        "sicsector": "Manufacturing",
        "sicindustry": "Pharmaceutical Preparations",
        "famasector": "Healthcare",
        "famaindustry": "Pharmaceutical Products",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers - General",
        "scalemarketcap": "6 - Mega",
        "scalerevenue": "6 - Mega",
        "relatedtickers": "",
        "currency": "USD",
        "location": "New Jersey; U.S.A",
        "companysite": "https://www.jnj.com",
        "start_price": 172.0,
        "annual_drift": 0.05,
        "annual_vol": 0.18,
        "avg_volume": 8_000_000,
        "div_per_share": 1.13,
        "div_months": [3, 6, 9, 12],
    },
    "ZNRG": {
        # Fictitious delisted stock — tests survivorship-bias-free code paths
        "permaticker": 999001,
        "name": "ZetaNRG Corp",
        "exchange": "NASDAQ",
        "isdelisted": "Y",
        "category": "Domestic Common Stock",
        "cusips": "999888777",
        "siccode": 1311,
        "sicsector": "Mining",
        "sicindustry": "Crude Petroleum & Natural Gas",
        "famasector": "Oil",
        "famaindustry": "Petroleum and Natural Gas",
        "sector": "Energy",
        "industry": "Oil & Gas E&P",
        "scalemarketcap": "2 - Micro",
        "scalerevenue": "2 - Micro",
        "relatedtickers": "",
        "currency": "USD",
        "location": "Texas; U.S.A",
        "companysite": "https://www.zetanrg-example.com",
        "start_price": 24.0,
        "annual_drift": -0.30,  # declining stock
        "annual_vol": 0.55,     # high volatility
        "avg_volume": 500_000,
        "div_per_share": 0.0,
        "div_months": [],
        "delist_date": "2024-03-15",  # delisted mid-dataset
    },
}

# ---------------------------------------------------------------------------
# 2. Build the US trading calendar (exclude weekends + major holidays)
# ---------------------------------------------------------------------------
US_HOLIDAYS = pd.to_datetime([
    # 2022
    "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30",
    "2022-06-20", "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26",
    # 2023
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
    "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
])

all_dates = pd.bdate_range("2022-01-03", "2024-12-31", freq="B")
trading_dates = all_dates[~all_dates.isin(US_HOLIDAYS)]

# ---------------------------------------------------------------------------
# 3. Generate daily OHLCV data (geometric Brownian motion)
# ---------------------------------------------------------------------------

def generate_price_series(cfg, dates):
    """Generate realistic daily OHLCV via geometric Brownian motion."""
    n = len(dates)
    dt = 1 / 252
    drift = cfg["annual_drift"]
    vol = cfg["annual_vol"]

    # Log-normal daily returns
    daily_returns = np.exp(
        (drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * np.random.randn(n)
    )

    # Build close price series
    close = np.empty(n)
    close[0] = cfg["start_price"]
    for i in range(1, n):
        close[i] = close[i - 1] * daily_returns[i]

    # Clamp to $0.01 minimum
    close = np.maximum(close, 0.01)

    # Generate OHLV from close
    intraday_range = vol * np.sqrt(dt) * np.abs(np.random.randn(n)) * close
    high = close + intraday_range * np.random.uniform(0.3, 0.8, n)
    low = close - intraday_range * np.random.uniform(0.3, 0.8, n)
    low = np.maximum(low, 0.01)
    open_ = low + (high - low) * np.random.uniform(0.2, 0.8, n)

    # Ensure OHLC consistency
    high = np.maximum(high, np.maximum(open_, close))
    low = np.minimum(low, np.minimum(open_, close))

    # Volume: base + volatility-correlated noise
    base_vol = cfg["avg_volume"]
    volume = (
        base_vol
        * np.exp(0.3 * np.random.randn(n))
        * (1 + 2 * np.abs(daily_returns - 1))
    ).astype(int)

    # Dividends
    dividends = np.zeros(n)
    for i, d in enumerate(dates):
        if d.month in cfg["div_months"] and 10 <= d.day <= 20:
            # Only one ex-date per quarter
            if i == 0 or dates[i - 1].month != d.month:
                dividends[i] = cfg["div_per_share"]

    # closeunadj: simulate a 2:1 split mid-2023 for AAPL only
    closeunadj = close.copy()

    return pd.DataFrame({
        "ticker": cfg["_ticker"],
        "date": dates,
        "open": np.round(open_, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
        "volume": volume,
        "closeunadj": np.round(closeunadj, 2),
        "dividends": np.round(dividends, 4),
        "lastupdated": dates,  # same as date for fake data
    })


sep_frames = []
for ticker, cfg in STOCKS.items():
    cfg["_ticker"] = ticker

    # Delisted stocks stop trading at delist_date
    if "delist_date" in cfg:
        stock_dates = trading_dates[trading_dates <= cfg["delist_date"]]
    else:
        stock_dates = trading_dates

    df = generate_price_series(cfg, stock_dates)
    sep_frames.append(df)

sep_df = pd.concat(sep_frames, ignore_index=True)

# Add a realistic 2:1 split for AAPL in mid-2023
# Pre-split: closeunadj = close * 2 for dates before split
split_date = pd.Timestamp("2023-06-15")
mask = (sep_df["ticker"] == "AAPL") & (sep_df["date"] < split_date)
sep_df.loc[mask, "closeunadj"] = (sep_df.loc[mask, "close"] * 2).round(2)

# Format dates as strings
sep_df["date"] = sep_df["date"].dt.strftime("%Y-%m-%d")
sep_df["lastupdated"] = sep_df["lastupdated"].dt.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# 4. Build the TICKERS metadata table
# ---------------------------------------------------------------------------

tickers_rows = []
for ticker, cfg in STOCKS.items():
    if "delist_date" in cfg:
        stock_dates = trading_dates[trading_dates <= cfg["delist_date"]]
    else:
        stock_dates = trading_dates

    tickers_rows.append({
        "table": "SEP",
        "permaticker": cfg["permaticker"],
        "ticker": ticker,
        "name": cfg["name"],
        "exchange": cfg["exchange"],
        "isdelisted": cfg["isdelisted"],
        "category": cfg["category"],
        "cusips": cfg["cusips"],
        "siccode": cfg["siccode"],
        "sicsector": cfg["sicsector"],
        "sicindustry": cfg["sicindustry"],
        "famasector": cfg["famasector"],
        "famaindustry": cfg["famaindustry"],
        "sector": cfg["sector"],
        "industry": cfg["industry"],
        "scalemarketcap": cfg["scalemarketcap"],
        "scalerevenue": cfg["scalerevenue"],
        "relatedtickers": cfg.get("relatedtickers", ""),
        "currency": cfg["currency"],
        "location": cfg["location"],
        "lastupdated": "2024-12-31",
        "firstadded": "2022-01-03",
        "firstpricedate": str(stock_dates[0].date()),
        "lastpricedate": str(stock_dates[-1].date()),
        "firstquarter": "2022-03-31",
        "lastquarter": "2024-12-31" if cfg["isdelisted"] == "N" else "2024-03-31",
        "secfilings": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}",
        "companysite": cfg["companysite"],
    })

tickers_df = pd.DataFrame(tickers_rows)

# ---------------------------------------------------------------------------
# 5. Write to CSV
# ---------------------------------------------------------------------------

sep_path = OUTPUT_DIR / "SHARADAR_SEP.csv"
tickers_path = OUTPUT_DIR / "SHARADAR_TICKERS.csv"

sep_df.to_csv(sep_path, index=False)
tickers_df.to_csv(tickers_path, index=False)

print(f"SEP:     {sep_path}  ({len(sep_df):,} rows, {sep_df['ticker'].nunique()} tickers)")
print(f"TICKERS: {tickers_path}  ({len(tickers_df)} rows)")
print()
print("SEP columns:", list(sep_df.columns))
print("TICKERS columns:", list(tickers_df.columns))
print()
print("Sample SEP data:")
print(sep_df.groupby("ticker").first().to_string())
print()
print("Date range per ticker:")
for t in sep_df["ticker"].unique():
    sub = sep_df[sep_df["ticker"] == t]
    print(f"  {t}: {sub['date'].min()} to {sub['date'].max()} ({len(sub)} trading days)")

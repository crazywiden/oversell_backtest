# Backend Data Pipeline Plan — v1

**Date:** 2026-02-24
**Author:** backend-planner (Designer mode)
**Status:** Draft

---

## 1. Summary & Context

This document specifies the data folder layout and the first preprocessing pipeline
(`data/v1/`) for the oversell backtesting platform. The pipeline reads raw Sharadar
equity data (daily prices + ticker metadata), filters and cleans it, and outputs a
single CSV file ready for the backtesting engine.

### Relevant Existing Files

| File | Purpose |
|---|---|
| `data/fake_data/SHARADAR_SEP.csv` | 3566 rows, 5 tickers, 2022–2024. Columns: ticker, date, open, high, low, close, volume, closeunadj, dividends, lastupdated |
| `data/fake_data/SHARADAR_TICKERS.csv` | 5 rows. Full Sharadar ticker metadata schema (28 columns) |
| `data/fake_data/generate_fake_sharadar.py` | Generates the two fake CSVs. Includes one delisted stock (ZNRG, delisted 2024-03-15) for survivorship bias testing |
| `CLAUDE.md` | Project conventions: pandas/numpy, vectorized ops, survivorship-bias-aware, separate concerns |

---

## 2. Goals

1. Establish a clear, versioned folder structure under `data/` that separates raw inputs from processed outputs.
2. Produce a single clean CSV (`data/v1/prices.csv`) that any downstream backtesting engine can load with one `pd.read_csv()` call.
3. Include delisted stocks to avoid survivorship bias.
4. Forward-fill missing close prices and flag trading halts so the backtesting engine does not need to handle gaps.
5. Merge essential ticker metadata (name, sector, industry) into the price data so the engine does not need to perform its own joins.
6. Support both real data (`data/raw/`) and fake data (`data/fake_data/`) via a CLI flag.

## 3. Non-Goals

- No database, no Parquet, no Arrow. CSV only.
- No incremental/streaming updates. The script always processes from scratch.
- No data download automation (the user manually places files in `data/raw/`).
- No derived features (returns, moving averages, signals). That belongs to the signal generation layer.
- No multi-version orchestration. `v1` is standalone; future versions (v2, v3) will be separate folders with their own `preprocess.py`.

---

## 4. Proposed Folder Structure

```
data/
  raw/                          # User drops real Sharadar CSVs here
    SHARADAR_SEP.csv            # (gitignored -- purchased data)
    SHARADAR_TICKERS.csv        # (gitignored -- purchased data)
    .gitkeep                    # Keep the folder in git
  fake_data/                    # Already exists
    generate_fake_sharadar.py
    SHARADAR_SEP.csv
    SHARADAR_TICKERS.csv
  v1/
    description.md              # Human-readable: what this version does
    preprocess.py               # Standalone script
    prices.csv                  # OUTPUT (gitignored)
```

### .gitignore additions

```
data/raw/*.csv
data/v1/prices.csv
```

Note: `data/raw/.gitkeep` and all files under `data/fake_data/` remain tracked.

---

## 5. Output CSV Schema: `data/v1/prices.csv`

The output is sorted by `(ticker, date)`. One row per ticker per trading day.

| Column | Type | Source | Description |
|---|---|---|---|
| `ticker` | str | SEP.ticker | Stock ticker symbol |
| `date` | str (YYYY-MM-DD) | SEP.date | Trading date |
| `open` | float | SEP.open | Adjusted open price |
| `high` | float | SEP.high | Adjusted high price |
| `low` | float | SEP.low | Adjusted low price |
| `close` | float | SEP.close | Adjusted close price (primary price field) |
| `volume` | int | SEP.volume | Daily volume |
| `dividends` | float | SEP.dividends | Dividend per share on ex-date (0.0 otherwise) |
| `name` | str | TICKERS.name | Company name |
| `sector` | str | TICKERS.sector | Sector (e.g., "Technology") |
| `industry` | str | TICKERS.industry | Industry (e.g., "Consumer Electronics") |
| `is_delisted` | bool | TICKERS.isdelisted | True if ticker is delisted (Y/N mapped to True/False) |
| `close_ffill` | float | Derived | Forward-filled close (fills gaps from halts/missing days) |
| `is_halt` | bool | Derived | True if close was missing and was forward-filled |

### Design Decisions on Schema

- **`close` stays as-is.** The raw adjusted close is preserved unchanged. `close_ffill` is
  provided separately so the engine can distinguish real prices from forward-filled values.
- **`closeunadj` is dropped.** The backtesting engine uses adjusted prices. Unadjusted
  prices add confusion with no benefit for the current oversell strategy use case.
- **`lastupdated` is dropped.** It is metadata about the data vendor's pipeline, not the stock.
- **Metadata columns are limited to `name`, `sector`, `industry`, `is_delisted`.** These are
  the only fields useful for filtering and reporting in v1.
- **No `returns` column.** Computing returns is a signal-layer concern, not a data-layer
  concern (per CLAUDE.md: "Separate concerns: data ingestion → signal generation").

---

## 6. Preprocessing Steps (in order)

### Step 1: Load raw data
- Read `SHARADAR_SEP.csv` and `SHARADAR_TICKERS.csv` from the source directory
  (either `data/raw/` or `data/fake_data/`).
- Parse the `date` column as datetime immediately via `parse_dates=["date"]`.
- Fail fast with a clear `FileNotFoundError` if either file is missing.

### Step 2: Filter TICKERS to US common stocks
- Keep only rows where `category == "Domestic Common Stock"`.
- Keep only rows where `table == "SEP"` (not SFP or other Sharadar tables).
- Keep both delisted (`isdelisted == "Y"`) and non-delisted stocks. Critical for survivorship-bias-free backtesting.

### Step 3: Filter SEP to matching tickers
- Inner-join SEP with the filtered TICKERS on `ticker`.
- This removes non-common-stock price rows (ETFs, ADRs, preferred shares, warrants).

### Step 4: Merge metadata
- From the TICKERS join, bring in: `name`, `sector`, `industry`, `isdelisted`.
- Rename `isdelisted` to `is_delisted` and map `"Y"` → `True`, `"N"` → `False`.

### Step 5: Handle missing data
- Sort by `(ticker, date)`.
- Within each ticker group:
  - Create `close_ffill` = forward-fill of `close` within each ticker.
  - Create `is_halt` = True where the original `close` was NaN.
- Drop any rows where `close_ffill` is still NaN after forward-fill (first row of ticker has no prior value).

### Step 6: Select and order columns
- Keep only the 14 columns defined in the output schema (Section 5).
- Order them as specified in the schema table.

### Step 7: Sort and write
- Sort by `(ticker, date)`.
- Format `date` as `YYYY-MM-DD` string.
- Write to `data/v1/prices.csv` with `index=False`.
- Print summary statistics to stdout: total row count, ticker count, date range, halt count.

---

## 7. `preprocess.py` File Structure

```python
"""
data/v1/preprocess.py

Preprocesses raw Sharadar data into a clean CSV for backtesting.

Usage:
    python data/v1/preprocess.py                  # defaults to data/raw/
    python data/v1/preprocess.py --source fake     # uses data/fake_data/
    python data/v1/preprocess.py --source raw      # uses data/raw/ (explicit)
"""

import argparse
from pathlib import Path
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DIRS = {
    "raw": REPO_ROOT / "data" / "raw",
    "fake": REPO_ROOT / "data" / "fake_data",
}
OUTPUT_PATH = Path(__file__).resolve().parent / "prices.csv"

OUTPUT_COLS = [
    "ticker", "date", "open", "high", "low", "close", "volume",
    "dividends", "name", "sector", "industry", "is_delisted",
    "close_ffill", "is_halt",
]


def load_data(source_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load SEP and TICKERS CSVs. Raises FileNotFoundError with clear message."""
    ...


def filter_tickers(tickers_df: pd.DataFrame) -> pd.DataFrame:
    """Keep Domestic Common Stock from SEP table only. Includes delisted."""
    ...


def merge_and_clean(sep_df: pd.DataFrame, tickers_df: pd.DataFrame) -> pd.DataFrame:
    """Inner-join on ticker. Map isdelisted Y/N → bool. Drop unused columns."""
    ...


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized forward-fill close within each ticker group. Adds close_ffill, is_halt."""
    ...


def write_output(df: pd.DataFrame, output_path: Path) -> None:
    """Sort, select OUTPUT_COLS, format date, write CSV, print summary."""
    ...


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["raw", "fake"], default="raw")
    args = parser.parse_args()
    source_dir = SOURCE_DIRS[args.source]
    sep_df, tickers_df = load_data(source_dir)
    tickers_df = filter_tickers(tickers_df)
    df = merge_and_clean(sep_df, tickers_df)
    df = handle_missing(df)
    write_output(df, OUTPUT_PATH)


if __name__ == "__main__":
    main()
```

### Key Characteristics

- **5 functions + main.** Each function does exactly one thing. No class hierarchy.
- **Vectorized.** `handle_missing` uses `groupby("ticker")["close"].ffill()`, not row-by-row loops.
- **Path resolution via `__file__`.** Works from any working directory.
- **Fail-fast.** `load_data` raises `FileNotFoundError` with a clear message.
- **No dependencies beyond pandas.**

---

## 8. `description.md` Contents (outline)

The file `data/v1/description.md` will contain:

- What v1 does in plain English
- Input files and expected source locations
- Filter criteria (Domestic Common Stock, SEP table, includes delisted)
- Output schema with column descriptions
- How missing data is handled (forward-fill close only, is_halt flag)
- What is NOT included (no returns, no signals, no unadjusted prices)
- How to run the script

---

## 9. Alternatives Considered

### Alternative A: Two output files (prices.csv + tickers.csv)

**Verdict: Rejected.** Downstream code must join on every load. One file, one `pd.read_csv()` call is simpler and eliminates a class of join-related bugs.

### Alternative B: Parquet format

**Verdict: Rejected.** Explicitly prohibited by requirements. Revisit in v2 if performance demands it.

### Alternative C: Include computed columns (returns, rolling means)

**Verdict: Rejected.** Violates separation of concerns (CLAUDE.md). Different strategies need different derived features.

---

## 10. Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Real Sharadar data has unexpected `category` values | Some stocks incorrectly filtered | Log distinct values found and counts kept vs. dropped |
| NaN in columns other than `close` (open, high, low, volume) | Engine receives unexpected NaN | v1 only forward-fills `close`. Others left as-is and documented |
| File size: real Sharadar SEP can be 2-4 GB | Memory pressure | pandas handles on 8+ GB RAM. Add chunked reads in future if needed |

---

## 11. Implementation Checklist

- [ ] Create `data/raw/` directory with `.gitkeep` file
- [ ] Create `data/v1/` directory
- [ ] Add `.gitignore` entries: `data/raw/*.csv` and `data/v1/prices.csv`
- [ ] Write `data/v1/description.md`
- [ ] Implement `data/v1/preprocess.py` with the 5 functions described in Section 7
- [ ] Run `python data/v1/preprocess.py --source fake` and verify:
  - Output exists at `data/v1/prices.csv`
  - All 5 tickers present including delisted ZNRG
  - `is_delisted` is True for ZNRG, False for others
  - No NaN in `close_ffill`
  - Sorted by `(ticker, date)`
- [ ] Commit all new files

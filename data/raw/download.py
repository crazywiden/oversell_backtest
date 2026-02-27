#!/usr/bin/env python3
"""
Download all Sharadar SEP database tables from Nasdaq Data Link.

Usage:
    python data/raw/download.py              # download all tables
    python data/raw/download.py SEP TICKERS  # download specific tables

Tables (all included in the SEP subscription):
    SEP      - Daily OHLCV equity prices
    TICKERS  - Ticker metadata (sector, industry, delisted status)
    DAILY    - Derived daily metrics: market cap, P/E, EV, P/B, dividend yield
    SP500    - Historical S&P 500 additions/removals since 1957
    ACTIONS  - Corporate actions: splits, dividends, spinoffs
    EVENTS   - SEC Form 8-K events since 1993

Output:
    data/raw/SHARADAR_{TABLE}.csv for each table

Next step:
    python data/v1/preprocess.py --source raw
"""

import io
import json
import os
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

RAW_DIR = Path(__file__).resolve().parent
ALL_TABLES = ["SEP", "TICKERS", "DAILY", "SP500", "ACTIONS", "EVENTS"]
POLL_INTERVAL = 30  # seconds between status checks


def get_api_key() -> str:
    key = os.environ.get("SHARADAR_API_KEY", "").strip()
    if not key:
        sys.exit("Error: SHARADAR_API_KEY environment variable not set.")
    return key


def request_bulk_download(table: str, api_key: str) -> str | None:
    """Initiate bulk download and poll until ready. Returns download URL, or None if not accessible."""
    url = (
        f"https://data.nasdaq.com/api/v3/datatables/SHARADAR/{table}.json"
        f"?qopts.export=true&api_key={api_key}"
    )
    print(f"  Requesting export for SHARADAR/{table}...")

    while True:
        try:
            with urllib.request.urlopen(url) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 422):
                print(f"  Skipped: not included in your subscription (HTTP {e.code})")
                return None
            raise

        bulk = data["datatable_bulk_download"]
        status = bulk["file"]["status"]
        link = bulk["file"]["link"]

        print(f"  Status: {status}")
        if status == "fresh":
            return link

        # "generating" or "regenerating" — wait and retry
        print(f"  Waiting {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)


def download_and_extract(table: str, link: str) -> None:
    """Download ZIP, extract and concatenate CSV(s), save as SHARADAR_{TABLE}.csv."""
    out_path = RAW_DIR / f"SHARADAR_{table}.csv"
    print(f"  Downloading ZIP...")

    with urllib.request.urlopen(link) as resp:
        zip_bytes = resp.read()

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = sorted(n for n in zf.namelist() if n.endswith(".csv"))
        if not csv_names:
            sys.exit(f"Error: no CSV found in ZIP for {table}")

        print(f"  Extracting {len(csv_names)} file(s)...")
        with out_path.open("wb") as out:
            for i, name in enumerate(csv_names):
                with zf.open(name) as part:
                    content = part.read()
                    if i > 0:
                        # Skip header row in subsequent parts
                        newline = content.index(b"\n")
                        content = content[newline + 1:]
                    out.write(content)

    size_mb = out_path.stat().st_size / 1_000_000
    print(f"  Saved: {out_path.name} ({size_mb:.1f} MB)")


def main() -> None:
    api_key = get_api_key()

    tables = sys.argv[1:] if len(sys.argv) > 1 else ALL_TABLES
    skipped = []

    for table in tables:
        print(f"\n[SHARADAR/{table}]")
        link = request_bulk_download(table, api_key)
        if link is None:
            skipped.append(table)
            continue
        download_and_extract(table, link)

    print("\nDone.")
    if skipped:
        print(f"Skipped (not in subscription): {', '.join(skipped)}")
    print("Next: python data/v1/preprocess.py --source raw")


if __name__ == "__main__":
    main()

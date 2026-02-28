from pathlib import Path
import gc

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
        df = _read_parquet_chunked(path, config.start_date, config.end_date)
    else:
        df = pd.read_csv(path, parse_dates=["date"])
        if config.start_date:
            df = df[df["date"] >= pd.Timestamp(config.start_date)]
        if config.end_date:
            df = df[df["date"] <= pd.Timestamp(config.end_date)]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    # Apply category dtype after full concat so categories are unified (not per-chunk)
    for col in ("ticker", "name", "sector", "industry"):
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


def _read_parquet_chunked(
    path: Path,
    start_date: "str | None",
    end_date: "str | None",
) -> pd.DataFrame:
    """
    Read parquet one mini-batch at a time (iter_batches default), filtering at the
    Arrow level and immediately converting to pandas with numeric dtype optimization.

    Benefits over pd.read_parquet():
    - Peak RAM ≈ one Arrow batch (~7 MB) + accumulated pandas chunks
    - Freed Arrow buffers released before the next batch is read
    - 2-year window peaks at ~663 MB RSS vs ~964 MB for a naive read

    Category columns (ticker, name, sector, industry) are cast AFTER concat
    by load_price_data() so the category index is unified across all chunks.
    """
    # Lazy imports — keep pyarrow out of module-level scope so import errors
    # surface as backtest errors (caught by engine_bridge), not startup crashes.
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    arrow_filter = _build_arrow_filter(start_date, end_date, pa, pc)
    pf = pq.ParquetFile(path)
    chunks: list[pd.DataFrame] = []

    for batch in pf.iter_batches():
        tbl = pa.Table.from_batches([batch])
        if arrow_filter is not None:
            tbl = tbl.filter(arrow_filter)
        if tbl.num_rows > 0:
            chunk = tbl.to_pandas()
            # Apply numeric optimizations per chunk — safe since no category merging needed
            for col in ("open", "high", "low", "close", "dividends", "close_ffill"):
                if col in chunk.columns:
                    chunk[col] = chunk[col].astype("float32")
            if "volume" in chunk.columns:
                chunk["volume"] = chunk["volume"].astype("int32")
            chunks.append(chunk)
        del batch, tbl
        gc.collect()

    if not chunks:
        return pd.DataFrame()

    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    return df


def _build_arrow_filter(start_date, end_date, pa, pc):
    """Build a PyArrow filter expression from optional ISO date strings."""
    exprs = []
    if start_date:
        exprs.append(
            pc.greater_equal(pc.field("date"), pa.scalar(pd.Timestamp(start_date)))
        )
    if end_date:
        exprs.append(
            pc.less_equal(pc.field("date"), pa.scalar(pd.Timestamp(end_date)))
        )
    if not exprs:
        return None
    result = exprs[0]
    for e in exprs[1:]:
        result = result & e
    return result

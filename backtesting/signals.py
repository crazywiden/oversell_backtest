import numpy as np
import pandas as pd

from backtesting.config import BacktestConfig


def compute_os_scores(df: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """
    Compute OS (oversold) scores for each ticker per day.

    OS_T = w1 * D(r)_T + w2 * D(v)_T

    where:
      D(r)_T = sign(r_T) * (|r_T| - rolling_mean(|r|, N)) / rolling_std(|r|, N)
      D(v)_T = (volume_T - rolling_mean(volume, N)) / rolling_std(volume, N)

    First N rows per ticker have NaN os_score (excluded by engine).
    Division by zero (std=0) produces NaN (stock safely excluded).
    Intermediate series are cast to float32 to limit peak RAM usage.
    """
    N, w1, w2 = config.N, config.w1, config.w2
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    # Step 1: daily return per ticker (first row per ticker = NaN)
    df["r"] = (
        df.groupby("ticker", observed=True)["close"]
        .pct_change()
        .astype("float32")
    )

    # Step 2: signed z-score of absolute return (float32 to save RAM)
    def _d_r(x: pd.Series) -> pd.Series:
        ax = x.abs()
        return (np.sign(x) * (ax - ax.rolling(N).mean()) / ax.rolling(N).std()).astype(
            "float32"
        )

    df["D_r"] = df.groupby("ticker", observed=True)["r"].transform(_d_r)

    # Step 3: volume z-score (float32 to save RAM)
    def _d_v(x: pd.Series) -> pd.Series:
        return ((x - x.rolling(N).mean()) / x.rolling(N).std()).astype("float32")

    df["D_v"] = df.groupby("ticker", observed=True)["volume"].transform(_d_v)

    # Step 4: combined OS score
    df["os_score"] = (w1 * df["D_r"] + w2 * df["D_v"]).astype("float32")

    return df

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
    """
    N, w1, w2 = config.N, config.w1, config.w2
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    # Step 1: daily return per ticker (first row per ticker = NaN)
    df["r"] = df.groupby("ticker")["close"].pct_change()

    # Step 2: signed z-score of absolute return
    df["D_r"] = df.groupby("ticker")["r"].transform(
        lambda x: np.sign(x) * (x.abs() - x.abs().rolling(N).mean()) / x.abs().rolling(N).std()
    )

    # Step 3: volume z-score
    df["D_v"] = df.groupby("ticker")["volume"].transform(
        lambda x: (x - x.rolling(N).mean()) / x.rolling(N).std()
    )

    # Step 4: combined OS score
    df["os_score"] = w1 * df["D_r"] + w2 * df["D_v"]

    return df

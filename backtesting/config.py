import dataclasses
from typing import Optional


@dataclasses.dataclass
class BacktestConfig:
    # Signal hyperparameters
    N: int = 20                     # Rolling window for z-scores (trading days)
    w1: float = -1.0                # Weight for return z-score D(r)
    w2: float = 1.0                 # Weight for volume z-score D(v)

    # Exit hyperparameters
    win_take_rate: float = 0.05     # Take-profit threshold (5%)
    stop_loss_rate: float = 0.03    # Stop-loss threshold (3%)
    K: int = 5                      # Max hold days

    # Universe filter
    V: int = 500_000                # Minimum volume filter (shares)
    min_price: float = 1.00         # Minimum entry price (filters penny stocks / bankrupt OTC names)
    max_position_adv_pct: float = 0.10  # Max position size as % of T-1 volume (liquidity cap)

    # Date filter (ISO strings "YYYY-MM-DD"; None means no limit)
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Capital
    initial_capital: float = 500_000.0
    max_positions: int = 3

    # Paths
    data_path: str = "data/v3/prices.parquet"
    output_dir: str = ""            # Set by run.py at runtime

    # Runtime (set by run.py, not by user)
    run_id: str = ""

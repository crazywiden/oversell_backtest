"""
Adapter between the Streamlit UI and the backtesting engine.

Translates BacktestParams -> BacktestConfig, calls execute_run(), returns RunResult.
"""

import dataclasses
import time
from typing import Optional

from backtesting.config import BacktestConfig
from backtesting.run import execute_run


@dataclasses.dataclass
class BacktestParams:
    N: int = 20
    w1: float = -1.0
    w2: float = 1.0
    win_take_rate: float = 0.05
    stop_loss_rate: float = 0.03
    K: int = 5
    V: int = 500_000
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    data_path: str = "data/v3/prices.parquet"


@dataclasses.dataclass
class RunResult:
    run_id: str
    report_path: str
    config_path: str
    success: bool
    error_message: Optional[str] = None
    total_return_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    n_trades: Optional[int] = None
    duration_seconds: Optional[float] = None


def run_backtest(params: BacktestParams, progress_callback=None, status_callback=None) -> RunResult:
    """Run the backtesting engine with the given parameters."""
    config = BacktestConfig(
        N=params.N,
        w1=params.w1,
        w2=params.w2,
        win_take_rate=params.win_take_rate,
        stop_loss_rate=params.stop_loss_rate,
        K=params.K,
        V=params.V,
        start_date=params.start_date,
        end_date=params.end_date,
        data_path=params.data_path,
    )

    t0 = time.time()
    try:
        config_dict = execute_run(config, progress_callback=progress_callback, status_callback=status_callback)
    except Exception as exc:
        return RunResult(
            run_id="",
            report_path="",
            config_path="",
            success=False,
            error_message=str(exc),
            duration_seconds=round(time.time() - t0, 1),
        )

    duration = round(time.time() - t0, 1)
    run_id = config_dict["run_id"]
    run_dir = config_dict["output_dir"]
    metrics = config_dict.get("metrics", {})

    return RunResult(
        run_id=run_id,
        report_path=f"{run_dir}/report.html",
        config_path=f"{run_dir}/config.json",
        success=True,
        total_return_pct=metrics.get("total_return_pct"),
        sharpe_ratio=metrics.get("sharpe_ratio"),
        max_drawdown_pct=metrics.get("max_drawdown_pct"),
        n_trades=metrics.get("n_trades"),
        duration_seconds=duration,
    )

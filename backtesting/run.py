"""
Entry point for running a backtest.

Usage:
    python -m backtesting.run                  # uses default BacktestConfig
    python -m backtesting.run --N 30 --K 7    # override hyperparameters

Outputs to results/{run_id}/: config.json, trades.csv, portfolio.csv, report.html
"""

import argparse
import dataclasses
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from backtesting.config import BacktestConfig
from backtesting.data_loader import load_price_data
from backtesting.engine import run_backtest
from backtesting.signals import compute_os_scores
from results.report import compute_metrics, save_report

def _resolve_results_dir() -> Path:
    """Return a writable results directory, falling back to /tmp/results."""
    candidate = Path(__file__).resolve().parents[1] / "results"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write_probe"
        probe.touch()
        probe.unlink()
        return candidate
    except (PermissionError, OSError):
        fallback = Path("/tmp/results")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


RESULTS_DIR = _resolve_results_dir()


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def execute_run(config: BacktestConfig, progress_callback=None, status_callback=None) -> dict:
    """
    Full pipeline: load data -> compute signals -> run simulation -> save outputs.

    progress_callback(i, n, date, n_positions, n_trades) — called each simulation day.
    status_callback(message, fraction) — called at each pipeline phase transition.

    Returns config dict with metrics appended (same as config.json contents).
    """
    def _status(msg: str, pct: float) -> None:
        print(f"[{config.run_id}] {msg}")
        if status_callback is not None:
            status_callback(msg, pct)

    if not config.run_id:
        config.run_id = make_run_id()

    run_dir = RESULTS_DIR / config.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir = str(run_dir)

    _status(f"Loading data from {config.data_path}...", 0.05)
    df = load_price_data(config)

    _status(f"Computing OS scores (N={config.N}, w1={config.w1}, w2={config.w2})...", 0.15)
    df = compute_os_scores(df, config)

    n_tickers = df["ticker"].nunique()
    n_days = df["date"].nunique()
    _status(f"Simulating {n_tickers} tickers over {n_days} trading days...", 0.25)
    trades_df, portfolio_df = run_backtest(df, config, progress_callback=progress_callback)

    _status("Computing performance metrics...", 0.90)
    metrics = compute_metrics(portfolio_df, trades_df)
    print(
        f"[{config.run_id}] Done. "
        f"Trades: {metrics['n_trades']}, "
        f"Return: {metrics['total_return_pct']:.2f}%, "
        f"Sharpe: {metrics['sharpe_ratio']:.2f}, "
        f"MaxDD: {metrics['max_drawdown_pct']:.2f}%"
    )

    _status("Saving trades and portfolio CSV files...", 0.93)
    trades_df.to_csv(run_dir / "trades.csv", index=False)
    portfolio_df.to_csv(run_dir / "portfolio.csv", index=False)

    # Save config.json (flat dataclasses.asdict + metrics)
    config_dict = dataclasses.asdict(config)
    config_dict["metrics"] = metrics
    with open(run_dir / "config.json", "w") as f:
        json.dump(config_dict, f, indent=2)

    _status("Generating HTML report...", 0.96)
    save_report(
        run_id=config.run_id,
        config_dict=config_dict,
        metrics=metrics,
        trades_df=trades_df,
        portfolio_df=portfolio_df,
        output_dir=run_dir,
    )
    print(f"[{config.run_id}] Report: {run_dir / 'report.html'}")

    return config_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Run oversell backtest")
    parser.add_argument("--N", type=int, default=20, help="Lookback window (default: 20)")
    parser.add_argument("--w1", type=float, default=-1.0, help="Return weight (default: -1.0)")
    parser.add_argument("--w2", type=float, default=1.0, help="Volume weight (default: 1.0)")
    parser.add_argument("--win_take_rate", type=float, default=0.05, help="Take-profit rate")
    parser.add_argument("--stop_loss_rate", type=float, default=0.03, help="Stop-loss rate")
    parser.add_argument("--K", type=int, default=5, help="Max hold days (default: 5)")
    parser.add_argument("--V", type=int, default=500_000, help="Min volume filter")
    parser.add_argument("--data_path", type=str, default="data/v1/prices.csv")
    args = parser.parse_args()

    config = BacktestConfig(
        N=args.N,
        w1=args.w1,
        w2=args.w2,
        win_take_rate=args.win_take_rate,
        stop_loss_rate=args.stop_loss_rate,
        K=args.K,
        V=args.V,
        data_path=args.data_path,
    )
    execute_run(config)


if __name__ == "__main__":
    main()

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

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def execute_run(config: BacktestConfig) -> dict:
    """
    Full pipeline: load data -> compute signals -> run simulation -> save outputs.

    Returns config dict with metrics appended (same as config.json contents).
    """
    if not config.run_id:
        config.run_id = make_run_id()

    run_dir = RESULTS_DIR / config.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir = str(run_dir)

    print(f"[{config.run_id}] Loading data from {config.data_path}...")
    df = load_price_data(config)

    print(f"[{config.run_id}] Computing OS scores (N={config.N})...")
    df = compute_os_scores(df, config)

    print(f"[{config.run_id}] Running simulation...")
    trades_df, portfolio_df = run_backtest(df, config)

    metrics = compute_metrics(portfolio_df, trades_df)
    print(
        f"[{config.run_id}] Done. "
        f"Trades: {metrics['n_trades']}, "
        f"Return: {metrics['total_return_pct']:.2f}%, "
        f"Sharpe: {metrics['sharpe_ratio']:.2f}, "
        f"MaxDD: {metrics['max_drawdown_pct']:.2f}%"
    )

    # Save CSVs
    trades_df.to_csv(run_dir / "trades.csv", index=False)
    portfolio_df.to_csv(run_dir / "portfolio.csv", index=False)

    # Save config.json (flat dataclasses.asdict + metrics)
    config_dict = dataclasses.asdict(config)
    config_dict["metrics"] = metrics
    with open(run_dir / "config.json", "w") as f:
        json.dump(config_dict, f, indent=2)

    # Generate HTML report
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

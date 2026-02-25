# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Backtesting framework for oversell/oversold trading strategies in the U.S. stock market, targeting small funds ($100K–$10M AUM).

## Python Environment

Use `/Users/widen/Documents/helpful/code/helpful_venv/bin/python3` (Python 3.14, shared venv).

Key commands:
```bash
# Preprocess data (required before first run)
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 data/v1/preprocess.py --source fake

# Run backtest (default hyperparameters)
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 -m backtesting.run

# Run with custom hyperparameters
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 -m backtesting.run --N 30 --K 7 --w1 -1.5

# Launch Streamlit frontend (requires Python 3.12 — protobuf incompatible with 3.14)
# streamlit run frontend/app.py
```

**Note:** Streamlit requires Python ≤ 3.12 (protobuf's C extension breaks on 3.14). The backtesting engine and reporting work fully on 3.14.

## Custom Agents

Use these specialized subagents via the Task tool for appropriate work:

- **quant-researcher** — Strategy hypothesis, signal construction, backtesting pipeline, institutional-quality reports with equity curves, drawdown analysis, and robustness checks
- **stock-trader** — U.S. market rules, transaction cost modeling, slippage/market impact estimation
- **backend-planner** — Architecture design, code review, refactoring plans (read-only, produces design docs to `docs/claude_docs/`)
- **debugger** — Systematic root-cause analysis; adds/removes debug statements, never leaves debug code in codebase

## Backtesting Principles (Non-Negotiable)

- Always account for transaction costs, slippage, market impact, survivorship bias, and look-ahead bias
- Walk-forward / out-of-sample validation only — in-sample performance is not trusted
- Every strategy change requires economic rationale before implementation

## Code Conventions (Expected)

- Python with pandas, numpy, scipy, statsmodels, sklearn, matplotlib
- Separate concerns: data ingestion → signal generation → backtesting engine → analysis/reporting
- Use vectorized operations over loops

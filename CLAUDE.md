# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Backtesting framework for oversell/oversold trading strategies in the U.S. stock market, targeting small funds ($100K–$10M AUM).

## Python Environment

This project uses a dedicated virtual environment. Use the appropriate venv Python binary for running scripts rather than the system `python3`. Check for a `venv/` or similar directory at the repo root once it's created.

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

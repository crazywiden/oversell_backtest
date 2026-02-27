# Oversell Backtest

A backtesting framework for oversold mean-reversion trading strategies in the U.S. stock market, targeting small funds ($100K–$10M AUM).

## Strategy Overview

The strategy buys stocks that show extreme short-term overselling — large negative returns accompanied by high volume — and exits via take-profit, stop-loss, or a maximum hold-day limit.

**OS Score formula:**

```
OS_T = w1 * D(r)_T + w2 * D(v)_T
```

where:
- `D(r)_T` = signed z-score of absolute daily return over a rolling `N`-day window
- `D(v)_T` = z-score of daily volume over a rolling `N`-day window
- `w1 < 0` (negative return z-score signals oversell), `w2 > 0` (high volume confirms conviction)

Each day, the top-scoring stocks from the previous day (T-1) are bought at today's (T) close — no look-ahead bias.

---

## Architecture

```
data/raw/                    ← Real Sharadar CSVs (SHARADAR_SEP.csv, SHARADAR_TICKERS.csv)
data/fake_data/              ← Synthetic equivalents for development/testing
data/v1/preprocess.py        ← Step 1: raw/fake → data/v1/prices.csv
data/v1/prices.csv           ← Preprocessed price data (14 cols, sorted by ticker+date)

backtesting/
  config.py                  ← BacktestConfig dataclass (all hyperparameters)
  data_loader.py             ← Loads and validates prices.csv
  signals.py                 ← Computes D_r, D_v, os_score columns
  engine.py                  ← Day-by-day simulation (4-phase loop)
  run.py                     ← Orchestrates full pipeline; CLI entry point

results/
  report.py                  ← compute_metrics() + save_report() (Plotly HTML)
  {run_id}/                  ← One folder per run:
    config.json              ←   Hyperparameters + metrics
    trades.csv               ←   One row per closed trade
    portfolio.csv            ←   Daily cash / position value / returns
    report.html              ←   Interactive Plotly report

frontend/
  app.py                     ← Streamlit UI (requires Python ≤ 3.12)
  engine_bridge.py           ← Translates UI params → BacktestConfig → RunResult
```

### Simulation loop (engine.py)

Each trading day runs four phases in order:

1. **Increment** `days_held` for all open positions
2. **Check exits** — sequential priority: gap-down stop → gap-up TP → intraday TP → intraday SL → max hold
3. **New entries** — select top-`N` scorers from T-1 data, buy at today's close
4. **Snapshot** — record cash + mark-to-market portfolio value

---

## Hyperparameters

| Parameter | Default | Description |
|---|---|---|
| `N` | 20 | Rolling window for z-scores (trading days) |
| `w1` | -1.0 | Weight for return z-score `D(r)` |
| `w2` | 1.0 | Weight for volume z-score `D(v)` |
| `win_take_rate` | 0.05 | Take-profit threshold (5%) |
| `stop_loss_rate` | 0.03 | Stop-loss threshold (3%) |
| `K` | 5 | Max hold days before forced exit |
| `V` | 500,000 | Minimum daily volume filter (shares) |
| `initial_capital` | 500,000 | Starting capital ($) |
| `max_positions` | 3 | Maximum concurrent open positions |

---

## Quick Start

### 1. Prerequisites

The backtesting engine requires **Python 3.14** from the shared venv:

```
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3
```

The Streamlit frontend requires a separate **Python ≤ 3.12** installation (protobuf's C extension is incompatible with 3.14). A local `venv/` with Python 3.12 is included in the repo.

### 2. Preprocess data (run once)

```bash
# Using synthetic data (no Sharadar subscription needed):
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 data/v1/preprocess.py --source fake

# Using real Sharadar data (place CSVs in data/raw/ first):
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 data/v1/preprocess.py --source raw
```

This produces `data/v1/prices.csv`.

### 3. Run a backtest (CLI)

```bash
# Default hyperparameters:
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 -m backtesting.run

# Custom hyperparameters:
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 -m backtesting.run --N 30 --K 7 --w1 -1.5

# All options:
/Users/widen/Documents/helpful/code/helpful_venv/bin/python3 -m backtesting.run \
  --N 20 --w1 -1.0 --w2 1.0 \
  --win_take_rate 0.05 --stop_loss_rate 0.03 \
  --K 5 --V 500000
```

Results are written to `results/{run_id}/` (timestamped folder).

### 4. View the report

Open the generated HTML file in a browser:

```bash
open results/<run_id>/report.html
```

The report includes: equity curve, daily returns bar chart, key metrics (total return, Sharpe, max drawdown, trade count), and a sortable/filterable trades table.

### 5. Launch the Streamlit frontend (optional)

```bash
# Install Streamlit into the Python 3.12 venv (one-time):
venv/bin/pip install streamlit

# Launch:
venv/bin/python -m streamlit run frontend/app.py
```

Opens at `http://localhost:8501`. Use the form to configure parameters and click **Run Backtest**.

---

## Data

### Fake data (default)
Synthetic Sharadar-format CSVs in `data/fake_data/`. Suitable for development and testing without a data subscription.

### Real data (Sharadar)
Place the following files in `data/raw/` and run preprocess with `--source raw`:
- `SHARADAR_SEP.csv` — daily OHLCV prices
- `SHARADAR_TICKERS.csv` — ticker metadata (name, sector, industry, category)

The preprocessor filters to US common stocks, merges metadata, forward-fills trading halts, and outputs the 14-column `prices.csv`.

---

## Output Files

Each run produces a timestamped folder `results/YYYYMMDD_HHMMSS/`:

| File | Contents |
|---|---|
| `config.json` | All hyperparameters + final metrics |
| `trades.csv` | One row per closed trade (entry/exit prices, P&L, exit reason, signal scores) |
| `portfolio.csv` | Daily cash, position value, total value, daily/cumulative returns |
| `report.html` | Self-contained interactive report (no server needed) |

---

## Backtesting Principles

- **No look-ahead bias** — entry decisions use T-1 scores; fills execute at T close
- **Transaction costs / slippage** — model in `engine.py` before deploying live
- **Survivorship bias** — use `is_delisted` column; delisted positions are force-closed at entry price (conservative)
- **Walk-forward validation** — in-sample performance is not trusted; use out-of-sample periods
- **Economic rationale required** — every hyperparameter change should have a thesis

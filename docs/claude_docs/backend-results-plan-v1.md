# Backend Plan #3: Results Storage & Interactive HTML Report

**Author:** backend-planner (Designer mode)
**Date:** 2026-02-24
**Status:** Draft v1

---

## Summary & Context

This is the third and final backend plan for the oversell backtesting platform. It
covers how backtest results are persisted to disk and how an interactive HTML5 report
is generated from those results.

**Relevant repo files:**
- `CLAUDE.md` — project conventions
- `data/fake_data/generate_fake_sharadar.py` — establishes style (pathlib, numpy/pandas, lowercase columns, section comments)

**Inputs to this component** (produced by the backtesting engine):
1. `trades` DataFrame — one row per fill event (buy or sell)
2. `daily_portfolio` DataFrame — one row per trading day

---

## Goals

1. Persist every backtest run as a self-contained folder under `results/{run_id}/`.
2. Generate a single interactive HTML5 report that can be opened by double-clicking — no server, no build step.
3. Keep the implementation minimal: one Python module (`results/report.py`), under 400 lines total.

## Non-goals

- Multi-run comparison dashboards (future work).
- Database storage (CSV files are sufficient at this scale).
- PDF export (the HTML report is the sole deliverable).
- Serving the report via a web server.

---

## Proposed Folder Structure

```
results/
  {run_id}/                       # e.g. 20260115_143022
    config.json                   # hyperparameters for this run
    trades.csv                    # all fills (buys and sells)
    portfolio.csv                 # daily portfolio snapshot
    report.html                   # interactive HTML5 report
```

The `results/` directory lives at the repo root. Each `run_id` is a timestamp string
formatted as `YYYYMMDD_HHMMSS`, generated at the moment the backtest starts.

**Run ID generation (Python):**

```python
from datetime import datetime

def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
```

---

## config.json Schema

The config captures all hyperparameters so any run can be reproduced.

```json
{
  "run_id": "20260115_143022",
  "timestamp": "2026-01-15T14:30:22",
  "params": {
    "N": 20,
    "win_take_rate": 0.05,
    "stop_loss_rate": 0.03,
    "w1": -1.0,
    "w2": 1.0,
    "K": 5,
    "V": 500000
  },
  "data": {
    "start_date": "2016-01-01",
    "end_date": "2025-12-31",
    "universe": "SHARADAR_SEP",
    "initial_capital": 500000
  },
  "metrics": {
    "total_return_pct": 24.57,
    "annualized_sharpe": 1.34,
    "max_drawdown_pct": -8.42,
    "n_trades": 142
  }
}
```

---

## trades.csv Schema

| Column        | Type    | Description                                         | Present on |
|---------------|---------|-----------------------------------------------------|------------|
| date          | str     | Trade date (YYYY-MM-DD)                             | all rows   |
| ticker        | str     | Stock ticker symbol                                 | all rows   |
| company_name  | str     | Full company name                                   | all rows   |
| industry      | str     | Industry classification                             | all rows   |
| action        | str     | "buy" or "sell"                                     | all rows   |
| price         | float   | Fill price                                          | all rows   |
| shares        | int     | Number of shares                                    | all rows   |
| value         | float   | price * shares                                      | all rows   |
| r_prev        | float   | Return (r_{T-1}) at time of buy decision            | all rows   |
| v_prev        | float   | Volume (v_{T-1}) at time of buy decision            | all rows   |
| dr_prev       | float   | D(r)_{T-1} at time of buy decision                  | all rows   |
| dv_prev       | float   | D(v)_{T-1} at time of buy decision                  | all rows   |
| os_prev       | float   | OS_{T-1} at time of buy decision                    | all rows   |
| hold_days     | int/NaN | Trading days held (NaN for buys)                    | sells only |
| exit_type     | str/NaN | "stop_loss", "take_profit", or "max_hold"           | sells only |
| run_id        | str     | Run identifier                                      | all rows   |

---

## portfolio.csv Schema

| Column            | Type   | Description                              |
|-------------------|--------|------------------------------------------|
| date              | str    | Trading date (YYYY-MM-DD)                |
| cash              | float  | Cash balance at end of day               |
| position_value    | float  | Market value of open positions at close  |
| total_value       | float  | cash + position_value                    |
| daily_return      | float  | Day-over-day return as decimal           |
| cumulative_return | float  | Cumulative return from start as decimal  |

---

## HTML Report Structure

### ASCII Layout

```
+------------------------------------------------------------------+
|  OVERSELL BACKTEST REPORT           Run: 20260115_143022         |
+------------------------------------------------------------------+
|                                                                  |
|  +---------------------------+  +-----------------------------+  |
|  | Total Return    +24.5%    |  | Sharpe Ratio     1.42       |  |
|  +---------------------------+  +-----------------------------+  |
|  +---------------------------+                                   |
|  | Max Drawdown    -8.3%     |                                   |
|  +---------------------------+                                   |
|                                                                  |
+------------------------------------------------------------------+
|  Daily Return (%)                                    [plotly]    |
|  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |
|  |    .  .                                                  |    |
|  |  .   .. .    .       .  .                               |    |
|  |---.---------.------.----.-------------------------------|    |
|  |       .  .     .  .    .      .                         |    |
|  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |
+------------------------------------------------------------------+
|  Total Portfolio Value ($)                           [plotly]    |
|  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |
|  |                                              ___/        |    |
|  |                               ___/---___---/             |    |
|  |              ___/---___---__/                            |    |
|  | ___/---___/                                              |    |
|  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |
+------------------------------------------------------------------+
|  Trades                                                          |
|  Filter: [____ticker____] [__action__] [__exit_type__]          |
|                                                                  |
|  | Date  |Act |Ticker|Company    |Industry |Price|r|v|Dr|Dv|OS|H|E |
|  | 2016..|buy |AAPL  |Apple Inc  |ConsElec |182.5|..                |
|  | 2016..|sell|AAPL  |Apple Inc  |ConsElec |195.2|..  5|TP          |
|  +--------------------------------------------------------------+  |
+------------------------------------------------------------------+
|  Config: { collapsed JSON viewer }                               |
+------------------------------------------------------------------+
```

### HTML Architecture

The report is a single `.html` file using `string.Template` (`$placeholder` syntax)
to avoid conflicts with CSS/JS braces.

Key structure:
- Plotly.js loaded from CDN (`https://cdn.plot.ly/plotly-2.35.2.min.js`)
- Chart data embedded as JS variable assignments: `var spec = {JSON};`
- Trade table: server-side rendered `<tr>` rows with `data-ticker`, `data-action`, `data-exit` attributes
- Config shown in `<details><summary>` collapsible section
- ~40 lines of vanilla JS for table filtering + sorting

---

## How Plotly Charts Are Embedded

Python `plotly.graph_objects` builds figure dicts, then `fig.to_json()` serializes them.
The HTML template injects raw JSON as JavaScript variables:

```python
# In Python (report.py):
import plotly.graph_objects as go, json

def _build_daily_return_chart(portfolio_df):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=portfolio_df["date"].tolist(),
        y=(portfolio_df["daily_return"] * 100).tolist(),
        marker_color=[
            "#22c55e" if r >= 0 else "#ef4444"
            for r in portfolio_df["daily_return"]
        ],
    ))
    fig.update_layout(
        title="Daily Return (%)", template="plotly_dark", height=350,
        xaxis_title="Date", yaxis_ticksuffix="%",
    )
    return fig.to_json()
```

In the HTML template:
```javascript
var dailyReturnSpec = JSON.parse('__DAILY_RETURN_JSON__');
Plotly.newPlot('chart-daily-return', dailyReturnSpec.data, dailyReturnSpec.layout, {responsive: true});
```

Use sentinel `__PLACEHOLDER__` strings and `str.replace()` to avoid conflicts with
CSS braces in the template.

---

## How Trade Table Filtering Works

Each `<tr>` has `data-*` attributes:
```html
<tr data-ticker="AAPL" data-action="buy" data-exit="">
```

~40 lines of vanilla JS:
```javascript
function applyFilters() {
    var ticker = document.getElementById('filter-ticker').value.toUpperCase();
    var action = document.getElementById('filter-action').value;
    var exit = document.getElementById('filter-exit').value;
    var rows = document.querySelectorAll('#trades-table tbody tr');
    rows.forEach(function(row) {
        var show = true;
        if (ticker && row.dataset.ticker.indexOf(ticker) === -1) show = false;
        if (action && row.dataset.action !== action) show = false;
        if (exit && row.dataset.exit !== exit) show = false;
        row.style.display = show ? '' : 'none';
    });
}
```

---

## Key Python Functions (`results/report.py`)

```python
def make_run_id() -> str:
    """Generate YYYYMMDD_HHMMSS run ID."""

def save_run(run_id, config, trades_df, portfolio_df, results_dir=None) -> Path:
    """
    Orchestrator. Creates results/{run_id}/ folder and writes:
      config.json, trades.csv, portfolio.csv, report.html
    Returns: Path to run folder.
    """

def _compute_metrics(portfolio_df) -> dict:
    """Total return %, annualized Sharpe (rf=0), max drawdown %."""

def _build_daily_return_chart(portfolio_df) -> str:
    """Plotly bar chart JSON string."""

def _build_total_value_chart(portfolio_df) -> str:
    """Plotly scatter+area chart JSON string with initial capital reference line."""

def _render_trades_table(trades_df) -> str:
    """HTML <thead>+<tbody> string with data-* attributes on each <tr>."""

def _render_html(run_id, config, metrics, chart1_json, chart2_json, trades_html) -> str:
    """Assemble full HTML using string.Template with $placeholder syntax."""
```

### Metrics Computation

```python
def _compute_metrics(portfolio_df):
    daily_returns = portfolio_df["daily_return"]

    total_return_pct = round(portfolio_df["cumulative_return"].iloc[-1] * 100, 2)

    std = daily_returns.std()
    sharpe = round((daily_returns.mean() / std) * (252 ** 0.5), 2) if std > 0 else 0.0

    running_max = portfolio_df["total_value"].cummax()
    drawdown = (portfolio_df["total_value"] - running_max) / running_max
    max_dd_pct = round(drawdown.min() * 100, 2)

    return {
        "total_return_pct": total_return_pct,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd_pct,
    }
```

---

## File Organization

```
oversell_backtest/
  results/
    __init__.py          # empty
    report.py            # ~350 lines: all report generation logic + HTML template
  # gitignored run folders appear here:
  #   20260115_143022/
  #     config.json, trades.csv, portfolio.csv, report.html
```

**.gitignore entry:**
```
results/*/
```
This ignores all run subfolders but keeps `results/report.py` and `results/__init__.py` tracked.

---

## Alternatives Considered

### Alternative A: `fig.to_html(include_plotlyjs='cdn', full_html=True)` per chart
**Rejected.** Each call produces a complete `<html>` document; combining multiple charts into one page with metrics and a trade table requires parsing/stripping and produces multiple redundant `<script>` tags.

### Alternative B: Bundle plotly.js inline (no CDN)
**Rejected.** Adds ~3.5 MB to each report file. CDN is acceptable for local use.

### Alternative C: Jinja2 template engine
**Rejected.** Unnecessary dependency for a single file with ~10 placeholders. `string.Template` from stdlib is sufficient.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Plotly CDN goes down | Pin version. Fallback: `include_plotlyjs=True` for offline bundle |
| `{` `}` conflicts with CSS/JS in template | Use `string.Template` with `$placeholder` syntax |
| Large trade count (>5k rows) | Browser handles fine for this strategy's trade volume; add pagination in v2 if needed |

---

## Implementation Checklist

- [ ] Create `results/__init__.py` (empty)
- [ ] Create `results/report.py` with `make_run_id()` and all helper functions
- [ ] Implement `_compute_metrics()` — total return, Sharpe, max drawdown
- [ ] Implement `_build_daily_return_chart()` and `_build_total_value_chart()`
- [ ] Implement `_render_trades_table()` with proper HTML escaping and data-* attributes
- [ ] Write the `_HTML_TEMPLATE` string using `string.Template` ($-style placeholders)
- [ ] Implement `_render_html()` and `save_run()` orchestrator
- [ ] Add `results/*/` to `.gitignore`
- [ ] Add `plotly` to dependencies (requirements.txt)
- [ ] Smoke test: generate report with fake data, open in browser, verify charts + filtering

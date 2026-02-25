# Frontend Final Plan — Oversell Backtesting Platform

**Date:** 2026-02-24
**Status:** Final (consolidated from 3 draft plans)
**Source plans:**
- `docs/claude_docs/frontend-config-plan-v1.md` (Hyperparameter Config UI)
- `docs/claude_docs/frontend-visualization-plan-v1.md` (Results Visualization)
- `docs/claude_docs/frontend-architecture-plan-v1.md` (Overall Architecture)

---

## 1. Folder Structure

```
frontend/
    __init__.py         # empty
    app.py              # main Streamlit application
    engine_bridge.py    # adapter: translates UI params -> engine call
```

Run command: `streamlit run frontend/app.py`

---

## 2. Key Interfaces

### BacktestParams

```python
@dataclasses.dataclass
class BacktestParams:
    N: int = 20                    # Lookback window. Range: 5-100. Min: 5 (rolling window < 5 meaningless)
    w1: float = -1.0               # OS score weight for D(r). Range: -5.0-5.0
    w2: float = 1.0                # OS score weight for D(v). Range: -5.0-5.0
    win_take_rate: float = 0.05    # Take-profit (%). Range: 0.01-0.50
    stop_loss_rate: float = 0.03   # Stop-loss (%). Range: 0.01-0.50
    K: int = 5                     # Max hold days. Range: 1-30
    V: int = 500_000               # Min daily volume filter. Range: 0-10M
```

### RunResult

```python
@dataclasses.dataclass
class RunResult:
    run_id: str
    report_path: str
    config_path: str
    success: bool
    error_message: Optional[str] = None
    total_return_pct: Optional[float] = None   # aligned with backend config.json
    sharpe_ratio: Optional[float] = None       # aligned with backend config.json
    max_drawdown_pct: Optional[float] = None   # aligned with backend config.json
    n_trades: Optional[int] = None             # aligned with backend config.json
    duration_seconds: Optional[float] = None
```

**Note:** Metric keys match the backend `config.json` "metrics" block exactly:
`n_trades`, `total_return_pct`, `sharpe_ratio`, `max_drawdown_pct`.

---

## 3. Widget Mapping (7 hyperparameters)

| Hyperparameter | Widget | Default |
|---|---|---|
| N | `st.number_input(min_value=5, max_value=100, step=1)` | 20 |
| w1 | `st.number_input(min_value=-5.0, max_value=5.0, step=0.1)` | -1.0 |
| w2 | `st.number_input(min_value=-5.0, max_value=5.0, step=0.1)` | 1.0 |
| win_take_rate | `st.number_input(min_value=0.01, max_value=0.50, step=0.01)` | 0.05 |
| stop_loss_rate | `st.number_input(min_value=0.01, max_value=0.50, step=0.01)` | 0.03 |
| K | `st.number_input(min_value=1, max_value=30, step=1)` | 5 |
| V | `st.number_input(min_value=0, max_value=10000000, step=10000)` | 500000 |

All 7 inputs + Run button wrapped in one `st.form` (prevents re-runs on every keystroke).

---

## 4. UI Layout

```
+============================================================+
|  OVERSELL BACKTEST                                    v1.0  |
+============================================================+
|  --- Signal Construction ---                                |
|  N (lookback days)    [ 20 ]                               |
|  w1 (return weight)   [ -1.0 ]                             |
|  w2 (volume weight)   [  1.0 ]                             |
|                                                             |
|  --- Position Management ---                                |
|  win_take_rate (%)    [ 0.05 ]                             |
|  stop_loss_rate (%)   [ 0.03 ]                             |
|  K (max hold days)    [  5  ]                              |
|                                                             |
|  --- Universe Filter ---                                    |
|  V (min volume)       [ 500000 ]                           |
|                                                             |
|  [WARNING: stop_loss >= win_take: exits will all be SL]    | <- if triggered
|                                                             |
|  [ Run Backtest ]                                          |
|                                                             |
|  --- Results ---                                           |
|  [spinner: "Running backtest..."]                           |
|  OR after completion:                                       |
|  Total Return: +24.6%  Sharpe: 1.34  Max DD: -8.4%  Trades: 142
|  Report saved to:                                          |
|  results/20260224_143022/report.html  (open in browser)    |
+============================================================+
```

---

## 5. engine_bridge.py Responsibilities

`run_backtest(params: BacktestParams) -> RunResult` must:
1. Convert `BacktestParams` → `BacktestConfig` (direct field mapping)
2. Call `backtesting.run.execute_run(config)` which:
   - Loads preprocessed data
   - Computes OS scores
   - Runs simulation
   - Saves trades.csv, portfolio.csv, config.json
   - Generates report.html
3. Read `config.json["metrics"]` to populate `RunResult` metrics fields
4. Return `RunResult`

**IMPORTANT:** `backtesting/run.py` handles the full pipeline including calling `results.report.save_report()`. The bridge does NOT need to call report generation separately.

---

## 6. Report Display (v1)

v1 shows only the file path. No embedding (Plotly in iframe = slow/broken):

```python
st.success("Backtest complete.")
st.code(result.report_path)
st.caption("Open the path above in your browser to view the interactive report.")
```

---

## 7. Conflicts Resolved Between Plans

| Conflict | Resolution |
|---|---|
| N minimum: min=1 (plan #1) vs min=5 (plan #3) | **min=5 wins.** Rolling window < 5 is meaningless for z-score |
| Template sentinels: `$placeholder` vs `__PLACEHOLDER__` | **`__PLACEHOLDER__` wins.** Avoids conflicts with JS/CSS `{}` and `$` variable syntax |
| Report display: embedded iframe vs `st.code(path)` | **`st.code(path)` wins.** Plotly charts break in Streamlit iframes; path is cleaner for v1 |
| Past Runs table | **Deferred to v1.1.** Not needed to validate core backtest functionality |
| Metric keys: `annualized_sharpe` vs `sharpe_ratio` | **`sharpe_ratio` wins.** Matches backend `config.json` exactly |

---

## 8. Implementation Checklist

- [ ] Create `frontend/__init__.py` (empty)
- [ ] Create `frontend/engine_bridge.py`:
  - `BacktestParams` dataclass (7 fields)
  - `RunResult` dataclass
  - `run_backtest(params) -> RunResult` (real engine call)
- [ ] Create `frontend/app.py`:
  - `st.set_page_config` with title "Oversell Backtest"
  - `st.form` with 7 `st.number_input` widgets grouped into 3 sections
  - Cross-field warning if `stop_loss_rate >= win_take_rate`
  - `st.spinner` wrapping engine call
  - `st.session_state` for result persistence across reruns
  - `st.metric` row (Total Return, Sharpe, Max DD, Trades)
  - `st.code(report_path)` for report display
  - Error display via `st.error()` on failure
- [ ] Verify: `streamlit run frontend/app.py` launches without import errors
- [ ] Verify: clicking Run triggers engine call and displays metrics

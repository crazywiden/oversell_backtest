# Frontend Architecture Plan v1 — Oversell Backtesting Platform

**Date:** 2026-02-24
**Status:** Draft
**Author:** Frontend Planner

---

## 1. Summary and Context

This document defines the complete frontend architecture for the oversell backtesting platform. The frontend has one job: let a user configure 6 hyperparameters, run the backtesting engine, and view the generated report.

**Relevant repo files:**
- `data/fake_data/generate_fake_sharadar.py` — establishes Python/pandas project style
- `data/fake_data/SHARADAR_SEP.csv` — daily equity prices schema
- `CLAUDE.md` — project conventions

---

## 2. Goals and Non-Goals

### Goals
- Single-file or minimal-file Python frontend
- Form with 6 hyperparameters (N, win_take_rate, stop_loss_rate, w1, w2, K, V), validation, and sensible defaults
- Run the backtesting engine and show progress
- Display a link to the generated HTML report
- List past backtest runs
- Single command to start: `streamlit run frontend/app.py`

### Non-Goals
- No JavaScript framework (no React, no Vue, no npm)
- No REST API layer (no Flask, no FastAPI)
- No database
- No authentication or deployment/Docker (local-only)
- No real-time streaming of engine internals (v1)

---

## 3. Technology Choice: Streamlit

### Decision: Streamlit (Option A — direct Python function call)

**Rationale:**

| Option | Complexity | Files | HTTP layer | Progress | Verdict |
|--------|-----------|-------|------------|----------|---------|
| A. Streamlit | Lowest | 1-2 .py files | None (same process) | `st.spinner` | **CHOSEN** |
| B. Flask + HTML | Medium | 3-5 files | Yes (HTTP) | JS polling or SSE | Over-engineered |
| C. FastAPI + HTML | Medium-High | 4-6 files | Yes (HTTP) | WebSocket | Over-engineered |
| D. Pure HTML + subprocess | Low-Medium | 2-3 files | CGI-style | Manual | Fragile |

**Why Streamlit wins:**
1. Zero HTTP layer — Streamlit calls Python functions directly. No API design, no request/response serialization, no CORS.
2. Built-in form widgets — `st.number_input`, `st.slider`, `st.form` map 1:1 to the hyperparameters.
3. Built-in progress — `st.spinner` handles the loading state natively.
4. Single command — `streamlit run frontend/app.py`.
5. Python only — no HTML templates, no CSS files, no JS bundling.
6. Consistent with pandas/numpy/matplotlib stack from CLAUDE.md.

**Risks and mitigations:**
- Streamlit reruns the entire script on every interaction → use `st.form` to batch inputs, `st.session_state` to persist results.
- Long backtests block the Streamlit thread → `st.spinner` sufficient for v1; upgrade to `st.status` with callbacks in future.

---

## 4. Folder Structure

```
frontend/
    app.py              # Main Streamlit application (single entry point)
    engine_bridge.py    # Thin adapter: translates UI params -> engine call
    __init__.py         # empty, makes frontend/ importable
```

Three files. `app.py` handles all UI. `engine_bridge.py` isolates the coupling between frontend and backtesting engine.

### Why `engine_bridge.py` exists

The backtesting engine does not exist yet. By routing all engine calls through `engine_bridge.py`, we create a single seam:
- During development: returns mock data
- After engine is built: update only `engine_bridge.py`

---

## 5. Data Flow Diagram

```
+------------------------------------------------------------------+
|                        STREAMLIT PROCESS                         |
|                                                                  |
|  +--------------------+      +-------------------+               |
|  |     app.py         |      | engine_bridge.py  |               |
|  |                    |      |                   |               |
|  |  [Hyperparameter   | (1)  |  run_backtest(    |               |
|  |   Form]            |----->|    params: dict   |               |
|  |                    |      |  ) -> RunResult   |               |
|  |  [Run Backtest]    |      |                   |               |
|  |   button           |      |  Calls:           |               |
|  |                    |      |  backtesting/      |               |
|  |  st.spinner(...)   | (2)  |  engine.run(...)  |               |
|  |  "Running..."      |<-----|  (direct import)  |               |
|  |                    |      |                   |               |
|  |  [Report Link]     | (3)  |  Returns:         |               |
|  |  [Metrics Summary] |<-----|  RunResult        |               |
|  |                    |      |                   |               |
|  |  [Past Runs Table] |      |                   |               |
|  +--------------------+      +-------------------+               |
|                                       |                          |
+---------------------------------------|---------------------------+
                                        |
                                        | (direct function call)
                                        v
                              +-------------------+
                              | backtesting/      |
                              | engine.py         |
                              |                   |
                              | Reads: data/      |
                              | Writes: results/  |
                              |   {run_id}/       |
                              |     config.json   |
                              |     trades.csv    |
                              |     portfolio.csv |
                              |     report.html   |
                              +-------------------+
```

---

## 6. Interface Definitions

### BacktestParams

```python
@dataclasses.dataclass
class BacktestParams:
    N: int                 # Lookback window. Range: 5-60. Default: 20
    win_take_rate: float   # Take-profit (%). Range: 0.01-0.50. Default: 0.05
    stop_loss_rate: float  # Stop-loss (%). Range: 0.01-0.50. Default: 0.03
    w1: float              # OS score weight for D(r). Range: -5.0-5.0. Default: -1.0
    w2: float              # OS score weight for D(v). Range: -5.0-5.0. Default: 1.0
    K: int                 # Max hold days. Range: 1-30. Default: 5
    V: int                 # Min daily volume filter. Range: 0-10M. Default: 500000
```

### RunResult

```python
@dataclasses.dataclass
class RunResult:
    run_id: str
    report_path: str
    config_path: str
    success: bool
    error_message: Optional[str]
    total_return: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    total_trades: Optional[int]
    duration_seconds: Optional[float]
```

### Expected config.json format (contract with engine)

```json
{
    "run_id": "20260224_143052",
    "timestamp": "2026-02-24T14:30:52",
    "params": {
        "N": 20, "win_take_rate": 0.05, "stop_loss_rate": 0.03,
        "w1": -1.0, "w2": 1.0, "K": 5, "V": 500000
    },
    "metrics": {
        "total_return": 0.152,
        "sharpe_ratio": 1.34,
        "max_drawdown": -0.087,
        "total_trades": 142
    }
}
```

---

## 7. UI Layout (ASCII Wireframe)

```
+============================================================+
|  OVERSELL BACKTEST                                    v1.0  |
+============================================================+
|                                                             |
|  --- Signal Construction ---                                |
|  N (lookback days)    [===slider===] 20                     |
|  w1 (return weight)   [  -1.0  ]                           |
|  w2 (volume weight)   [   1.0  ]                           |
|                                                             |
|  --- Position Management ---                                |
|  win_take_rate (%)    [===slider===] 5%                     |
|  stop_loss_rate (%)   [===slider===] 3%                     |
|  K (max hold days)    [===slider===] 5                      |
|                                                             |
|  --- Universe Filter ---                                    |
|  V (min volume)       [ 500000 ]                           |
|                                                             |
|  [ Run Backtest ]                                          |
|                                                             |
|  --- Results ---                                           |
|  [spinner: "Running backtest..."]                           |
|  OR after completion:                                       |
|  Return: +15.2%   Sharpe: 1.34   MaxDD: -8.7%              |
|  Trades: 47    Duration: 12.3s                              |
|  [Open Full Report: results/20260224_143022/report.html]    |
|                                                             |
|  --- Past Runs ---                                         |
|  Run ID    | Return | Sharpe | DD    | Report               |
|  20260224  | +15.2% |  1.34  | -8.7% | [View]              |
|  20260223  | +8.1%  |  0.92  | -12%  | [View]              |
+============================================================+
```

### Widget Mapping

| Hyperparameter | Widget | Default |
|---|---|---|
| N | `st.number_input(min=5, max=100, step=1)` | 20 |
| w1 | `st.number_input(min=-5.0, max=5.0, step=0.1)` | -1.0 |
| w2 | `st.number_input(min=-5.0, max=5.0, step=0.1)` | 1.0 |
| win_take_rate | `st.number_input(min=0.01, max=0.50, step=0.01)` | 0.05 |
| stop_loss_rate | `st.number_input(min=0.01, max=0.50, step=0.01)` | 0.03 |
| K | `st.number_input(min=1, max=30, step=1)` | 5 |
| V | `st.number_input(min=0, max=10000000, step=10000)` | 500000 |

---

## 8. Key Implementation Details

### Form batching with `st.form`
All 7 inputs and the Run button are inside one `st.form`. Engine only runs on explicit click.

### Loading state
```python
if submitted:
    with st.spinner("Running backtest..."):
        result = engine_bridge.run_backtest(params)
```

### Session state persistence
```python
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    # render metrics, report link
```

### Viewing the HTML report
Use `streamlit.components.v1.html()` to embed the self-contained HTML:
```python
import streamlit.components.v1 as components
with open(result.report_path) as f:
    components.html(f.read(), height=800, scrolling=True)
```

### Past runs listing
Scan `results/` for subdirectories, read `config.json` from each, display as `st.dataframe` sorted by recency.

---

## 9. Mock Mode (Development Before Engine Exists)

`engine_bridge.py` ships with a mock that simulates a 3-second backtest and writes fake `config.json` + `report.html` to `results/{run_id}/`.

```python
def run_backtest(params: BacktestParams) -> RunResult:
    # TODO: replace body with real engine call when backtesting/ is built
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("results") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    time.sleep(3)  # Simulate work
    # Write mock config.json and report.html ...
    return RunResult(run_id=run_id, success=True, total_return=0.152, ...)
```

---

## 10. Run Command

```bash
streamlit run frontend/app.py
```

Opens browser at `http://localhost:8501`. No build step. No compile step.

---

## 11. Dependencies

```
streamlit>=1.30.0
```

Only one new dependency. No Node.js, no npm.

---

## 12. Error Handling

| Scenario | UI Response |
|---|---|
| Engine raises exception | `st.error(f"Backtest failed: {msg}")` |
| results/ folder missing | "No past runs found." |
| report.html missing | Show run in table, disable View link |
| w1 + w2 unusual values | `st.warning()` — informational only |

---

## 13. Implementation Checklist

- [ ] Create `frontend/__init__.py` (empty)
- [ ] Create `frontend/engine_bridge.py` with `BacktestParams`, `RunResult` dataclasses and mock `run_backtest()`
- [ ] Create `frontend/app.py` with:
  - [ ] `st.set_page_config` with title
  - [ ] `st.form` with all 7 `st.number_input` widgets
  - [ ] Cross-field warning if `stop_loss_rate >= win_take_rate`
  - [ ] `st.spinner` wrapping engine call
  - [ ] `st.session_state` for result persistence
  - [ ] `st.metric` row showing 4 key metrics
  - [ ] `components.html()` embedding the report
  - [ ] Past runs `st.dataframe`
- [ ] Test: `streamlit run frontend/app.py` launches without errors
- [ ] Test: 3-second mock run completes and shows metrics
- [ ] Replace mock with real engine call when `backtesting/` is built

---

## 14. Engine Integration Contracts (Blockers for Real Use)

| Contract | Description |
|---|---|
| `results/{run_id}/config.json` format | Must match schema in Section 6 |
| `results/{run_id}/report.html` | Must be self-contained single HTML file |
| Callable Python function | Engine must expose `run_backtest(config_dict)` or equivalent |
| All 7 hyperparameters accepted | Engine must accept N, win_take_rate, stop_loss_rate, w1, w2, K, V |

All contracts are covered by mock mode until real engine is built.

# Frontend Plan v1: Hyperparameter Configuration Panel

**Date:** 2026-02-24
**Status:** DRAFT
**Scope:** Frontend plan #1 of 3 — config panel only (results display and report viewer are separate plans)

---

## 1. Technology Choice: Streamlit

**Decision:** Streamlit (pure Python, single-file app)

**Rationale:**

| Option              | Pros                           | Cons                                     |
|---------------------|--------------------------------|------------------------------------------|
| Streamlit           | Zero JS, built-in widgets, spinner, single command | Opinionated layout, less customizable    |
| Flask + HTML form   | Full control over HTML         | Requires templates, static files, JS for loading state |
| Single HTML + API   | Fully decoupled frontend       | Two processes, CORS, manual JS/fetch     |

Streamlit wins because:
- The entire project is Python. No reason to introduce a second language.
- `st.number_input`, `st.slider`, `st.spinner`, `st.success` cover every requirement out of the box.
- The backtesting engine (Python function) can be called **in-process** — no HTTP API needed.
- One dependency added: `streamlit`. No build step. Run command: `streamlit run frontend/app.py`.
- Loading state (spinner while backtest runs) is a single `with st.spinner():` block.

**Rejected alternatives:**
- Flask: Would require writing HTML templates, JavaScript for the loading spinner, and a separate API endpoint. More moving parts for identical functionality.
- Single HTML: Would require two processes (static server + API server), CORS configuration, and hand-written fetch/XHR code. Over-engineered for this use case.

---

## 2. ASCII Layout

```
+================================================================+
|                  OVERSELL BACKTEST CONFIGURATOR                  |
+================================================================+
|                                                                  |
|  --- Signal Construction ---                                     |
|                                                                  |
|  N (Rolling Window Days)          [===== 20 =====]  (1..100)    |
|  Rolling lookback for D(r) and D(v) percentile computation      |
|                                                                  |
|  w1 (Return Deviation Weight)     [  -1.0  ]        (-5..5)     |
|  OS score weight for D(r). Negative = oversold when returns drop |
|                                                                  |
|  w2 (Volume Deviation Weight)     [   1.0  ]        (-5..5)     |
|  OS score weight for D(v). Positive = oversold on volume spikes  |
|                                                                  |
|  --- Position Management ---                                     |
|                                                                  |
|  win_take_rate (Take Profit %)    [===== 0.05 =====] (0.01..0.5)|
|  Exit when price rises this fraction above entry (e.g. 0.05=5%) |
|                                                                  |
|  stop_loss_rate (Stop Loss %)     [===== 0.03 =====] (0.01..0.5)|
|  Exit when price falls this fraction below entry (e.g. 0.03=3%) |
|                                                                  |
|  K (Max Hold Days)                [===== 5 ======]   (1..30)    |
|  Force-close position after this many trading days               |
|                                                                  |
|  --- Universe Filter ---                                         |
|                                                                  |
|  V (Min Daily Volume)             [ 500000 ]         (0..10M)   |
|  Exclude stocks with avg daily volume below this threshold       |
|                                                                  |
|  +----------------------------------------------------------+   |
|  |              [ >>> RUN BACKTEST <<< ]                     |   |
|  +----------------------------------------------------------+   |
|                                                                  |
|  (after click, this area shows:)                                 |
|  [SPINNER] Running backtest... (N=20, K=5, ...)                  |
|                                                                  |
|  (after completion:)                                             |
|  [SUCCESS] Backtest complete. 142 trades, Sharpe 1.34            |
|  [LINK] View Full Report: results/20260224_143022/report.html    |
|                                                                  |
+================================================================+
```

---

## 3. Hyperparameter Definitions

All 7 hyperparameters with their input specifications:

### 3a. Signal Construction Group

| Parameter | Label                     | Type    | Widget         | Default | Min   | Max   | Step  | Description                                                          |
|-----------|---------------------------|---------|----------------|---------|-------|-------|-------|----------------------------------------------------------------------|
| `N`       | Rolling Window Days       | `int`   | `number_input` | 20      | 1     | 100   | 1     | Rolling lookback window for D(r) and D(v) percentile computation     |
| `w1`      | Return Deviation Weight   | `float` | `number_input` | -1.0    | -5.0  | 5.0   | 0.1   | OS score weight for D(r). Negative means oversold on return drops    |
| `w2`      | Volume Deviation Weight   | `float` | `number_input` | 1.0     | -5.0  | 5.0   | 0.1   | OS score weight for D(v). Positive means oversold on volume spikes   |

### 3b. Position Management Group

| Parameter        | Label             | Type    | Widget         | Default | Min   | Max  | Step  | Description                                                     |
|------------------|-------------------|---------|----------------|---------|-------|------|-------|-----------------------------------------------------------------|
| `win_take_rate`  | Take Profit Rate  | `float` | `number_input` | 0.05    | 0.01  | 0.50 | 0.01  | Exit when price rises this fraction above entry (0.05 = 5%)    |
| `stop_loss_rate` | Stop Loss Rate    | `float` | `number_input` | 0.03    | 0.01  | 0.50 | 0.01  | Exit when price drops this fraction below entry (0.03 = 3%)    |
| `K`              | Max Hold Days     | `int`   | `number_input` | 5       | 1     | 30   | 1     | Force-close position after this many trading days               |

### 3c. Universe Filter Group

| Parameter | Label            | Type  | Widget         | Default  | Min | Max       | Step   | Description                                                     |
|-----------|------------------|-------|----------------|----------|-----|-----------|--------|-----------------------------------------------------------------|
| `V`       | Min Daily Volume | `int` | `number_input` | 500000   | 0   | 10000000  | 10000  | Exclude stocks with average daily volume below this threshold   |

---

## 4. Validation Approach

Streamlit's `st.number_input` enforces type and range constraints at the widget level. No separate validation code needed for basic checks. Additional validation:

1. **Widget-level (automatic):** `min_value`, `max_value`, and `step` parameters prevent out-of-range entries.
2. **Cross-field validation (manual):** Before running the backtest, one sanity check:
   - `stop_loss_rate` should be less than `win_take_rate` — warn (not block) using `st.warning()`.
3. **Config dict construction:** All 7 values collected into a single Python dict before being passed to the engine.

```python
config = {
    "N": n_val,
    "win_take_rate": win_take_rate_val,
    "stop_loss_rate": stop_loss_rate_val,
    "w1": w1_val,
    "w2": w2_val,
    "K": k_val,
    "V": v_val,
}
```

---

## 5. Run Button and Loading State

### Flow

```
[User clicks "Run Backtest"]
        |
        v
[st.spinner("Running backtest with N={N}, K={K}...")]
        |
        v
[Call: run_backtest(config) -> returns result dict]
        |
        +---> On success:
        |       st.success("Backtest complete. {n_trades} trades, Sharpe {sharpe:.2f}")
        |       st.code("results/{run_id}/report.html")   # path for user to open
        |
        +---> On error:
                st.error("Backtest failed: {error_message}")
```

### Expected Return Schema from Engine

```python
# run_backtest(config) must return:
{
    "success": True,
    "run_id": "20260224_143022",
    "report_path": "results/20260224_143022/report.html",
    "summary": {
        "n_trades": 142,
        "sharpe_ratio": 1.34,
        "max_drawdown": -0.087,
        "total_return": 0.156,
    },
}
```

### Report Link Behavior

v1: Display file path via `st.code(report_path)` so user can copy-paste and open locally.
(No need to embed the report in-app for v1.)

---

## 6. File Structure

```
oversell_backtest/
    frontend/
        app.py              # Streamlit app (single file, ~80-120 lines)
    results/                # Generated run folders land here
        .gitkeep
```

---

## 7. Backend Contract (BLOCKER)

The backtesting engine function must implement this signature:

```python
def run_backtest(config: dict) -> dict:
    """
    Parameters: config dict with keys N, win_take_rate, stop_loss_rate, w1, w2, K, V
    Returns: dict with success(bool), run_id(str), report_path(str), summary(dict)
    """
```

Until the engine exists, the frontend ships with a stub (clearly marked `# TODO: replace`).

---

## 8. Dependencies

```
streamlit>=1.30.0
```

No other frontend dependencies. No Node.js, no npm, no build tools.

---

## 9. Implementation Checklist

- [ ] Create `frontend/` directory
- [ ] Write `frontend/app.py` with:
  - [ ] Page config (title, centered layout)
  - [ ] Title and brief description
  - [ ] Three `st.subheader` groups: Signal Construction, Position Management, Universe Filter
  - [ ] Seven `st.number_input` widgets with labels, defaults, ranges, steps, `help=` tooltips
  - [ ] Cross-field warning if `stop_loss_rate >= win_take_rate`
  - [ ] Config dict assembly
  - [ ] "Run Backtest" button (`type="primary"`)
  - [ ] `st.spinner` wrapper around engine call
  - [ ] Stub `run_backtest()` clearly marked `# TODO: replace with real engine`
  - [ ] Success state: `st.success` + `st.metric` row + report path display
  - [ ] Error state: `st.error` with message
- [ ] Test: `streamlit run frontend/app.py` launches without errors
- [ ] Replace stub with real engine call once backtesting module is built

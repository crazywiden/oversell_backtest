# Backend Final Plan — Oversell Backtesting Platform

**Date:** 2026-02-24
**Status:** Final (consolidated from 3 draft plans)
**Source plans:**
- `docs/claude_docs/backend-data-plan-v1.md` (Data Pipeline)
- `docs/claude_docs/backend-engine-plan-v1.md` (Backtesting Engine)
- `docs/claude_docs/backend-results-plan-v1.md` (Results & Reporting)

---

## 1. Complete Folder Structure

```
oversell_backtest/
  data/
    raw/                            # User drops real Sharadar CSVs here (gitignored)
      .gitkeep
    fake_data/                      # Already exists, tracked in git
      generate_fake_sharadar.py
      SHARADAR_SEP.csv
      SHARADAR_TICKERS.csv
    v1/
      preprocess.py                 # Standalone preprocessing script
      prices.csv                    # OUTPUT (gitignored)
  backtesting/
    __init__.py                     # Exports BacktestConfig, run_backtest
    config.py                       # BacktestConfig dataclass
    data_loader.py                  # Load and validate prices.csv
    signals.py                      # Vectorized OS score computation
    engine.py                       # Day-by-day simulation loop + exit logic
    run.py                          # Entry point: orchestrates full pipeline
  results/
    __init__.py                     # Empty
    report.py                       # Metrics computation + HTML report generation
  .gitignore                        # Repo root
```

**Run output folders** (created at runtime, gitignored):

```
results/
  {run_id}/                         # e.g. 20260224_143022
    config.json
    trades.csv
    portfolio.csv
    report.html
```

---

## 2. File List with Purpose

| File | Purpose |
|---|---|
| `data/v1/preprocess.py` | Reads raw Sharadar CSVs, filters to US common stocks (incl. delisted), merges metadata, forward-fills close, outputs `prices.csv` |
| `backtesting/__init__.py` | Exports `BacktestConfig` and `run_backtest` |
| `backtesting/config.py` | `BacktestConfig` dataclass — all hyperparameters, paths, capital settings |
| `backtesting/data_loader.py` | `load_price_data(config)` — reads `prices.csv`, validates, returns DataFrame |
| `backtesting/signals.py` | `compute_os_scores(df, config)` — vectorized OS score computation |
| `backtesting/engine.py` | `Position` dataclass, `check_exit()`, `run_backtest()` — day-by-day simulation |
| `backtesting/run.py` | Generates run_id, calls data_loader → signals → engine → saves CSVs → calls report |
| `results/__init__.py` | Empty |
| `results/report.py` | `save_report(...)` — generates interactive HTML report |

---

## 3. .gitignore (repo root)

```
data/raw/*.csv
data/v1/prices.csv
results/*/
```

---

## 4. Key Interfaces

### 4a. BacktestConfig (backtesting/config.py)

```python
@dataclasses.dataclass
class BacktestConfig:
    # Signal hyperparameters
    N: int = 20                     # Rolling window for z-scores (trading days)
    w1: float = -1.0                # Weight for return z-score D(r)
    w2: float = 1.0                 # Weight for volume z-score D(v)

    # Exit hyperparameters
    win_take_rate: float = 0.05     # Take-profit threshold (5%)
    stop_loss_rate: float = 0.03    # Stop-loss threshold (3%)
    K: int = 5                      # Max hold days

    # Universe filter
    V: int = 500_000                # Minimum volume filter (shares)

    # Capital
    initial_capital: float = 500_000.0
    max_positions: int = 3

    # Paths
    data_path: str = "data/v1/prices.csv"
    output_dir: str = ""            # Set by run.py at runtime

    # Runtime (set by run.py, not by user)
    run_id: str = ""
```

### 4b. config.json (saved per run)

Flat `dataclasses.asdict(config)` plus `metrics` appended after simulation:

```json
{
  "N": 20,
  "w1": -1.0,
  "w2": 1.0,
  "win_take_rate": 0.05,
  "stop_loss_rate": 0.03,
  "K": 5,
  "V": 500000,
  "initial_capital": 500000.0,
  "max_positions": 3,
  "data_path": "data/v1/prices.csv",
  "output_dir": "results/20260224_143022",
  "run_id": "20260224_143022",
  "metrics": {
    "n_trades": 142,
    "total_return_pct": 24.57,
    "sharpe_ratio": 1.34,
    "max_drawdown_pct": -8.42
  }
}
```

### 4c. trades.csv columns (one row per completed trade)

| Column | Type | Description |
|---|---|---|
| `ticker` | str | Stock ticker symbol |
| `company_name` | str | Full company name |
| `industry` | str | Industry classification |
| `entry_date` | str | Date position opened (YYYY-MM-DD) |
| `entry_price` | float | Close price on entry day |
| `exit_date` | str | Date position closed (YYYY-MM-DD) |
| `exit_price` | float | Fill price at exit |
| `shares` | int | Number of shares held |
| `pnl` | float | (exit_price - entry_price) * shares |
| `pnl_pct` | float | exit_price / entry_price - 1 |
| `exit_reason` | str | `gap_down_stop` \| `gap_up_tp` \| `intraday_tp` \| `intraday_sl` \| `max_hold` \| `forced_close` |
| `days_held` | int | Trading days held |
| `r_prev` | float | r at T-1 (return on signal day) |
| `v_prev` | float | Volume at T-1 |
| `dr_prev` | float | D(r)_{T-1} z-score |
| `dv_prev` | float | D(v)_{T-1} z-score |
| `os_prev` | float | OS_{T-1} score |

### 4d. portfolio.csv columns

| Column | Type | Description |
|---|---|---|
| `date` | str | Trading date (YYYY-MM-DD) |
| `cash` | float | Cash balance at end of day |
| `position_value` | float | Mark-to-market value of open positions at close |
| `total_value` | float | cash + position_value |
| `daily_return` | float | Day-over-day return as decimal |
| `cumulative_return` | float | Cumulative return from start as decimal |

### 4e. prices.csv columns (output of preprocess.py)

| Column | Type | Description |
|---|---|---|
| `ticker` | str | Stock ticker symbol |
| `date` | str (YYYY-MM-DD) | Trading date |
| `open` | float | Adjusted open price |
| `high` | float | Adjusted high price |
| `low` | float | Adjusted low price |
| `close` | float | Adjusted close price |
| `volume` | int | Daily volume |
| `dividends` | float | Dividend per share on ex-date (0.0 otherwise) |
| `name` | str | Company name |
| `sector` | str | Sector |
| `industry` | str | Industry |
| `is_delisted` | bool | True if ticker is delisted |
| `close_ffill` | float | Forward-filled close (fills gaps from halts) |
| `is_halt` | bool | True if close was NaN and was forward-filled |

---

## 5. OS Score Formula (exact pseudocode)

```python
def compute_os_scores(df: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    N, w1, w2 = config.N, config.w1, config.w2
    df = df.sort_values(['ticker', 'date']).reset_index(drop=True)

    # Step 1: Daily return per ticker (first row per ticker = NaN)
    df['r'] = df.groupby('ticker')['close'].pct_change()

    # Step 2: Signed z-score of absolute return
    #   D(r)_T = sign(r_T) * (|r_T| - rolling_mean(|r|, N)) / rolling_std(|r|, N)
    df['D_r'] = df.groupby('ticker')['r'].transform(
        lambda x: np.sign(x) * (x.abs() - x.abs().rolling(N).mean()) / x.abs().rolling(N).std()
    )

    # Step 3: Volume z-score
    #   D(v)_T = (volume_T - rolling_mean(volume, N)) / rolling_std(volume, N)
    df['D_v'] = df.groupby('ticker')['volume'].transform(
        lambda x: (x - x.rolling(N).mean()) / x.rolling(N).std()
    )

    # Step 4: Combined OS score
    #   OS_T = w1 * D(r)_T + w2 * D(v)_T
    #   Default: w1=-1.0, w2=1.0 -> high OS = large negative return + high volume = oversold
    df['os_score'] = w1 * df['D_r'] + w2 * df['D_v']

    return df
```

**Key details:**
- First N rows per ticker have NaN os_score. Engine skips these.
- Division by zero (std=0) produces NaN os_score. Stock safely excluded.
- `w1 = -1.0` → large negative return (oversold) produces large positive OS score.

---

## 6. Exit Logic (exact pseudocode with correct phase ordering)

### 6a. Position dataclass

```python
@dataclasses.dataclass
class Position:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float          # Close price on entry day
    shares: int
    cost_basis: float           # entry_price * shares
    days_held: int = 0          # 0 on entry day, incremented each subsequent day
    r_prev: float = 0.0        # Factor scores at time of buy decision (T-1 data)
    v_prev: float = 0.0
    dr_prev: float = 0.0
    dv_prev: float = 0.0
    os_prev: float = 0.0
    company_name: str = ""
    industry: str = ""
```

### 6b. Sequential exit check

```python
def check_exit(pos: Position, row: pd.Series, config: BacktestConfig) -> tuple[bool, float, str]:
    """
    Returns: (should_exit, fill_price, exit_reason)

    Sequential priority:
      1. Gap-down stop:  open <= entry * (1 - SL)  -> fill at open
      2. Gap-up TP:      open >= entry * (1 + TP)  -> fill at open
      3. Intraday TP:    high >= entry * (1 + TP)  -> fill at limit price
      4. Intraday SL:    low  <= entry * (1 - SL)  -> fill at limit price
         BOTH 3 & 4 trigger on same bar -> TP wins (check high before low)
      5. Max hold:       days_held >= K             -> fill at close
    """
    p = pos.entry_price
    tp_price = p * (1 + config.win_take_rate)
    sl_price = p * (1 - config.stop_loss_rate)
    o, h, l, c = row['open'], row['high'], row['low'], row['close']

    if o <= sl_price:
        return True, o, 'gap_down_stop'
    if o >= tp_price:
        return True, o, 'gap_up_tp'
    if h >= tp_price:           # TP checked before SL -> TP wins ties
        return True, tp_price, 'intraday_tp'
    if l <= sl_price:
        return True, sl_price, 'intraday_sl'
    if pos.days_held >= config.K:
        return True, c, 'max_hold'

    return False, 0.0, ''
```

### 6c. Phase ordering (CRITICAL — per trading day)

```
For each trading day T:
    PHASE 1: INCREMENT days_held for all existing positions (pos.days_held += 1)
    PHASE 2: CHECK EXITS on positions where days_held >= 1
    PHASE 3: SELECT NEW ENTRIES from T-1 scores, buy at T close (days_held = 0)
    PHASE 4: RECORD DAILY SNAPSHOT (cash + mark-to-market)
```

**Why this order is correct:**
Entry day: position created with `days_held = 0`.
Next day (T+1): Phase 1 increments to `days_held = 1`, Phase 2 can now exit.
This correctly enforces "can only sell the day after buying."
If increment came AFTER exit check, first exit would be T+2 (off-by-one bug).

---

## 7. Main Simulation Loop (pseudocode)

```python
def run_backtest(df: pd.DataFrame, config: BacktestConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = sorted(df['date'].unique())
    # Pre-build lookup for O(1) per-stock access
    date_to_df = {d: grp.set_index('ticker') for d, grp in df.groupby('date')}

    cash = config.initial_capital
    positions: list[Position] = []
    trades: list[dict] = []
    snapshots: list[dict] = []

    for i, today in enumerate(dates):
        today_df = date_to_df[today]
        prev_df = date_to_df.get(dates[i - 1]) if i > 0 else None

        # PHASE 1: INCREMENT
        for pos in positions:
            pos.days_held += 1

        # PHASE 2: CHECK EXITS
        remaining = []
        for pos in positions:
            if pos.days_held < 1:
                remaining.append(pos)
                continue
            if pos.ticker not in today_df.index:
                # Delisted: force close at entry price (conservative)
                cash += pos.shares * pos.entry_price
                trades.append(_build_trade(pos, today, pos.entry_price, 'forced_close'))
                continue
            should_exit, fill_price, reason = check_exit(pos, today_df.loc[pos.ticker], config)
            if should_exit:
                cash += pos.shares * fill_price
                trades.append(_build_trade(pos, today, fill_price, reason))
            else:
                remaining.append(pos)
        positions = remaining

        # PHASE 3: NEW ENTRIES
        open_slots = config.max_positions - len(positions)
        if open_slots > 0 and prev_df is not None:
            held_tickers = {p.ticker for p in positions}
            # NOTE: each condition MUST be in parentheses (pandas & precedence)
            candidates = prev_df[
                (prev_df['volume'] > config.V) &
                (prev_df['os_score'].notna()) &
                (~prev_df.index.isin(held_tickers)) &
                (prev_df.index.isin(today_df.index))
            ].nlargest(open_slots, 'os_score')

            for ticker in candidates.index:
                allocation = cash / open_slots
                buy_price = today_df.loc[ticker, 'close']
                shares = int(allocation // buy_price)
                if shares > 0:
                    cost = shares * buy_price
                    cash -= cost
                    open_slots -= 1
                    positions.append(Position(
                        ticker=ticker,
                        entry_date=today,
                        entry_price=buy_price,
                        shares=shares,
                        cost_basis=cost,
                        days_held=0,
                        r_prev=prev_df.loc[ticker, 'r'],
                        v_prev=prev_df.loc[ticker, 'volume'],
                        dr_prev=prev_df.loc[ticker, 'D_r'],
                        dv_prev=prev_df.loc[ticker, 'D_v'],
                        os_prev=prev_df.loc[ticker, 'os_score'],
                        company_name=prev_df.loc[ticker].get('name', ''),
                        industry=prev_df.loc[ticker].get('industry', ''),
                    ))

        # PHASE 4: SNAPSHOT
        pos_value = sum(
            pos.shares * today_df.loc[pos.ticker, 'close']
            for pos in positions if pos.ticker in today_df.index
        )
        snapshots.append({
            'date': today.strftime('%Y-%m-%d'),
            'cash': round(cash, 2),
            'position_value': round(pos_value, 2),
            'total_value': round(cash + pos_value, 2),
        })

    port_df = pd.DataFrame(snapshots)
    port_df['daily_return'] = port_df['total_value'].pct_change().fillna(0)
    port_df['cumulative_return'] = (1 + port_df['daily_return']).cumprod() - 1

    return pd.DataFrame(trades), port_df


def _build_trade(pos: Position, exit_date, exit_price: float, reason: str) -> dict:
    pnl = (exit_price - pos.entry_price) * pos.shares
    return {
        'ticker': pos.ticker,
        'company_name': pos.company_name,
        'industry': pos.industry,
        'entry_date': pos.entry_date.strftime('%Y-%m-%d'),
        'entry_price': round(pos.entry_price, 4),
        'exit_date': exit_date.strftime('%Y-%m-%d'),
        'exit_price': round(exit_price, 4),
        'shares': pos.shares,
        'pnl': round(pnl, 2),
        'pnl_pct': round(exit_price / pos.entry_price - 1, 6),
        'exit_reason': reason,
        'days_held': pos.days_held,
        'r_prev': round(pos.r_prev, 6),
        'v_prev': pos.v_prev,
        'dr_prev': round(pos.dr_prev, 6),
        'dv_prev': round(pos.dv_prev, 6),
        'os_prev': round(pos.os_prev, 6),
    }
```

---

## 8. Data Flow: preprocess.py → engine → report.py

```
[1] python data/v1/preprocess.py --source fake
      Reads:  data/fake_data/SHARADAR_SEP.csv + SHARADAR_TICKERS.csv
      Writes: data/v1/prices.csv (14 columns, sorted by ticker+date)

[2] python -m backtesting.run
      |
      +-- data_loader.load_price_data(config)
      |     Reads: data/v1/prices.csv -> pd.DataFrame
      |
      +-- signals.compute_os_scores(df, config)
      |     Adds columns: r, D_r, D_v, os_score
      |
      +-- engine.run_backtest(df, config)
      |     Returns: trades_df, portfolio_df
      |
      +-- Saves to results/{run_id}/:
      |     trades.csv, portfolio.csv, config.json
      |
      +-- results.report.save_report(run_id, config_dict, metrics, trades_df, portfolio_df)
            Writes: results/{run_id}/report.html
```

`run.py` is the single entry point after preprocessing. No other script to run.

---

## 9. Reporting Module (results/report.py)

```python
def compute_metrics(portfolio_df: pd.DataFrame) -> dict:
    """
    Returns: {n_trades, total_return_pct, sharpe_ratio, max_drawdown_pct}
    Sharpe = (mean(daily_return) / std(daily_return)) * sqrt(252), rf=0.
    Max drawdown = min((total_value - running_max) / running_max) * 100.
    """

def save_report(run_id: str, config_dict: dict, metrics: dict,
                trades_df: pd.DataFrame, portfolio_df: pd.DataFrame,
                output_dir: Path) -> Path:
    """Generates report.html using Plotly + string.Template. Returns path."""

# Private helpers:
def _build_daily_return_chart(portfolio_df) -> str:    # Plotly bar chart JSON
def _build_total_value_chart(portfolio_df) -> str:     # Plotly line chart JSON
def _render_trades_table(trades_df) -> str:            # HTML <table> rows
def _render_html(...) -> str:                          # Full HTML assembly
```

**HTML report contains:**
1. Header (run_id)
2. Metric cards: Total Return %, Sharpe Ratio, Max Drawdown %
3. Daily Return bar chart (Plotly, red/green bars, CDN)
4. Total Portfolio Value line chart (Plotly, with initial capital reference line)
5. Trades table with client-side JS filtering by ticker and exit_reason (~40 lines vanilla JS)
6. Collapsible `<details>` config viewer

**Template approach:** `string.Template` with `$placeholder` syntax (avoids `{` `}` conflicts with CSS/JS).

---

## 10. Conflicts Resolved Between Plans

| Conflict | Resolution |
|---|---|
| trades.csv: one-row-per-trade (Engine plan) vs two-rows-per-trade (Results plan) | **One row per completed trade wins.** Simpler, self-contained rows. |
| config.json: flat structure (Engine) vs nested params/data/metrics (Results) | **Flat wins** (`dataclasses.asdict`). Added Sharpe/drawdown from Results into `metrics`. |
| Exit reason: 6 granular values (Engine) vs 3 coarse values (Results) | **6 granular values win.** More analytical value. |
| `days_held` vs `hold_days` | **Standardized to `days_held`.** |
| `exit_reason` vs `exit_type` | **Standardized to `exit_reason`.** |
| run_id generation location | **In `run.py` only.** No utility function in report.py. |
| Pandas `&` precedence bug in candidate filter | **Fixed.** Each condition wrapped in parentheses. |
| `data/v1/description.md` | **Dropped.** Code + this plan are sufficient documentation. |

---

## 11. Implementation Order

### Step 1: Setup
- [ ] Create `.gitignore` with entries from Section 3
- [ ] Create `data/raw/.gitkeep`
- [ ] Create `data/v1/` directory

### Step 2: Data Pipeline
- [ ] Implement `data/v1/preprocess.py` (5 functions: load_data, filter_tickers, merge_and_clean, handle_missing, write_output)
- [ ] Run: `python data/v1/preprocess.py --source fake`
- [ ] Verify: `prices.csv` exists, 5 tickers incl. ZNRG, 14 columns, no NaN in close_ffill

### Step 3: Config + Data Loader
- [ ] Create `backtesting/` with `__init__.py`
- [ ] Implement `config.py` with `BacktestConfig`
- [ ] Implement `data_loader.py` with `load_price_data()`

### Step 4: Signal Computation
- [ ] Implement `signals.py` with `compute_os_scores()`
- [ ] Verify against hand-computed values for one ticker

### Step 5: Engine
- [ ] Implement `Position` dataclass and `check_exit()` in `engine.py`
- [ ] Test all 7 exit cases (gap_down_stop, gap_up_tp, intraday_tp, intraday_sl, both-hit-TP-wins, max_hold, no_exit)
- [ ] Implement `run_backtest()` with correct 4-phase ordering

### Step 6: Orchestrator
- [ ] Implement `backtesting/run.py`
- [ ] Wire `__init__.py` exports
- [ ] Run: `python -m backtesting.run`
- [ ] Verify: `results/{run_id}/` has trades.csv, portfolio.csv, config.json
- [ ] Verify: cash never negative, positions never exceed 3

### Step 7: Reporting
- [ ] Create `results/__init__.py` (empty)
- [ ] Implement `results/report.py`
- [ ] Wire `save_report()` into `backtesting/run.py`
- [ ] Add `plotly` to requirements.txt
- [ ] Open report.html in browser: verify charts render, table filters work

### Step 8: Validation
- [ ] Run on fake data (5 stocks, 2022-2024), inspect all outputs
- [ ] Verify no look-ahead bias
- [ ] Verify edge cases: first N days (no signals), delisted ZNRG, max hold, gap exits

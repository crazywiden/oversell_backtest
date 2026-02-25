# Backend Engine Plan v1 — Oversell Backtesting Engine

**Date:** 2026-02-24
**Status:** Draft
**Author:** backend-planner agent

---

## Summary & Context

This document specifies the architecture for the `backtesting/` folder: the core simulation engine for the oversell/oversold trading strategy. The engine loads preprocessed OHLCV data, computes OS (OverSell) scores vectorized across all stocks, runs a day-by-day portfolio simulation with sequential exit logic, and outputs trades and daily portfolio snapshots as CSV files.

### Relevant Repo Files

| File | Role |
|------|------|
| `data/fake_data/SHARADAR_SEP.csv` | 3566 rows, 5 tickers. Columns: ticker, date, open, high, low, close, volume, closeunadj, dividends, lastupdated |
| `data/fake_data/SHARADAR_TICKERS.csv` | Ticker metadata (name, sector, industry, isdelisted) |
| `data/fake_data/generate_fake_sharadar.py` | Generates fake data; establishes code style |
| `CLAUDE.md` | Project conventions: vectorized ops, no look-ahead bias, separate concerns |

---

## Goals

1. Compute OS scores vectorized across all stocks using pandas rolling operations
2. Simulate the strategy day-by-day with correct position tracking (max 3 positions, equal weight 1/3 of available cash)
3. Enforce no look-ahead bias: on day T, only use data available through close of T-1
4. Implement the exact sequential exit logic (gap-down stop, gap-up TP, intraday bracket, max hold)
5. Output two CSV files: trades log and daily portfolio state
6. Accept all hyperparameters via a single Python dataclass

## Non-Goals

- No transaction cost or slippage modeling (strategy is finalized as-is)
- No optimization or grid search
- No visualization or reporting (separate component)
- No live trading integration
- No database; CSV in, CSV out
- No multi-threading or parallelism

---

## Proposed `backtesting/` Folder Structure

```
backtesting/
    __init__.py          # Exports run_backtest, BacktestConfig
    config.py            # BacktestConfig dataclass (all hyperparameters)
    data_loader.py       # Load and validate price CSV
    signals.py           # Vectorized OS score computation
    engine.py            # Day-by-day simulation loop + exit logic
    run.py               # Entry point: load config -> load data -> run engine -> save CSVs
```

Five files plus `__init__.py`. Each file has a single responsibility. Total estimated size: under 500 lines.

---

## Data Flow Diagram

```
   data/v1/prices.csv     (or data/fake_data/SHARADAR_SEP.csv)
           |
     [data_loader.py]
     load_price_data()
           |
    pd.DataFrame (OHLCV)
           |
      [signals.py]
   compute_os_scores()
           |
   pd.DataFrame (OHLCV + r, D_r, D_v, os_score)
           |
      [engine.py]
     run_backtest()
     /            \
trades_df      portfolio_df
     |                |
 trades.csv      portfolio.csv
     \                /
       [run_id folder]
```

---

## Module/Function Breakdown

### `config.py`

```python
import dataclasses

@dataclasses.dataclass
class BacktestConfig:
    # --- Hyperparameters ---
    N: int = 20                    # Rolling window for z-scores (days)
    w1: float = -1.0               # Weight for return z-score D(r)
    w2: float = 1.0                # Weight for volume z-score D(v)
    win_take_rate: float = 0.05    # Take-profit threshold (5%)
    stop_loss_rate: float = 0.03   # Stop-loss threshold (3%)
    K: int = 5                     # Max hold days
    V: int = 500_000               # Minimum volume filter (shares)

    # --- Capital ---
    initial_capital: float = 500_000.0
    max_positions: int = 3

    # --- Paths ---
    data_path: str = "data/v1/prices.csv"
    output_dir: str = "results/default"
    run_id: str = ""               # Set by run.py at runtime
```

No methods. Pure data container.

---

### `data_loader.py`

```python
def load_price_data(config: BacktestConfig) -> pd.DataFrame:
    """
    Load price CSV into a DataFrame.

    Steps:
    1. Read CSV from config.data_path, parse 'date' as datetime
    2. Sort by (ticker, date)
    3. Keep columns: ticker, date, open, high, low, close, volume
       (plus name, sector, industry if present — needed for trade records)
    4. Verify no nulls in critical OHLCV columns
    5. Return the DataFrame

    Returns:
        pd.DataFrame sorted by (ticker, date), date as datetime dtype.
    """
```

---

### `signals.py` — Vectorized OS Score Computation

```python
def compute_os_scores(df: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
    """
    Compute OS scores vectorized across all stocks.

    For each stock (grouped by ticker), using rolling window N:

    1. r_T     = close_T / close_{T-1} - 1
    2. D(r)_T  = sign(r_T) * (|r_T| - rolling_mean(|r|, N)) / rolling_std(|r|, N)
    3. D(v)_T  = (volume_T - rolling_mean(volume, N)) / rolling_std(volume, N)
    4. OS_T    = w1 * D(r)_T + w2 * D(v)_T

    NaN in first N rows per ticker propagates to NaN os_score — engine skips these.
    Division by zero (std=0) produces NaN — safely excluded from selection.
    """
```

**Implementation (vectorized, no per-row loops):**

```python
def compute_os_scores(df, config):
    N, w1, w2 = config.N, config.w1, config.w2
    df = df.sort_values(['ticker', 'date']).reset_index(drop=True)

    # Daily return per ticker (first row per ticker = NaN)
    df['r'] = df.groupby('ticker')['close'].pct_change()

    # Rolling stats on |r|
    df['D_r'] = df.groupby('ticker')['r'].transform(
        lambda x: np.sign(x) * (x.abs() - x.abs().rolling(N).mean()) / x.abs().rolling(N).std()
    )

    # Rolling stats on volume
    df['D_v'] = df.groupby('ticker')['volume'].transform(
        lambda x: (x - x.rolling(N).mean()) / x.rolling(N).std()
    )

    df['os_score'] = w1 * df['D_r'] + w2 * df['D_v']
    return df
```

---

### `engine.py` — Simulation Loop + Exit Logic

#### Position Tracking

```python
@dataclasses.dataclass
class Position:
    """Tracks a single open position."""
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float         # Close price on entry day
    shares: int
    cost_basis: float          # entry_price * shares
    days_held: int = 0         # Trading days held (0 on entry day, 1 on T+1)
    # Factor scores at time of buy decision (from T-1 data)
    r_prev: float = 0.0
    v_prev: float = 0.0
    dr_prev: float = 0.0
    dv_prev: float = 0.0
    os_prev: float = 0.0
    # Metadata for trade records
    company_name: str = ""
    industry: str = ""
```

#### Exit Logic (Sequential)

```python
def check_exit(pos: Position, row: pd.Series, config: BacktestConfig) -> tuple[bool, float, str]:
    """
    Check sequential exit conditions.

    Returns: (should_exit, fill_price, exit_reason)
    exit_reason: "gap_down_stop" | "gap_up_tp" | "intraday_tp" | "intraday_sl" | "max_hold" | ""

    Step 1 — Gap-down stop:   open <= p*(1-SL)  -> fill at open
    Step 2 — Gap-up TP:       open >= p*(1+TP)  -> fill at open
    Step 3 — Intraday bracket (only if 1 & 2 did not fire):
              high >= p*(1+TP) -> TP fill at limit price
              low  <= p*(1-SL) -> SL fill at limit price
              BOTH hit: TP wins
    Step 4 — Max hold: days_held >= K -> fill at close
    """
    p = pos.entry_price
    tp = p * (1 + config.win_take_rate)
    sl = p * (1 - config.stop_loss_rate)
    o, h, l, c = row['open'], row['high'], row['low'], row['close']

    # Step 1
    if o <= sl:
        return True, o, 'gap_down_stop'
    # Step 2
    if o >= tp:
        return True, o, 'gap_up_tp'
    # Step 3
    if h >= tp:  # TP wins even if SL also in range
        return True, tp, 'intraday_tp'
    if l <= sl:
        return True, sl, 'intraday_sl'
    # Step 4
    if pos.days_held >= config.K:
        return True, c, 'max_hold'

    return False, 0.0, ''
```

**TP wins intraday ties:** The spec states "If BOTH TP and SL within range on same day, TP wins." Checking `h >= tp` before `l <= sl` implements this correctly — TP is returned whenever the high reaches the TP level, regardless of whether the low also reaches SL.

#### Critical: Phase Ordering for Correct days_held Timing

The spec states: "When buy a stock, we can only sell it the next day."

**Corrected per-day execution order:**

```
For each trading day:
    PHASE 1: INCREMENT days_held for all existing positions
    PHASE 2: CHECK EXITS on positions where days_held >= 1
    PHASE 3: SELECT NEW ENTRIES (new positions created with days_held=0)
    PHASE 4: DAILY SNAPSHOT
```

**Trace (why this is correct):**
- Day T, Phase 3: Position created, `days_held = 0`
- Day T+1, Phase 1: Increment → `days_held = 1`
- Day T+1, Phase 2: `days_held = 1 >= 1` → eligible for exit ✓

**If increment came AFTER exit check (wrong order):**
- Day T, Phase 3: `days_held = 0`
- Day T+1, Phase 2: `days_held = 0 < 1` → skipped (wrong! can't exit on T+1)
- Day T+1, Phase 3 (increment): `days_held = 1`
- Day T+2: first exit → off by one day

#### Main Simulation Pseudocode

```python
def run_backtest(df, config):
    # Pre-loop: build fast lookup dict
    dates = sorted(df['date'].unique())
    date_to_df = {d: grp.set_index('ticker') for d, grp in df.groupby('date')}

    cash = config.initial_capital
    positions = []      # list[Position]
    trades = []         # list of dicts (completed trades)
    snapshots = []      # list of dicts (daily portfolio state)

    for i, today in enumerate(dates):
        today_df = date_to_df[today]
        prev_df = date_to_df.get(dates[i-1]) if i > 0 else None

        # PHASE 1: INCREMENT days_held
        for pos in positions:
            pos.days_held += 1

        # PHASE 2: CHECK EXITS
        remaining = []
        for pos in positions:
            if pos.days_held < 1:
                remaining.append(pos)
                continue
            if pos.ticker not in today_df.index:
                # Stock delisted — force close at entry price
                cash += pos.shares * pos.entry_price
                trades.append(build_trade_record(pos, today, pos.entry_price, 'forced_close'))
                continue
            should_exit, fill_price, reason = check_exit(pos, today_df.loc[pos.ticker], config)
            if should_exit:
                cash += pos.shares * fill_price
                trades.append(build_trade_record(pos, today, fill_price, reason))
            else:
                remaining.append(pos)
        positions = remaining

        # PHASE 3: NEW ENTRIES
        open_slots = config.max_positions - len(positions)
        if open_slots > 0 and prev_df is not None:
            held = {p.ticker for p in positions}
            candidates = prev_df[
                prev_df['volume'] > config.V &
                prev_df['os_score'].notna() &
                ~prev_df.index.isin(held) &
                prev_df.index.isin(today_df.index)
            ].nlargest(open_slots, 'os_score')

            for ticker in candidates.index:
                allocation = cash / (open_slots)  # equal split of remaining cash
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

    # Compute daily_return and cumulative_return from portfolio snapshots
    port_df = pd.DataFrame(snapshots)
    port_df['daily_return'] = port_df['total_value'].pct_change().fillna(0)
    port_df['cumulative_return'] = (1 + port_df['daily_return']).cumprod() - 1

    return pd.DataFrame(trades), port_df
```

---

### `run.py` — Orchestrator

```python
from backtesting.config import BacktestConfig
from backtesting.data_loader import load_price_data
from backtesting.signals import compute_os_scores
from backtesting.engine import run_backtest
from datetime import datetime
from pathlib import Path
import json

def main(config: BacktestConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if config is None:
        config = BacktestConfig()

    # Generate run ID if not provided
    if not config.run_id:
        config.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        config.output_dir = f"results/{config.run_id}"

    # 1. Load
    df = load_price_data(config)

    # 2. Signals
    df = compute_os_scores(df, config)

    # 3. Simulate
    trades_df, portfolio_df = run_backtest(df, config)

    # 4. Save
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    trades_df.to_csv(out / "trades.csv", index=False)
    portfolio_df.to_csv(out / "portfolio.csv", index=False)

    # 5. Save config
    config_dict = dataclasses.asdict(config)
    config_dict["metrics"] = {
        "n_trades": len(trades_df),
        "total_return_pct": round(portfolio_df["cumulative_return"].iloc[-1] * 100, 2) if len(portfolio_df) else 0,
    }
    (out / "config.json").write_text(json.dumps(config_dict, indent=2))

    return trades_df, portfolio_df


if __name__ == "__main__":
    main()
```

---

### `__init__.py`

```python
from backtesting.config import BacktestConfig
from backtesting.run import main as run_backtest
```

---

## Output Schemas

### trades.csv

| Column | Type | Description |
|---|---|---|
| ticker | str | Stock ticker symbol |
| company_name | str | Full company name |
| industry | str | Industry classification |
| entry_date | str | Date position opened (YYYY-MM-DD) |
| entry_price | float | Close price on entry day |
| exit_date | str | Date position closed (YYYY-MM-DD) |
| exit_price | float | Fill price at exit |
| shares | int | Number of shares held |
| pnl | float | Profit/loss in dollars |
| pnl_pct | float | Return as decimal |
| exit_reason | str | gap_down_stop \| gap_up_tp \| intraday_tp \| intraday_sl \| max_hold \| forced_close |
| days_held | int | Trading days held |
| r_prev | float | r_{T-1} at time of buy decision |
| v_prev | float | v_{T-1} (volume) at time of buy decision |
| dr_prev | float | D(r)_{T-1} z-score |
| dv_prev | float | D(v)_{T-1} z-score |
| os_prev | float | OS_{T-1} score |

### portfolio.csv

| Column | Type | Description |
|---|---|---|
| date | str | Trading date (YYYY-MM-DD) |
| cash | float | Cash balance at end of day |
| position_value | float | Mark-to-market value of open positions |
| total_value | float | cash + position_value |
| daily_return | float | Day-over-day return as decimal |
| cumulative_return | float | Cumulative return from start as decimal |

---

## Alternatives Considered

### Alternative A: Event-Driven Architecture

Use an event bus with separate handler classes for entry signals, exit checks, portfolio updates.

**Rejected.** Over-engineered for 3 positions and 4 exit types. Violates CLAUDE.md "DO NOT over-engineer." Sequential day loop is simpler and easier to audit for correctness.

### Alternative B: Fully Vectorized Simulation

Precompute all entry/exit signals as boolean matrices, track positions without any Python loop.

**Rejected.** Position sizing depends on current cash (sequential dependency). "Freed cash available same day" rule creates intra-day ordering dependencies. Sequential exit priority (gap > intraday > max hold) is extremely hard to express vectorized correctly.

### Alternative C: Single-File Script

Everything in one `backtest.py` file.

**Rejected.** Mixes data loading, signal computation, simulation, and output. Harder to test components independently. Violates CLAUDE.md separation of concerns.

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Look-ahead bias | Low | Use `prev_df` (T-1 data) for all signal lookups. Entry executes at close of T. |
| Off-by-one in days_held | Medium (caught in design) | Increment BEFORE exit check. Entry day = 0, first exit day = T+1 (days_held=1). Documented invariant. |
| Cash going negative | Low | `int(allocation // buy_price)` — floor division ensures exact budget. If shares=0, position skipped. |
| Delisted stock in open position | Low | Force-close when stock data missing for the day. Conservative: fill at entry price. |
| Rolling std = 0 (constant prices) | Low | Produces NaN os_score → stock excluded from selection safely. |

---

## Testing Strategy

1. **Unit test `signals.py`**: Hand-compute OS scores for 2 stocks over 25 days. Compare output within float tolerance.
2. **Unit test `check_exit`**: 7 cases: gap_down_stop, gap_up_tp, intraday_tp, intraday_sl, both-hit-TP-wins, max_hold, no_exit.
3. **Unit test `data_loader.py`**: Load fake data, verify shape, column names, dtypes, no nulls.
4. **Integration test**: Run full pipeline on fake data. Verify: entry dates use prior-day scores, cash never negative, positions never exceed 3, final equity = cash + sum of positions.
5. **Regression test**: Save golden output CSVs. Assert future runs produce identical output (engine is deterministic).

---

## Implementation Checklist

- [ ] Create `backtesting/` folder with empty `__init__.py`
- [ ] Implement `config.py` with `BacktestConfig` dataclass
- [ ] Implement `data_loader.py` with `load_price_data()`
- [ ] Implement `signals.py` with `compute_os_scores()` — test against hand calculation
- [ ] Implement `Position` dataclass and `check_exit()` in `engine.py` — test all 7 exit cases
- [ ] Implement main `run_backtest()` loop in `engine.py` with correct phase ordering
- [ ] Implement `run.py` with CSV output and summary print
- [ ] Wire up `__init__.py` exports
- [ ] Run on fake data (5 stocks, 2022-2024), inspect trades.csv and portfolio.csv
- [ ] Verify no look-ahead bias: all entries use T-1 data
- [ ] Verify edge cases: first N days (no OS scores), delisted stock (ZNRG), max hold expiry, gap exits
- [ ] Add `results/*/` to `.gitignore`

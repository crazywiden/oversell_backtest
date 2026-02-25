import dataclasses

import pandas as pd

from backtesting.config import BacktestConfig


@dataclasses.dataclass
class Position:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float          # Close price on entry day
    shares: int
    cost_basis: float           # entry_price * shares
    days_held: int = 0          # 0 on entry day, incremented each subsequent day
    r_prev: float = 0.0         # Factor scores at time of buy decision (T-1 data)
    v_prev: float = 0.0
    dr_prev: float = 0.0
    dv_prev: float = 0.0
    os_prev: float = 0.0
    company_name: str = ""
    industry: str = ""


def check_exit(pos: Position, row: pd.Series, config: BacktestConfig) -> tuple[bool, float, str]:
    """
    Sequential exit priority:
      1. Gap-down stop:  open <= entry * (1 - SL)  -> fill at open
      2. Gap-up TP:      open >= entry * (1 + TP)  -> fill at open
      3. Intraday TP:    high >= entry * (1 + TP)  -> fill at limit price (TP wins ties)
      4. Intraday SL:    low  <= entry * (1 - SL)  -> fill at limit price
      5. Max hold:       days_held >= K             -> fill at close

    Returns: (should_exit, fill_price, exit_reason)
    """
    p = pos.entry_price
    tp_price = p * (1 + config.win_take_rate)
    sl_price = p * (1 - config.stop_loss_rate)
    o, h, l, c = row["open"], row["high"], row["low"], row["close"]

    if o <= sl_price:
        return True, o, "gap_down_stop"
    if o >= tp_price:
        return True, o, "gap_up_tp"
    if h >= tp_price:
        return True, tp_price, "intraday_tp"
    if l <= sl_price:
        return True, sl_price, "intraday_sl"
    if pos.days_held >= config.K:
        return True, c, "max_hold"

    return False, 0.0, ""


def run_backtest(df: pd.DataFrame, config: BacktestConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Day-by-day simulation with 4-phase ordering:
      PHASE 1: INCREMENT days_held for all existing positions
      PHASE 2: CHECK EXITS on positions where days_held >= 1
      PHASE 3: SELECT NEW ENTRIES from T-1 scores, buy at T close
      PHASE 4: RECORD DAILY SNAPSHOT (cash + mark-to-market)

    Returns: (trades_df, portfolio_df)
    """
    dates = sorted(df["date"].unique())
    # Pre-build lookup dict for O(1) per-stock access per date
    date_to_df = {d: grp.set_index("ticker") for d, grp in df.groupby("date")}

    cash = config.initial_capital
    positions: list[Position] = []
    trades: list[dict] = []
    snapshots: list[dict] = []

    for i, today in enumerate(dates):
        today_df = date_to_df[today]
        prev_df = date_to_df.get(dates[i - 1]) if i > 0 else None

        # PHASE 1: INCREMENT days_held
        for pos in positions:
            pos.days_held += 1

        # PHASE 2: CHECK EXITS
        remaining = []
        for pos in positions:
            if pos.ticker not in today_df.index:
                # Delisted: force close at entry price (conservative)
                cash += pos.shares * pos.entry_price
                trades.append(_build_trade(pos, today, pos.entry_price, "forced_close"))
                continue
            should_exit, fill_price, reason = check_exit(
                pos, today_df.loc[pos.ticker], config
            )
            if should_exit:
                cash += pos.shares * fill_price
                trades.append(_build_trade(pos, today, fill_price, reason))
            else:
                remaining.append(pos)
        positions = remaining

        # PHASE 3: NEW ENTRIES (using T-1 scores)
        open_slots = config.max_positions - len(positions)
        if open_slots > 0 and prev_df is not None:
            held_tickers = {p.ticker for p in positions}
            candidates = prev_df[
                (prev_df["volume"] > config.V) &
                (prev_df["os_score"].notna()) &
                (~prev_df.index.isin(held_tickers)) &
                (prev_df.index.isin(today_df.index))
            ].nlargest(open_slots, "os_score")

            for ticker in candidates.index:
                allocation = cash / open_slots
                buy_price = today_df.loc[ticker, "close"]
                shares = int(allocation // buy_price)
                if shares > 0:
                    cost = shares * buy_price
                    cash -= cost
                    open_slots -= 1
                    prev_row = prev_df.loc[ticker]
                    positions.append(Position(
                        ticker=ticker,
                        entry_date=today,
                        entry_price=buy_price,
                        shares=shares,
                        cost_basis=cost,
                        days_held=0,
                        r_prev=float(prev_row.get("r", 0.0) or 0.0),
                        v_prev=float(prev_row.get("volume", 0.0) or 0.0),
                        dr_prev=float(prev_row.get("D_r", 0.0) or 0.0),
                        dv_prev=float(prev_row.get("D_v", 0.0) or 0.0),
                        os_prev=float(prev_row.get("os_score", 0.0) or 0.0),
                        company_name=str(prev_row.get("name", "")),
                        industry=str(prev_row.get("industry", "")),
                    ))

        # PHASE 4: DAILY SNAPSHOT
        pos_value = sum(
            pos.shares * today_df.loc[pos.ticker, "close"]
            for pos in positions
            if pos.ticker in today_df.index
        )
        snapshots.append({
            "date": pd.Timestamp(today).strftime("%Y-%m-%d"),
            "cash": round(cash, 2),
            "position_value": round(pos_value, 2),
            "total_value": round(cash + pos_value, 2),
        })

    # Force-close any remaining open positions at last close
    last_date = dates[-1]
    last_df = date_to_df[last_date]
    for pos in positions:
        if pos.ticker in last_df.index:
            fill_price = last_df.loc[pos.ticker, "close"]
            trades.append(_build_trade(pos, last_date, fill_price, "forced_close"))

    port_df = pd.DataFrame(snapshots)
    if not port_df.empty:
        port_df["daily_return"] = port_df["total_value"].pct_change().fillna(0)
        port_df["cumulative_return"] = (1 + port_df["daily_return"]).cumprod() - 1

    return pd.DataFrame(trades), port_df


def _build_trade(pos: Position, exit_date, exit_price: float, reason: str) -> dict:
    pnl = (exit_price - pos.entry_price) * pos.shares
    return {
        "ticker": pos.ticker,
        "company_name": pos.company_name,
        "industry": pos.industry,
        "entry_date": pd.Timestamp(pos.entry_date).strftime("%Y-%m-%d"),
        "entry_price": round(pos.entry_price, 4),
        "exit_date": pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
        "exit_price": round(exit_price, 4),
        "shares": pos.shares,
        "pnl": round(pnl, 2),
        "pnl_pct": round(exit_price / pos.entry_price - 1, 6),
        "exit_reason": reason,
        "days_held": pos.days_held,
        "r_prev": round(pos.r_prev, 6),
        "v_prev": pos.v_prev,
        "dr_prev": round(pos.dr_prev, 6),
        "dv_prev": round(pos.dv_prev, 6),
        "os_prev": round(pos.os_prev, 6),
    }

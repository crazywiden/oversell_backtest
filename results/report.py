"""
Generate interactive HTML5 report from backtest results.

Public API:
    compute_metrics(portfolio_df, trades_df) -> dict
    save_report(run_id, config_dict, metrics, trades_df, portfolio_df, output_dir) -> Path
"""

import html
import itertools
import json
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Sentinel-based template: use __PLACEHOLDER__ to avoid conflicts with CSS/JS
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Oversell Backtest — __RUN_ID__</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 16px; }
  h1 { font-size: 1.4rem; margin-bottom: 4px; }
  .run-id { color: #94a3b8; font-size: 0.85rem; margin-bottom: 24px; }
  .metrics { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
  .metric-card { background: #1e293b; border-radius: 8px; padding: 16px 24px; min-width: 160px; }
  .metric-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; }
  .metric-value { font-size: 1.7rem; font-weight: 700; margin-top: 4px; }
  .positive { color: #22c55e; }
  .negative { color: #ef4444; }
  .neutral { color: #e2e8f0; }
  .chart-container { background: #1e293b; border-radius: 8px; margin-bottom: 20px; padding: 8px; }
  .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
  .section-title { font-size: 1rem; font-weight: 600; margin: 24px 0 12px; color: #cbd5e1; }
  .filter-bar { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
  .filter-bar input, .filter-bar select {
    background: #1e293b; border: 1px solid #334155; color: #e2e8f0;
    padding: 6px 10px; border-radius: 6px; font-size: 0.85rem;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
  thead { background: #1e293b; position: sticky; top: 0; }
  th { padding: 8px 10px; text-align: left; color: #94a3b8; font-weight: 600; cursor: pointer; user-select: none; }
  th:hover { color: #e2e8f0; }
  td { padding: 6px 10px; border-bottom: 1px solid #1e293b; }
  tr:hover td { background: #1e293b; }
  .pnl-pos { color: #22c55e; font-weight: 600; }
  .pnl-neg { color: #ef4444; font-weight: 600; }
  details { margin-top: 24px; background: #1e293b; border-radius: 8px; padding: 12px 16px; }
  summary { cursor: pointer; color: #94a3b8; font-size: 0.85rem; }
  pre { font-size: 0.75rem; color: #94a3b8; overflow-x: auto; margin-top: 8px; }
</style>
</head>
<body>

<h1>Oversell Backtest Report</h1>
<div class="run-id">Run: __RUN_ID__</div>

<div class="metrics">
  <div class="metric-card">
    <div class="metric-label">Total Return</div>
    <div class="metric-value __RETURN_CLASS__">__TOTAL_RETURN__</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Sharpe Ratio</div>
    <div class="metric-value __SHARPE_CLASS__">__SHARPE_RATIO__</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Max Drawdown</div>
    <div class="metric-value negative">__MAX_DRAWDOWN__</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Total Trades</div>
    <div class="metric-value neutral">__N_TRADES__</div>
  </div>
</div>

<div class="chart-container" id="chart-daily-return"></div>
<div class="chart-container" id="chart-total-value"></div>

<div class="section-title">Trade Analysis</div>
<div class="metrics">
  <div class="metric-card">
    <div class="metric-label">Win Rate</div>
    <div class="metric-value __WIN_RATE_CLASS__">__WIN_RATE__</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Profit Factor</div>
    <div class="metric-value __PROFIT_FACTOR_CLASS__">__PROFIT_FACTOR__</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Payoff Ratio</div>
    <div class="metric-value neutral">__PAYOFF_RATIO__</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Max Consec. Losses</div>
    <div class="metric-value neutral">__MAX_CONSEC_LOSSES__</div>
  </div>
</div>
<div class="chart-grid">
  <div class="chart-container" id="chart-return-dist"></div>
  <div class="chart-container" id="chart-exit-reason"></div>
  <div class="chart-container" id="chart-exit-pnl"></div>
  <div class="chart-container" id="chart-monthly-pnl"></div>
</div>

<div class="section-title">Trades</div>
<div class="filter-bar">
  <input id="filter-ticker" placeholder="Filter ticker..." oninput="applyFilters()">
  <select id="filter-exit" onchange="applyFilters()">
    <option value="">All exit types</option>
    <option value="gap_down_stop">Gap-down stop</option>
    <option value="gap_up_tp">Gap-up TP</option>
    <option value="intraday_tp">Intraday TP</option>
    <option value="intraday_sl">Intraday SL</option>
    <option value="max_hold">Max hold</option>
    <option value="forced_close">Forced close</option>
  </select>
</div>
<div style="overflow-x:auto">
<table id="trades-table">
  <thead>
    <tr>
      <th onclick="sortTable(0)">Ticker</th>
      <th onclick="sortTable(1)">Company</th>
      <th onclick="sortTable(2)">Industry</th>
      <th onclick="sortTable(3)">Entry Date</th>
      <th onclick="sortTable(4)">Exit Date</th>
      <th onclick="sortTable(5)">Entry $</th>
      <th onclick="sortTable(6)">Exit $</th>
      <th onclick="sortTable(7)">Shares</th>
      <th onclick="sortTable(8)">P&amp;L</th>
      <th onclick="sortTable(9)">P&amp;L %</th>
      <th onclick="sortTable(10)">Days</th>
      <th onclick="sortTable(11)">Exit Reason</th>
      <th onclick="sortTable(12)">OS Score</th>
      <th onclick="sortTable(13)">D(r)</th>
      <th onclick="sortTable(14)">D(v)</th>
    </tr>
  </thead>
  <tbody id="trades-tbody">
__TRADES_ROWS__
  </tbody>
</table>
</div>

<details>
  <summary>Config</summary>
  <pre>__CONFIG_JSON__</pre>
</details>

<script>
var dailyReturnSpec = JSON.parse('__DAILY_RETURN_JSON__');
Plotly.newPlot('chart-daily-return', dailyReturnSpec.data, dailyReturnSpec.layout, {responsive: true});

var totalValueSpec = JSON.parse('__TOTAL_VALUE_JSON__');
Plotly.newPlot('chart-total-value', totalValueSpec.data, totalValueSpec.layout, {responsive: true});

var returnDistSpec = JSON.parse('__RETURN_DIST_JSON__');
Plotly.newPlot('chart-return-dist', returnDistSpec.data, returnDistSpec.layout, {responsive: true});

var exitReasonSpec = JSON.parse('__EXIT_REASON_JSON__');
Plotly.newPlot('chart-exit-reason', exitReasonSpec.data, exitReasonSpec.layout, {responsive: true});

var exitPnlSpec = JSON.parse('__EXIT_PNL_JSON__');
Plotly.newPlot('chart-exit-pnl', exitPnlSpec.data, exitPnlSpec.layout, {responsive: true});

var monthlyPnlSpec = JSON.parse('__MONTHLY_PNL_JSON__');
Plotly.newPlot('chart-monthly-pnl', monthlyPnlSpec.data, monthlyPnlSpec.layout, {responsive: true});

function applyFilters() {
  var ticker = document.getElementById('filter-ticker').value.toUpperCase();
  var exit = document.getElementById('filter-exit').value;
  var rows = document.querySelectorAll('#trades-tbody tr');
  rows.forEach(function(row) {
    var show = true;
    if (ticker && row.dataset.ticker.indexOf(ticker) === -1) show = false;
    if (exit && row.dataset.exit !== exit) show = false;
    row.style.display = show ? '' : 'none';
  });
}

var sortDir = {};
function sortTable(col) {
  var tbody = document.getElementById('trades-tbody');
  var rows = Array.from(tbody.querySelectorAll('tr'));
  sortDir[col] = !sortDir[col];
  rows.sort(function(a, b) {
    var va = a.cells[col] ? a.cells[col].innerText : '';
    var vb = b.cells[col] ? b.cells[col].innerText : '';
    var na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return sortDir[col] ? na - nb : nb - na;
    return sortDir[col] ? va.localeCompare(vb) : vb.localeCompare(va);
  });
  rows.forEach(function(r) { tbody.appendChild(r); });
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_metrics(portfolio_df: pd.DataFrame, trades_df: pd.DataFrame = None) -> dict:
    """
    Returns: {n_trades, total_return_pct, sharpe_ratio, max_drawdown_pct}
    Sharpe = (mean(daily_return) / std(daily_return)) * sqrt(252), rf=0.
    Max drawdown = min((total_value - running_max) / running_max) * 100.
    """
    if portfolio_df.empty:
        return {"n_trades": 0, "total_return_pct": 0.0, "sharpe_ratio": 0.0, "max_drawdown_pct": 0.0}

    daily_returns = portfolio_df["daily_return"]
    total_return_pct = round(float(portfolio_df["cumulative_return"].iloc[-1]) * 100, 2)

    std = daily_returns.std()
    sharpe = round((daily_returns.mean() / std) * math.sqrt(252), 2) if std > 0 else 0.0

    running_max = portfolio_df["total_value"].cummax()
    drawdown = (portfolio_df["total_value"] - running_max) / running_max
    max_dd_pct = round(float(drawdown.min()) * 100, 2)

    n_trades = len(trades_df) if trades_df is not None else 0

    return {
        "n_trades": n_trades,
        "total_return_pct": total_return_pct,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd_pct,
    }


def save_report(
    run_id: str,
    config_dict: dict,
    metrics: dict,
    trades_df: pd.DataFrame,
    portfolio_df: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Generate report.html. Returns path to the file."""
    chart1_json = _build_daily_return_chart(portfolio_df)
    chart2_json = _build_total_value_chart(portfolio_df, config_dict.get("initial_capital", 500_000))
    trades_html = _render_trades_table(trades_df)

    trade_metrics = _compute_trade_metrics(trades_df)
    return_dist_json = _build_return_dist_chart(trades_df)
    exit_reason_json = _build_exit_reason_chart(trades_df)
    exit_pnl_json = _build_exit_pnl_chart(trades_df)
    monthly_pnl_json = _build_monthly_pnl_chart(trades_df)

    html_content = _render_html(
        run_id=run_id,
        config_dict=config_dict,
        metrics=metrics,
        chart1_json=chart1_json,
        chart2_json=chart2_json,
        trades_html=trades_html,
        trade_metrics=trade_metrics,
        return_dist_json=return_dist_json,
        exit_reason_json=exit_reason_json,
        exit_pnl_json=exit_pnl_json,
        monthly_pnl_json=monthly_pnl_json,
    )

    out_path = Path(output_dir) / "report.html"
    out_path.write_text(html_content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _compute_trade_metrics(trades_df: pd.DataFrame) -> dict:
    """Compute win rate, profit factor, payoff ratio, max consecutive losses."""
    if trades_df.empty:
        return {
            "win_rate": "—", "win_rate_class": "neutral",
            "profit_factor": "—", "profit_factor_class": "neutral",
            "payoff_ratio": "—",
            "max_consec_losses": "—",
        }

    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] < 0]

    win_rate = len(wins) / len(trades_df) * 100
    win_rate_str = f"{win_rate:.1f}%"
    win_rate_class = "positive" if win_rate >= 50 else "negative"

    if len(losses) > 0 and losses["pnl"].sum() != 0:
        pf = wins["pnl"].sum() / abs(losses["pnl"].sum())
        profit_factor_str = f"{pf:.2f}"
        profit_factor_class = "positive" if pf >= 1.0 else "negative"
    else:
        profit_factor_str = "∞"
        profit_factor_class = "positive"

    if len(wins) > 0 and len(losses) > 0:
        pr = wins["pnl_pct"].mean() / abs(losses["pnl_pct"].mean())
        payoff_ratio_str = f"{pr:.2f}"
    else:
        payoff_ratio_str = "—"

    pnl_sorted = trades_df.sort_values("entry_date")["pnl"].tolist()
    is_loss = [v < 0 for v in pnl_sorted]
    max_consec = max(
        (sum(1 for _ in g) for k, g in itertools.groupby(is_loss) if k),
        default=0,
    )

    return {
        "win_rate": win_rate_str,
        "win_rate_class": win_rate_class,
        "profit_factor": profit_factor_str,
        "profit_factor_class": profit_factor_class,
        "payoff_ratio": payoff_ratio_str,
        "max_consec_losses": str(max_consec),
    }


def _build_return_dist_chart(trades_df: pd.DataFrame) -> str:
    fig = go.Figure()
    if not trades_df.empty:
        pct_values = (trades_df["pnl_pct"] * 100).tolist()
        p5 = trades_df["pnl_pct"].quantile(0.05) * 100
        p95 = trades_df["pnl_pct"].quantile(0.95) * 100
        fig.add_trace(go.Histogram(
            x=pct_values,
            nbinsx=30,
            marker_color="#3b82f6",
            name="Return",
        ))
        fig.add_vline(x=p5, line_dash="dash", line_color="#f59e0b",
                      annotation_text=f"P5: {p5:.1f}%", annotation_position="top right")
        fig.add_vline(x=p95, line_dash="dash", line_color="#22c55e",
                      annotation_text=f"P95: {p95:.1f}%", annotation_position="top left")
    fig.update_layout(
        title="Return Distribution",
        template="plotly_dark",
        height=300,
        xaxis_title="Return (%)",
        xaxis_ticksuffix="%",
        showlegend=False,
        margin=dict(l=48, r=16, t=48, b=48),
    )
    return _safe_json(fig)


def _build_exit_reason_chart(trades_df: pd.DataFrame) -> str:
    fig = go.Figure()
    if not trades_df.empty:
        counts = trades_df["exit_reason"].value_counts()
        fig.add_trace(go.Bar(
            x=counts.index.tolist(),
            y=counts.values.tolist(),
            marker_color="#3b82f6",
        ))
    fig.update_layout(
        title="Exit Reason Distribution",
        template="plotly_dark",
        height=300,
        xaxis_title="Exit Reason",
        yaxis_title="# Trades",
        showlegend=False,
        margin=dict(l=48, r=16, t=48, b=48),
    )
    return _safe_json(fig)


def _build_exit_pnl_chart(trades_df: pd.DataFrame) -> str:
    fig = go.Figure()
    if not trades_df.empty:
        reason_pnl = trades_df.groupby("exit_reason")["pnl_pct"].mean() * 100
        colors = ["#22c55e" if v >= 0 else "#ef4444" for v in reason_pnl.values]
        fig.add_trace(go.Bar(
            x=reason_pnl.index.tolist(),
            y=reason_pnl.values.tolist(),
            marker_color=colors,
        ))
    fig.update_layout(
        title="Avg Return by Exit Reason",
        template="plotly_dark",
        height=300,
        xaxis_title="Exit Reason",
        yaxis_ticksuffix="%",
        showlegend=False,
        margin=dict(l=48, r=16, t=48, b=48),
    )
    return _safe_json(fig)


def _build_monthly_pnl_chart(trades_df: pd.DataFrame) -> str:
    fig = go.Figure()
    if not trades_df.empty:
        df = trades_df.copy()
        df["month"] = pd.to_datetime(df["entry_date"]).dt.to_period("M").astype(str)
        monthly = df.groupby("month")["pnl"].sum()
        colors = ["#22c55e" if v >= 0 else "#ef4444" for v in monthly.values]
        fig.add_trace(go.Bar(
            x=monthly.index.tolist(),
            y=monthly.values.tolist(),
            marker_color=colors,
        ))
    fig.update_layout(
        title="Monthly P&L ($)",
        template="plotly_dark",
        height=300,
        xaxis_title="Month",
        yaxis_tickprefix="$",
        showlegend=False,
        margin=dict(l=64, r=16, t=48, b=48),
    )
    return _safe_json(fig)


def _build_daily_return_chart(portfolio_df: pd.DataFrame) -> str:
    if portfolio_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Daily Return (%)", template="plotly_dark", height=300)
        return _safe_json(fig)

    returns = portfolio_df["daily_return"] * 100
    colors = ["#22c55e" if r >= 0 else "#ef4444" for r in returns]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=portfolio_df["date"].tolist(),
        y=returns.tolist(),
        marker_color=colors,
        name="Daily Return",
    ))
    fig.update_layout(
        title="Daily Return (%)",
        template="plotly_dark",
        height=320,
        xaxis_title="Date",
        yaxis_ticksuffix="%",
        margin=dict(l=48, r=16, t=48, b=48),
    )
    return _safe_json(fig)


def _build_total_value_chart(portfolio_df: pd.DataFrame, initial_capital: float) -> str:
    if portfolio_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Total Portfolio Value ($)", template="plotly_dark", height=300)
        return _safe_json(fig)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio_df["date"].tolist(),
        y=portfolio_df["total_value"].tolist(),
        mode="lines",
        line=dict(color="#3b82f6", width=2),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.12)",
        name="Portfolio Value",
    ))
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="#94a3b8",
        annotation_text="Initial Capital",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title="Total Portfolio Value ($)",
        template="plotly_dark",
        height=320,
        xaxis_title="Date",
        yaxis_tickprefix="$",
        margin=dict(l=64, r=16, t=48, b=48),
    )
    return _safe_json(fig)


def _render_trades_table(trades_df: pd.DataFrame) -> str:
    if trades_df.empty:
        return "<tr><td colspan='15' style='text-align:center;color:#94a3b8'>No trades</td></tr>"

    rows = []
    for _, row in trades_df.iterrows():
        ticker = html.escape(str(row.get("ticker", "")))
        exit_reason = html.escape(str(row.get("exit_reason", "")))
        pnl = float(row.get("pnl", 0))
        pnl_class = "pnl-pos" if pnl >= 0 else "pnl-neg"
        pnl_pct = float(row.get("pnl_pct", 0)) * 100

        rows.append(
            f'    <tr data-ticker="{ticker}" data-exit="{exit_reason}">'
            f'<td>{ticker}</td>'
            f'<td>{html.escape(str(row.get("company_name", "")))}</td>'
            f'<td>{html.escape(str(row.get("industry", "")))}</td>'
            f'<td>{html.escape(str(row.get("entry_date", "")))}</td>'
            f'<td>{html.escape(str(row.get("exit_date", "")))}</td>'
            f'<td>{float(row.get("entry_price", 0)):.4f}</td>'
            f'<td>{float(row.get("exit_price", 0)):.4f}</td>'
            f'<td>{int(row.get("shares", 0))}</td>'
            f'<td class="{pnl_class}">{pnl:+.2f}</td>'
            f'<td class="{pnl_class}">{pnl_pct:+.2f}%</td>'
            f'<td>{int(row.get("days_held", 0))}</td>'
            f'<td>{exit_reason}</td>'
            f'<td>{float(row.get("os_prev", 0)):.4f}</td>'
            f'<td>{float(row.get("dr_prev", 0)):.4f}</td>'
            f'<td>{float(row.get("dv_prev", 0)):.4f}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _render_html(
    run_id: str,
    config_dict: dict,
    metrics: dict,
    chart1_json: str,
    chart2_json: str,
    trades_html: str,
    trade_metrics: dict,
    return_dist_json: str,
    exit_reason_json: str,
    exit_pnl_json: str,
    monthly_pnl_json: str,
) -> str:
    total_ret = metrics.get("total_return_pct", 0)
    sharpe = metrics.get("sharpe_ratio", 0)
    max_dd = metrics.get("max_drawdown_pct", 0)
    n_trades = metrics.get("n_trades", 0)

    return_class = "positive" if total_ret >= 0 else "negative"
    sharpe_class = "positive" if sharpe >= 1.0 else ("neutral" if sharpe >= 0 else "negative")

    def _esc_json(j: str) -> str:
        return j.replace("\\", "\\\\").replace("'", "\\'")

    config_pretty = json.dumps(config_dict, indent=2)

    content = _HTML_TEMPLATE
    content = content.replace("__RUN_ID__", html.escape(run_id))
    content = content.replace("__TOTAL_RETURN__", f"{total_ret:+.2f}%")
    content = content.replace("__SHARPE_RATIO__", f"{sharpe:.2f}")
    content = content.replace("__MAX_DRAWDOWN__", f"{max_dd:.2f}%")
    content = content.replace("__N_TRADES__", str(n_trades))
    content = content.replace("__RETURN_CLASS__", return_class)
    content = content.replace("__SHARPE_CLASS__", sharpe_class)
    content = content.replace("__WIN_RATE__", trade_metrics["win_rate"])
    content = content.replace("__WIN_RATE_CLASS__", trade_metrics["win_rate_class"])
    content = content.replace("__PROFIT_FACTOR__", trade_metrics["profit_factor"])
    content = content.replace("__PROFIT_FACTOR_CLASS__", trade_metrics["profit_factor_class"])
    content = content.replace("__PAYOFF_RATIO__", trade_metrics["payoff_ratio"])
    content = content.replace("__MAX_CONSEC_LOSSES__", trade_metrics["max_consec_losses"])
    content = content.replace("__DAILY_RETURN_JSON__", _esc_json(chart1_json))
    content = content.replace("__TOTAL_VALUE_JSON__", _esc_json(chart2_json))
    content = content.replace("__RETURN_DIST_JSON__", _esc_json(return_dist_json))
    content = content.replace("__EXIT_REASON_JSON__", _esc_json(exit_reason_json))
    content = content.replace("__EXIT_PNL_JSON__", _esc_json(exit_pnl_json))
    content = content.replace("__MONTHLY_PNL_JSON__", _esc_json(monthly_pnl_json))
    content = content.replace("__TRADES_ROWS__", trades_html)
    content = content.replace("__CONFIG_JSON__", html.escape(config_pretty))
    return content


def _safe_json(fig: go.Figure) -> str:
    """Serialize Plotly figure to JSON string."""
    return fig.to_json()

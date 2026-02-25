"""
Generate interactive HTML5 report from backtest results.

Public API:
    compute_metrics(portfolio_df, trades_df) -> dict
    save_report(run_id, config_dict, metrics, trades_df, portfolio_df, output_dir) -> Path
"""

import html
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

    html_content = _render_html(
        run_id=run_id,
        config_dict=config_dict,
        metrics=metrics,
        chart1_json=chart1_json,
        chart2_json=chart2_json,
        trades_html=trades_html,
    )

    out_path = Path(output_dir) / "report.html"
    out_path.write_text(html_content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

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
    # Initial capital reference line
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
) -> str:
    total_ret = metrics.get("total_return_pct", 0)
    sharpe = metrics.get("sharpe_ratio", 0)
    max_dd = metrics.get("max_drawdown_pct", 0)
    n_trades = metrics.get("n_trades", 0)

    return_class = "positive" if total_ret >= 0 else "negative"
    sharpe_class = "positive" if sharpe >= 1.0 else ("neutral" if sharpe >= 0 else "negative")

    # Escape the JSON strings so they can be safely embedded in JS string literals
    chart1_escaped = chart1_json.replace("\\", "\\\\").replace("'", "\\'")
    chart2_escaped = chart2_json.replace("\\", "\\\\").replace("'", "\\'")

    config_pretty = json.dumps(config_dict, indent=2)

    content = _HTML_TEMPLATE
    content = content.replace("__RUN_ID__", html.escape(run_id))
    content = content.replace("__TOTAL_RETURN__", f"{total_ret:+.2f}%")
    content = content.replace("__SHARPE_RATIO__", f"{sharpe:.2f}")
    content = content.replace("__MAX_DRAWDOWN__", f"{max_dd:.2f}%")
    content = content.replace("__N_TRADES__", str(n_trades))
    content = content.replace("__RETURN_CLASS__", return_class)
    content = content.replace("__SHARPE_CLASS__", sharpe_class)
    content = content.replace("__DAILY_RETURN_JSON__", chart1_escaped)
    content = content.replace("__TOTAL_VALUE_JSON__", chart2_escaped)
    content = content.replace("__TRADES_ROWS__", trades_html)
    content = content.replace("__CONFIG_JSON__", html.escape(config_pretty))
    return content


def _safe_json(fig: go.Figure) -> str:
    """Serialize Plotly figure to JSON string."""
    return fig.to_json()

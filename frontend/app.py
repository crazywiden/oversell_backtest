"""
Oversell Backtest — Streamlit frontend.

Run: streamlit run frontend/app.py

Streamlit secrets required for Google Drive data (configure in Community Cloud UI
or in .streamlit/secrets.toml locally — never commit that file):

  drive_file_id = "your-google-drive-file-id"

  [gcp_service_account]
  type = "service_account"
  project_id = "..."
  private_key_id = "..."
  private_key = "-----BEGIN RSA PRIVATE KEY-----\n..."
  client_email = "..."
  client_id = "..."
  token_uri = "https://oauth2.googleapis.com/token"
"""

import itertools
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.engine_bridge import BacktestParams, run_backtest

st.set_page_config(page_title="Oversell Backtest", layout="centered")
st.title("Oversell Backtest")


# ---------------------------------------------------------------------------
# Google Drive data download (runs once per app session, cached)
# ---------------------------------------------------------------------------
@st.cache_resource
def _get_drive_data() -> "str | None":
    """Download prices.parquet from Google Drive if secrets are configured."""
    try:
        if "gcp_service_account" not in st.secrets:
            return None
    except Exception:
        return None

    import io

    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    local_path = Path("/tmp/prices.parquet")
    if local_path.exists():
        return str(local_path)

    creds = service_account.Credentials.from_service_account_info(
        {k: v for k, v in st.secrets["gcp_service_account"].items()},
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    svc = build("drive", "v3", credentials=creds)
    request = svc.files().get_media(fileId=st.secrets["drive_file_id"])
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    local_path.write_bytes(buf.read())
    return str(local_path)


# ---------------------------------------------------------------------------
# Data path selector
# ---------------------------------------------------------------------------
_repo_root = Path(__file__).resolve().parents[1]
_drive_path = _get_drive_data()
_detected = sorted(str(p.relative_to(_repo_root)) for p in _repo_root.glob("data/*/prices.csv"))
_options = ([_drive_path] if _drive_path else []) + _detected + ["Custom…"]


def _label(p: str) -> str:
    if p == _drive_path:
        return "Google Drive — prices.parquet"
    return p


if "data_path" not in st.session_state:
    st.session_state["data_path"] = _options[0] if _options else "data/v1/prices.csv"

selected = st.selectbox(
    "Dataset",
    _options,
    format_func=_label,
    index=_options.index(st.session_state["data_path"])
    if st.session_state["data_path"] in _options else len(_options) - 1,
)

if selected == "Custom…":
    st.text_input("Custom data path", key="data_path")
else:
    st.session_state["data_path"] = selected

# ---------------------------------------------------------------------------
# Hyperparameter form
# ---------------------------------------------------------------------------
with st.form("backtest_form"):
    st.subheader("Signal Construction")
    col1, col2, col3 = st.columns(3)
    with col1:
        N = st.number_input("N — Lookback days", min_value=5, max_value=100, value=20, step=1)
    with col2:
        w1 = st.number_input("w1 — Return weight", min_value=-5.0, max_value=5.0, value=-1.0, step=0.1, format="%.1f")
    with col3:
        w2 = st.number_input("w2 — Volume weight", min_value=-5.0, max_value=5.0, value=1.0, step=0.1, format="%.1f")

    st.subheader("Position Management")
    col4, col5, col6 = st.columns(3)
    with col4:
        win_take_rate = st.number_input(
            "win_take_rate — Take-profit", min_value=0.01, max_value=0.50, value=0.05, step=0.01, format="%.2f"
        )
    with col5:
        stop_loss_rate = st.number_input(
            "stop_loss_rate — Stop-loss", min_value=0.01, max_value=0.50, value=0.03, step=0.01, format="%.2f"
        )
    with col6:
        K = st.number_input("K — Max hold days", min_value=1, max_value=30, value=5, step=1)

    st.subheader("Universe Filter")
    V = st.number_input(
        "V — Min daily volume", min_value=0, max_value=10_000_000, value=500_000, step=10_000
    )

    st.subheader("Data Filtering")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("Start date", value=None)
    with col_d2:
        end_date = st.date_input("End date", value=None)

    # Cross-field validation warning (non-blocking)
    if stop_loss_rate >= win_take_rate:
        st.warning(
            f"stop_loss_rate ({stop_loss_rate:.2f}) >= win_take_rate ({win_take_rate:.2f}): "
            "most exits will be stop-losses."
        )

    submitted = st.form_submit_button("Run Backtest", type="primary")

# ---------------------------------------------------------------------------
# Run engine
# ---------------------------------------------------------------------------
if submitted:
    params = BacktestParams(
        N=int(N),
        w1=float(w1),
        w2=float(w2),
        win_take_rate=float(win_take_rate),
        stop_loss_rate=float(stop_loss_rate),
        K=int(K),
        V=int(V),
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date) if end_date else None,
        data_path=st.session_state["data_path"],
    )
    progress_bar = st.progress(0.0, text="Starting backtest...")

    def _on_status(msg: str, pct: float) -> None:
        progress_bar.progress(pct, text=msg)

    def _on_progress(i: int, n: int, date, n_positions: int, n_trades: int) -> None:
        # Simulation occupies 25%–90% of the overall pipeline
        pct = 0.25 + 0.65 * (i / n) if n else 0.25
        date_str = str(date)[:10]
        text = (
            f"Simulating {date_str}  ·  Day {i + 1} / {n}"
            f"  ·  {n_positions} open positions"
            f"  ·  {n_trades} trades closed"
        )
        progress_bar.progress(pct, text=text)

    result = run_backtest(params, progress_callback=_on_progress, status_callback=_on_status)
    progress_bar.progress(1.0, text="Done")
    st.session_state["last_result"] = result

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if not result.success:
        st.error(f"Backtest failed: {result.error_message}")
    else:
        st.success(f"Backtest complete in {result.duration_seconds:.1f}s")

        # Key metrics row
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric(
            "Total Return",
            f"{result.total_return_pct:+.2f}%" if result.total_return_pct is not None else "—",
        )
        col_b.metric(
            "Sharpe Ratio",
            f"{result.sharpe_ratio:.2f}" if result.sharpe_ratio is not None else "—",
        )
        col_c.metric(
            "Max Drawdown",
            f"{result.max_drawdown_pct:.2f}%" if result.max_drawdown_pct is not None else "—",
        )
        col_d.metric(
            "Trades",
            str(result.n_trades) if result.n_trades is not None else "—",
        )

        # Report path
        st.markdown("**Report saved to:**")
        st.code(result.report_path)
        st.caption("Open the path above in your browser to view the interactive report.")

        # ---------------------------------------------------------------------------
        # Trade analysis
        # ---------------------------------------------------------------------------
        trades_path = Path(result.report_path).parent / "trades.csv"
        if trades_path.exists():
            trades = pd.read_csv(trades_path)
        else:
            trades = pd.DataFrame()

        if len(trades) > 0:
            st.subheader("Trade Analysis")

            wins = trades[trades["pnl"] > 0]
            losses = trades[trades["pnl"] < 0]

            win_rate = len(wins) / len(trades) * 100

            if len(losses) > 0 and losses["pnl"].sum() != 0:
                profit_factor = wins["pnl"].sum() / abs(losses["pnl"].sum())
                profit_factor_str = f"{profit_factor:.2f}"
            else:
                profit_factor_str = "∞"

            if len(wins) > 0 and len(losses) > 0:
                payoff_ratio = wins["pnl_pct"].mean() / abs(losses["pnl_pct"].mean())
                payoff_ratio_str = f"{payoff_ratio:.2f}"
            else:
                payoff_ratio_str = "—"

            pnl_sorted = trades.sort_values("entry_date")["pnl"]
            is_loss = (pnl_sorted < 0).tolist()
            max_consec = max(
                (sum(1 for _ in g) for k, g in itertools.groupby(is_loss) if k),
                default=0,
            )

            col_e, col_f, col_g, col_h = st.columns(4)
            col_e.metric("Win Rate", f"{win_rate:.1f}%")
            col_f.metric("Profit Factor", profit_factor_str)
            col_g.metric("Payoff Ratio", payoff_ratio_str)
            col_h.metric("Max Consec. Losses", str(max_consec))

            col_l, col_r = st.columns(2)

            with col_l:
                p5 = trades["pnl_pct"].quantile(0.05)
                p95 = trades["pnl_pct"].quantile(0.95)
                fig_hist = px.histogram(
                    trades,
                    x="pnl_pct",
                    nbins=30,
                    title="Return Distribution",
                    labels={"pnl_pct": "Return"},
                )
                fig_hist.update_xaxes(tickformat=".1%")
                fig_hist.update_layout(showlegend=False, height=300, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_hist, use_container_width=True)
                st.caption(f"5th/95th percentile: {p5:.1%} / {p95:.1%}")

            with col_r:
                reason_counts = trades["exit_reason"].value_counts().reset_index()
                reason_counts.columns = ["exit_reason", "count"]
                fig_reason = px.bar(
                    reason_counts,
                    x="exit_reason",
                    y="count",
                    title="Exit Reason Distribution",
                    labels={"exit_reason": "Reason", "count": "# Trades"},
                )
                fig_reason.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_reason, use_container_width=True)

            col_l2, col_r2 = st.columns(2)

            with col_l2:
                reason_pnl = (
                    trades.groupby("exit_reason")["pnl_pct"]
                    .mean()
                    .reset_index()
                    .rename(columns={"pnl_pct": "avg_return"})
                )
                fig_reason_pnl = px.bar(
                    reason_pnl,
                    x="exit_reason",
                    y="avg_return",
                    title="Avg Return by Exit Reason",
                    labels={"exit_reason": "Reason", "avg_return": "Avg Return"},
                    color="avg_return",
                    color_continuous_scale=["red", "lightgray", "green"],
                    color_continuous_midpoint=0,
                )
                fig_reason_pnl.update_yaxes(tickformat=".1%")
                fig_reason_pnl.update_layout(
                    height=300, margin=dict(t=40, b=0, l=0, r=0), showlegend=False
                )
                st.plotly_chart(fig_reason_pnl, use_container_width=True)

            with col_r2:
                trades["month"] = pd.to_datetime(trades["entry_date"]).dt.to_period("M").astype(str)
                monthly = trades.groupby("month")["pnl"].sum().reset_index()
                monthly["color"] = monthly["pnl"].apply(lambda x: "profit" if x >= 0 else "loss")
                fig_monthly = px.bar(
                    monthly,
                    x="month",
                    y="pnl",
                    title="Monthly P&L ($)",
                    labels={"month": "Month", "pnl": "P&L ($)"},
                    color="color",
                    color_discrete_map={"profit": "green", "loss": "red"},
                )
                fig_monthly.update_layout(
                    height=300, margin=dict(t=40, b=0, l=0, r=0), showlegend=False
                )
                st.plotly_chart(fig_monthly, use_container_width=True)

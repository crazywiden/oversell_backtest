"""
Oversell Backtest — Streamlit frontend.

Run: streamlit run frontend/app.py
"""

import streamlit as st

from frontend.engine_bridge import BacktestParams, run_backtest

st.set_page_config(page_title="Oversell Backtest", layout="centered")
st.title("Oversell Backtest")

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
    )
    with st.spinner("Running backtest..."):
        result = run_backtest(params)
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

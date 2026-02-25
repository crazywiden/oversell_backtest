# Second-Round Critical Review: Oversell Strategy v2 — Execution Logic, Risk Management & Backtesting Methodology

**Author**: Senior Quant Researcher (Internal Review)
**Date**: 2026-02-24
**Review Round**: v2 (Second Pass)
**Prior Review**: `review_execution_methodology.md` (v1), `review_signal_quality.md` (v1)
**Status**: Pre-Implementation — Not for Distribution

---

## Preface

This is a second-round peer review of the Oversell Score strategy following a partial specification update (v2). The v1 review identified four critical flaws and six major issues across signal quality and execution methodology. v2 introduced two material changes: (1) the addition of a `sign(r_T)` modifier to $D(r)$, addressing the directional ambiguity identified in `review_signal_quality.md`, and (2) a "large volume" liquidity filter on the universe.

**The central finding of this review is unchanged: the two most dangerous structural problems — survivorship bias and the intraday fill assumption — remain fully unaddressed. A backtest run against v2 is still not trustworthy.** The liquidity filter is a genuine improvement on transaction cost grounds but introduces a new tension with signal quality that v2 does not resolve. This document provides a complete forensic analysis of what changed, what remains broken, and what is newly broken.

---

## Section 1: What Changed in v2 — Execution Impact

### 1a. Liquidity Filter Impact on Transaction Costs

v2 adds a "large volume" filter to the universe. The threshold is not defined — this is immediately flagged as an ambiguity that must be resolved before any code is written. For the purposes of this analysis, two interpretations are evaluated:

**Interpretation A — Mid-cap filter (ADDV > $10M/day)**: Narrows the universe to roughly the top 2,000 liquid U.S. equities. This was the implicit assumption in v1's cost analysis.

**Interpretation B — Large-cap filter (ADDV > $50M/day)**: Narrows the universe to roughly the top 500–800 most liquid equities. The analysis below uses this as the optimistic case.

Under Interpretation B, the revised cost estimate using the square-root market impact model is:

$$\text{Market Impact} \approx \sigma \sqrt{\frac{Q}{ADV}} \approx 0.02 \times \sqrt{\frac{167{,}000}{50{,}000{,}000}} \approx 0.02 \times 0.0578 \approx 11.6 \text{ bps per leg}$$

This is a significant improvement from v1's estimate of 39 bps per leg (based on $10M ADV). The full revised round-trip cost breakdown is:

| Cost Component | v1 Estimate | v2 Estimate (ADDV > $50M) | Notes |
|---|---|---|---|
| Bid-ask spread | 10–20 bps/leg | 2–5 bps/leg | Spread compresses sharply with liquidity |
| Market impact (per leg) | ~39 bps | ~12 bps | Square-root model, $167K order |
| Commission | ~1 bp | ~1 bp | Negligible at IB rates |
| **Round-trip total** | **~100–118 bps** | **~30–36 bps** | |

This is a material reduction — from approximately 110 bps round-trip to approximately 33 bps. For a strategy targeting a 3% take-profit, transaction costs drop from consuming ~37% of gross alpha to ~11%. This meaningfully improves the viability of the strategy **if** the signal still fires reliably on large-volume stocks, which is the central question raised in Section 1b.

Two important qualifications apply. First, the $50M ADDV threshold is the optimistic case. If the actual filter is closer to $5–10M ADDV, the cost improvement is much smaller. The threshold must be stated precisely in the strategy specification. Second, the stocks this strategy targets — those with extreme return deviations and extreme volume deviations — are by definition in an atypical market state on the day of entry. Even for normally liquid stocks, the bid-ask spread and market impact on a high-volume, large-move day will be wider than the typical-day estimates above. A 50% haircut on the liquidity assumption (i.e., treat the entry day as a half-liquidity day) is conservative and appropriate, raising the effective round-trip cost back toward 45–55 bps on entry days.

### 1b. Trade Frequency Impact of the Liquidity Filter — Signal Quality Tension

This is the most important new issue introduced by v2's liquidity filter, and it is not addressed anywhere in the v2 specification.

The OS score is designed to identify stocks with anomalously large price moves accompanied by anomalously large volume. The empirical literature on short-term reversals consistently shows that the strongest mean-reversion signals arise in **smaller, less liquid stocks** — precisely because these names have shallower order books, more volatile price impact from large orders, and a greater incidence of forced selling by unsophisticated market participants. By filtering to large-volume stocks, v2 may be systematically removing the highest-alpha portion of the signal.

There is a specific structural tension in the volume component:

$$D(v)_T = \frac{v_T - \bar{v}_T}{\sigma(v)_T}$$

For a large-cap stock with ADDV of $500M, a day with $700M in volume represents a $D(v)$ of roughly 1.0–2.0 standard deviations above normal. For a small-cap stock with ADDV of $5M, the same proportional volume deviation is structurally harder to achieve because the denominator $\sigma(v)_T$ scales with the typical volume level. However, the absolute dollar volume required to move a small-cap stock's price significantly is much lower, which means genuine forced selling is better captured in illiquid names.

The net result is: **filtering to large-volume stocks trades signal quality for execution quality.** Both matter. The question is whether the net effect (better fills, lower alpha) is better or worse than the unfiltered universe (worse fills, higher alpha). This is an empirical question that must be validated, not assumed. The v2 specification simply applies the filter without any justification of its expected effect on signal frequency or alpha.

Additionally, if the universe contracts significantly — say, from 3,000 eligible stocks to 500 — there will be many trading days where fewer than 3 stocks satisfy the OS threshold at a meaningful level. The strategy then has two options: (a) trade fewer than 3 positions and hold cash, or (b) lower the OS threshold to maintain a full book. Neither option is documented in v2.

**Practical recommendation before v2 is implemented**: Run a signal frequency analysis on the filtered vs. unfiltered universe. Count how many stocks per day have OS scores above a fixed threshold (e.g., OS > 2.0) under each universe definition. If signal frequency drops by more than 40%, the liquidity filter is too aggressive and should be relaxed to ADDV > $10M rather than $50M.

---

## Section 2: Execution Logic Issues — Unchanged from v1, Still Critical

### 2a. Intraday Fill Assumption — Critical, Unresolved

The stop-loss and take-profit exit conditions check whether the target price falls within the day's $[\text{Low}_t, \text{High}_t]$ range and, if so, assume a fill at exactly the target price. This assumption has three distinct problems, none of which were addressed in v2.

**Problem 1 — Gap-through events.** If a stock opens below the stop-loss level — which is disproportionately likely for the distressed stocks this strategy targets — the backtest records a fill at the stop level. In live trading, the fill would be at the open price. The gap loss is:

$$\text{Gap loss per event} = \text{Open}_t - p(1 - \text{stop\_loss\_rate})$$

where this quantity is negative (an additional unmodeled loss). Estimating the frequency: among stocks that have experienced a large single-day decline (the strategy's target universe), overnight gap-downs exceeding the stop level occur on approximately 10–20% of stop events, based on empirical data from short-term reversal studies. With a 2% stop-loss and a gap-down averaging 1–3% beyond the stop level, the expected unmodeled loss per trade is:

$$\text{Expected unmodeled gap loss} = 0.15 \times 0.02 \approx 0.30\% \text{ per trade}$$

At a 5-day average hold and moderate trade frequency, this adds up to 50–150 bps of annual drag that does not appear in the backtest.

**Problem 2 — Ordering ambiguity.** If both $p(1 + \text{win\_take\_rate})$ and $p(1 - \text{stop\_loss\_rate})$ fall within $[\text{Low}_t, \text{High}_t]$ on the same day, the strategy's sequential rule — "check take-profit first" — assumes the price visited the take-profit level before the stop-loss level. This assumption cannot be verified from OHLC data. In a mean-reversion context where the stock opens near the stop level and rallies to the take-profit intraday, the assumption is correct. But for a stock that opens at the prior close, falls to the stop, and then recovers to the take-profit, the assumption produces an optimistic outcome (take-profit fill) when the actual outcome would have been a stop-loss fill.

The bias direction is systematic: the rule always resolves the ambiguous case in favor of the more profitable outcome. This is the definition of backtest overfitting at the execution level.

**Problem 3 — Limit order fill probability.** Even when the target price is within the day's range, a limit order at that exact level does not guarantee a fill. Market microstructure theory gives the probability of a limit order fill, given that the price touches the limit level, as approximately 50% (the "limit order at the touch" result from Parlour, 1998). The backtest assumes 100% fill probability whenever the price is within range. This overstates both take-profit capture rates and stop-loss execution certainty.

**Quantified annual impact from all three problems combined**: Conservatively 80–200 bps of overstated annual performance, depending on win/loss ratio and trade frequency. This is not a rounding error — it can be the difference between a profitable strategy and an unprofitable one.

**Recommended fix**: Use the following hierarchy, applied consistently:
1. Check for gap-through at open: if $\text{Open}_t < p(1 - \text{stop\_loss\_rate})$, fill stop-loss at $\text{Open}_t$.
2. Check for gap-through take-profit: if $\text{Open}_t > p(1 + \text{win\_take\_rate})$, fill take-profit at $\text{Open}_t$.
3. If neither gap condition applies, apply the $[\text{Low}_t, \text{High}_t]$ bracket check with a 50% fill probability adjustment, or assume stop-loss has priority over take-profit when both levels are within range on the same day (the conservative choice).

### 2b. Buying at Close — Workflow Clarification Still Required

The v1 review established that buying at the close of day $T$ using day $T-1$ signals is operationally feasible via MOC orders and contains no look-ahead bias in the signal. This conclusion stands. However, there is a subtle operational nuance that remains unresolved in v2.

The strategy's OS score is computed using returns through day $T-1$. The entry price is the close of day $T$. Since $r_T = \text{Close}_T / \text{Close}_{T-1} - 1$ is used only to compute $OS_T$ (which drives day $T+1$'s decision), not the current day's signal, there is no circular dependency or look-ahead bias in signal computation itself.

However, the practical workflow requires an explicit statement. The correct order of operations is:
1. Close of day $T-1$ prices finalized (4:30 PM ET).
2. Morning of day $T$: compute $OS_{T-1}$ for all stocks using data through $T-1$.
3. By 3:45 PM ET on day $T$: submit MOC buy orders for the top-3 OS stocks not already held.
4. Close of day $T$: fills executed at official closing prices.

Any implementation that computes the signal using intraday data from day $T$ (rather than end-of-day data from $T-1$) introduces look-ahead bias and must be explicitly guarded against in the code.

### 2c. Same-Day Capital Recycling — Re-entry Logic Undefined

When a position exits on day $t$ via take-profit or stop-loss, the strategy redeploys capital at the close of day $t$. The v2 specification does not define the selection logic for the replacement stock, leaving three critical ambiguities:

**Ambiguity 1 — Self-replacement risk.** If the exiting stock still ranks in the top-3 by OS score on day $t$ (computed using $t-1$ data), should it be re-entered? Buying back into a stock that just hit a stop-loss is economically incoherent: the stop-loss was triggered because the mean-reversion thesis was invalidated (or at least interrupted). Re-entry into the same stock violates the strategy's own risk logic. The specification must explicitly state that the exiting stock is excluded from re-entry on the same day.

**Ambiguity 2 — Rank recalculation.** The OS rankings are computed once per day using $T-1$ data. A position that exits at 10:30 AM does not trigger a new ranking computation. The replacement candidate comes from the pre-computed day-$t$ ranking, excluding currently held names and the exiting stock. This is correct behavior but must be explicitly documented.

**Ambiguity 3 — Cash drag in no-replacement scenarios.** If the pre-computed ranking has no qualifying candidates beyond the 3 currently held positions (or 2 remaining after an exit), the recycled capital sits as cash until the next day's ranking. This cash drag is real and must be modeled. The backtest should not assume 100% capital deployment at all times.

---

## Section 3: Risk Management — Revised Analysis

### 3a. Stop-Loss / Take-Profit Calibration with Volume Filter

With a large-cap universe (ADDV > $50M), typical daily volatility is approximately 1.5–2% (lower than the 2–3% assumed in v1 for small/mid-caps). This changes the probability calculus for the stop-loss and take-profit levels.

For a stock with daily volatility $\sigma_d = 1.75\%$ and a 5-day hold, assuming the returns are approximately i.i.d. (a simplification that ignores autocorrelation but is adequate for order-of-magnitude analysis):

The expected per-trade P&L is:

$$\mathbb{E}[\text{PnL per trade}] = p_w \cdot \text{win\_take\_rate} - p_l \cdot \text{stop\_loss\_rate} - \text{TC}$$

where $p_w + p_l \approx 1$ for trades exiting via TP or SL (ignoring max-hold exits). The break-even condition on win rate, given the ratio $R = \text{win\_take\_rate} / \text{stop\_loss\_rate}$, is:

$$p_w^{\min} = \frac{1}{1 + R}$$

For a 3% take-profit and 2% stop-loss ($R = 1.5$): break-even win rate is $1 / 2.5 = 40\%$.

For a 3% take-profit and 2% stop-loss with 33 bps round-trip costs, the cost-adjusted break-even is:

$$p_w^{\min} \approx \frac{\text{stop\_loss\_rate} + \text{TC}}{\text{win\_take\_rate} + \text{stop\_loss\_rate}} = \frac{0.02 + 0.0033}{0.03 + 0.02} = \frac{0.0233}{0.05} \approx 46.6\%$$

This is a much more comfortable threshold than the v1 estimate of ~50% (due to lower costs under the liquidity filter). Short-term reversal strategies in the academic literature routinely achieve 55–65% win rates on oversold signals, which provides a margin above the 46.6% break-even.

However, the analysis shifts if the 10–20% gap-through adjustment is applied. With gap-throughs increasing effective stop-loss cost by ~0.3% per trade, the cost-adjusted break-even rises to approximately 48–50%, which begins to encroach on the realistic win rate range. This again reinforces that the gap-through problem in Section 2a is not cosmetic — it materially affects the strategy's economic viability.

The sensitivity of expected P&L to the win rate is:

$$\frac{\partial \mathbb{E}[\text{PnL}]}{\partial p_w} = \text{win\_take\_rate} + \text{stop\_loss\_rate} = 0.03 + 0.02 = 0.05$$

Every percentage point increase in win rate adds 5 bps of expected PnL per trade. This is a shallow gradient, meaning the strategy's profitability is not hypersensitive to win rate, but it also means the cushion above break-even must be consistently positive — a single regime shift that drops the win rate from 58% to 45% turns the strategy from modestly profitable to loss-making.

### 3b. Maximum Drawdown Analysis — Concentrated Portfolio Scenario

With 3 equal-weight positions and a $500K portfolio, each position carries approximately $167K. The worst-case sequence for the strategy is correlated stop-outs across all positions.

**Single-day worst case (all 3 stop out simultaneously):**

$$\text{Daily portfolio loss} = \frac{1}{3} \times \text{stop\_loss\_rate} \times 3 = \text{stop\_loss\_rate}$$

With stop\_loss\_rate = 2% and gap-through risk (effective stop = 3%): single-day portfolio loss = 2–3%.

**Multi-day drawdown cascade (replacement stocks also stop out):**

If the strategy repeatedly enters new positions from the OS-top ranking, and the market environment continues to produce failed mean-reversions (e.g., a sector is in a sustained downtrend), the cascade loss over $K$ days is:

| Day | Portfolio Loss (2% stop, no gap) | Cumulative |
|-----|----------------------------------|------------|
| 1 | 2.0% | 2.0% |
| 2 | 2.0% × 0.98 = 1.96% | 3.96% |
| 3 | 1.92% | 5.88% |
| 4 | 1.88% | 7.76% |
| 5 | 1.84% | 9.60% |

After 5 consecutive total stop-outs with capital recycling into new positions, the portfolio has lost approximately 9.6% (geometric compounding). This is the best-case scenario; with gap-throughs and 3% effective losses, the 5-day sequence produces approximately 14% portfolio drawdown.

In practice, the 2020 COVID crash period (February 24 – March 20, 2020) would have triggered near-daily stop-outs for a strategy of this type, with no successful mean-reversions. Over 20 trading days, the cumulative portfolio loss at 2% stop-outs with recycling could reach **30–40%**. The strategy has no portfolio-level circuit breaker — no rule that says "if drawdown exceeds X%, stop trading." This is an operational risk that the v2 specification does not address.

**Recommendation**: Add a portfolio-level drawdown stop at 15–20% (halt new entries until the portfolio recovers to, say, 10% below peak). This preserves capital during regime breaks and reduces the severity of drawdown sequences.

### 3c. Tail Risk — Gap-Downs and Fraud/Catalyst Events

The strategy systematically buys stocks that just experienced large declines on large volume. This population includes a disproportionate share of:

1. **Genuine forced-selling dislocations** (mean-reversion opportunity, the target case)
2. **Earnings catastrophes** — sustained repricing, not mean reversion
3. **Fraud disclosures** — stock eventually approaches zero (Wirecard, Luckin Coffee style events)
4. **Regulatory/legal actions** — often sustained, multi-month declines
5. **Industry disruption** — competitor announcements that permanently impair the business

The stop-loss limits the theoretical maximum loss to stop\_loss\_rate per position. But for cases 2–5 above, gap-through risk is maximal — these events often produce overnight gaps of 10–40% that completely bypass the stop-loss level. For a position in a fraudulent company, the gap loss is not bounded by the stop level; it can be the entire position.

A rough empirical estimate: in any given year, approximately 1–3% of S&P 500 companies experience a single-day decline of more than 20% (earnings catastrophes, fraud revelations, etc.). For the broader liquid universe, the rate is higher. If the strategy makes approximately 150 trades per year (3 positions × 50 full turns) and 2% of those trades are "disaster" events with a 20% gap-down:

$$\text{Annual disaster loss} \approx 0.02 \times 150 \times \frac{1}{3} \times 0.20 \approx 2.0\% \text{ of portfolio}$$

This is material but not catastrophic by itself. Combined with gap-throughs at the stop level, the total tail risk contribution is approximately 2–4% of annual portfolio value — a persistent drag that does not appear in the headline backtest numbers unless gap-through modeling is implemented.

**Minimum mitigation**: Exclude stocks with earnings announcements within 2 days (either side) of the signal date. This eliminates the single largest source of discontinuous gap-down events in the target population.

---

## Section 4: Backtesting Methodology — Unchanged Critical Gaps

### 4a. Survivorship Bias — Still Critical, Still Unresolved

v2 made no changes to address survivorship bias. This remains a critical flaw. For a strategy that targets stocks with extreme declines:

The survivorship bias mechanism is direct: stocks that experienced extreme declines in 2014–2020 and subsequently went bankrupt or were delisted are excluded from the backtest universe if point-in-time data is not used. These are precisely the "disaster" events that would have produced the worst losses. A backtest using a current-day ticker list will never encounter these outcomes.

Published estimates of survivorship bias in mean-reversion strategies range from 2% to 5% per year of artificial outperformance. Over a 10-year backtest, this inflates the equity curve by 22–63% in cumulative terms — enough to make an unprofitable strategy appear highly profitable.

**Acceptable data sources (must include delisted stocks)**:
- Sharadar via Nasdaq Data Link (~$300/year): Russell 3000 point-in-time constituents, delisted tickers, full corporate action history
- CRSP via WRDS: academic gold standard, expensive
- Polygon.io (institutional tier, ~$200/month): comprehensive ticker history including delistings

**Unacceptable for this strategy**: yfinance, any source that returns only currently-listed tickers, any source that cannot confirm point-in-time universe membership.

This issue is non-negotiable. No backtest result produced without point-in-time universe data should be presented, published, or used to make capital allocation decisions.

### 4b. Walk-Forward Validation Design

The following walk-forward structure is recommended for the 10-year backtest period:

| Phase | Date Range | Purpose |
|-------|-----------|---------|
| Warm-up | 2014-01-01 to 2014-12-31 | Rolling window initialization, no trades |
| In-sample (IS) | 2015-01-01 to 2019-12-31 | Hyperparameter selection, signal validation |
| Out-of-sample (OOS) | 2020-01-01 to 2024-12-31 | True performance evaluation |
| Stress sub-period | 2020-02-20 to 2020-04-30 | COVID crash behavior |
| Bear market sub-period | 2022-01-01 to 2022-12-31 | Sustained mean-reversion failure |

**Critical rule**: The OOS period (2020–2024) must not be examined for parameter tuning at any point during development. Any adjustment made after viewing OOS results converts it into additional IS data and invalidates the test. This rule is routinely violated — even casually glancing at the equity curve before finalizing parameters constitutes contamination.

IS and OOS metrics must be reported separately in any strategy presentation. If OOS Sharpe is more than 50% below IS Sharpe, the strategy is overfit and should not be deployed with real capital.

### 4c. Multiple Testing Correction

v2 did not address the multiple testing problem. The six hyperparameters — $N$, $w_1$, $w_2$, win\_take\_rate, stop\_loss\_rate, $K$ — define a search space that produces a large number of effectively independent strategy configurations. A modest grid:

$$N \in \{10,20,40\}, \quad (w_1, w_2) \in 3 \text{ configs}, \quad \text{TP} \in \{2\%,3\%,5\%\}, \quad \text{SL} \in \{1\%,2\%,3\%\}, \quad K \in \{3,5,7\}$$

yields $3^5 = 243$ combinations. At the standard 5% significance threshold, this grid produces approximately **12 expected false discoveries** — parameter sets that appear statistically significant purely by chance, with no underlying edge.

The correct mitigation is not a statistical correction applied after the fact — it is a commitment to a single, economically motivated parameter set before running any backtest. This pre-commitment eliminates the multiple testing problem entirely by construction.

**Economically motivated default configuration:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| $N$ | 20 | One trading month; consistent with short-term reversal literature |
| $w_1$ | -1.0 (relative) | Negative weight if $D(r)$ is signed — low (negative) score = oversold |
| $w_2$ | 1.0 (relative) | High volume deviation reinforces the oversell thesis |
| win\_take\_rate | 0.03 | 3% consistent with 1–5 day reversal magnitudes |
| stop\_loss\_rate | 0.02 | 2% stop gives R-ratio of 1.5, break-even at 40% win rate |
| $K$ | 5 | Signal half-life for short-term reversal; alpha largely decays by day 5 |

**Note on $w_1$ sign**: The v2 update adds `sign(r_T)` to the $D(r)$ formula, so $D(r)$ is now negative for large down-moves. To select oversold stocks (most negative returns), the ranking must select stocks with the **lowest** (most negative) $D(r)$ component. If the composite OS score is ranked descending (top 3 highest), then $w_1$ must be negative. If OS is ranked ascending (top 3 lowest), $w_1$ can be positive. This must be specified explicitly and consistently throughout the codebase. Ranking inversion bugs are silent — the backtest will run without errors but will select overbought stocks instead of oversold ones.

Run this un-tuned configuration first. If it shows no alpha after costs, no amount of hyperparameter optimization will rescue the strategy — it will only produce a false positive.

---

## Section 5: Report Requirements Analysis

### 5a. Required Metrics — Completeness Check

The v2 specification includes: daily return curve, total asset curve, total return, Sharpe ratio, max drawdown, and a trade log. This is insufficient for any serious strategy assessment. The following metrics are required additions:

**Risk-adjusted performance:**
- **Sortino ratio**: $\text{Sortino} = \frac{\bar{R}_p - R_f}{\sigma_{\text{downside}}} \cdot \sqrt{252}$ — penalizes only downside volatility; more appropriate for a strategy with a fixed take-profit cap (asymmetric return profile)
- **Calmar ratio**: $\text{Calmar} = \frac{\text{CAGR}}{|\text{MDD}|}$ — links compounded return to worst-case scenario; the primary metric for fund manager assessment
- **Rolling 6-month Sharpe**: reveals regime dependency; a strategy with high full-period Sharpe but near-zero rolling Sharpe in 2022 is regime-dependent

**Trade-level diagnostics:**
- **Win rate**: fraction of trades exiting via take-profit vs. stop-loss vs. max-hold (reported separately for each exit type)
- **Average win / average loss ratio**: validates the risk/reward assumptions embedded in the TP/SL calibration
- **Profit factor**: gross profit / gross loss; must exceed 1.5 to be viable after realistic costs
- **Average holding period**: mean days from entry to exit; directly converts to annualized turnover and transaction cost drag
- **Exit mechanism breakdown**: % TP / % SL / % max-hold. If max-hold exits dominate, the TP and SL levels are too tight/wide relative to actual price behavior

**Portfolio-level diagnostics:**
- **Benchmark comparison (SPY total return)**: without a benchmark, there is no context for performance; alpha and beta vs. SPY must be reported
- **Annual turnover**: total notional traded / AUM; converts directly to annual cost drag
- **Monthly return heatmap**: year × month grid; immediately identifies crisis periods and seasonal patterns
- **Drawdown chart over time**: not just the max drawdown number, but the time series of drawdown depth

### 5b. Trade Log — Additional Required Columns

The v2 trade log should include the following additions beyond what is currently specified:

| Column | Description |
|--------|-------------|
| exit\_date | Date position was closed |
| exit\_price | Actual fill price at exit |
| exit\_reason | "take\_profit" / "stop\_loss" / "max\_hold" |
| holding\_days | Calendar days from entry to exit |
| gross\_return\_pct | (exit\_price / entry\_price - 1) × 100 |
| estimated\_tc\_bps | Round-trip transaction cost estimate in basis points |
| net\_return\_pct | Gross return minus estimated transaction costs |
| gap\_flag | Boolean: did exit gap through the target level? |

The `gap_flag` column is particularly important for auditing the fill assumption. Reviewing trades where `gap_flag = True` allows the researcher to quantify actual gap-through frequency and loss versus the modeled assumption.

### 5c. Interactive HTML Report — Implementation

For the HTML5 interactive report, the recommended approach is Plotly with a single-file HTML export:

```python
fig.write_html("strategy_report.html", include_plotlyjs='cdn')
```

This produces a self-contained file that can be emailed or shared without a server. All charts should use `plotly.graph_objects` for the full API (hover templates, subplots, secondary axes). Key charts to include beyond the basics: equity curve with drawdown subplot, rolling 12-month Sharpe, monthly return heatmap (`go.Heatmap`), return distribution histogram with normal overlay, and a scatter plot of OS score vs. forward 5-day return (to validate signal quality visually).

---

## Section 6: Operational Readiness Assessment

### 6a. Data Requirements Checklist

| Data Item | Minimum Acceptable Source | Notes |
|-----------|--------------------------|-------|
| OHLCV with delistings | Sharadar, CRSP, Polygon.io | yfinance is NOT acceptable |
| Point-in-time universe | Sharadar or CRSP | Critical for survivorship bias |
| Split + dividend adjustments | Same source | Use point-in-time factors |
| Company name / sector | GICS via same source | Required for trade log and concentration monitoring |
| Earnings dates | FactSet, Bloomberg, or Nasdaq Data Link | Required for catalyst filter |
| VIX daily | CBOE or any OHLCV provider | Required for regime filter (recommended) |

### 6b. Pre-Launch Validation Checklist

Before the first backtest run is presented to any stakeholder:

- [ ] Point-in-time universe confirmed (delisted stocks included)
- [ ] Gap-through handling implemented (open price check before range check)
- [ ] Stop-loss ordering ambiguity resolved (stop has priority when both TP and SL are in range, OR gap-open check handles it)
- [ ] Self-replacement exclusion implemented (exiting stock excluded from same-day re-entry)
- [ ] Walk-forward structure locked (IS ends 2019-12-31; OOS not touched until development is complete)
- [ ] Single un-optimized parameter set run first
- [ ] Transaction costs implemented from day one (not added as an afterthought)
- [ ] IS and OOS metrics reported separately

---

## Section 7: Summary — v1 vs. v2 Issue Status

The following table captures every issue identified across the two prior reviews and its current status after v2:

| Issue | Severity | v1 Status | v2 Change | v2 Status |
|-------|----------|-----------|-----------|-----------|
| Directional ambiguity in $D(r)$ — use of $\|r_T\|$ | Critical | Open | Added `sign(r_T)` to formula | Partially fixed — ranking inversion risk ($w_1$ sign) remains unspecified |
| Intraday fill assumption (gap-throughs, order precedence) | Critical | Open | No change | Still open |
| Survivorship bias — no point-in-time universe | Critical | Open | No change | Still open |
| Multiple testing — 6 unconstrained hyperparameters | Critical | Open | No change | Still open |
| Liquidity filter — universe undefined | Major | Open | Added "large volume" text | Partially addressed — threshold undefined |
| Transaction costs — v1 estimate ~110 bps round-trip | Major | Open | Liquidity filter reduces costs | Partially addressed — conditional on threshold being $50M+ ADDV |
| Same-day capital recycling — re-entry logic undefined | Major | Open | No change | Still open |
| No regime filter (bear market / crisis exposure) | Major | Open | No change | Still open |
| Volume absolute value redundant | Minor | Open | No change | Still open |
| Log transformation missing from $D(v)$ | Minor | Open | No change | Still open |
| Non-robust statistics (mean/std vs. median/MAD) | Minor | Open | No change | Still open |
| No catalyst filter (earnings window) | Major | Open | No change | Still open |
| Walk-forward structure not defined | Major | Open | No change | Still open |
| Missing report metrics (Sortino, Calmar, win rate, etc.) | Major | Open | No change | Still open |
| Benchmark comparison absent from report | Major | Open | No change | Still open |

**New issues introduced in v2:**

| New Issue | Severity | Description |
|-----------|----------|-------------|
| $w_1$ sign ambiguity post-`sign(r_T)` update | Critical | With signed $D(r)$, the ranking direction depends on $w_1$'s sign; a positive $w_1$ with descending sort selects overbought stocks, not oversold. Unspecified. |
| Signal frequency degradation from liquidity filter | Major | Large-volume filter may eliminate most OS signals; no frequency analysis conducted before applying filter |
| Filter threshold undefined | Major | "Large volume" has no quantitative definition; different interpretations produce cost estimates ranging from 33 bps to 110 bps round-trip |

---

## Conclusion

v2 is a meaningful but insufficient update. The directional ambiguity fix (`sign(r_T)`) is the right direction on signal quality, but it introduces a new silent bug risk in the ranking direction that must be explicitly resolved. The liquidity filter is a genuine improvement on transaction cost grounds but carries an unquantified cost to signal frequency and alpha.

The two most dangerous structural problems — survivorship bias and intraday fill assumption — are unchanged and unaddressed. A backtest produced under v2 without fixing these issues will generate numbers that are optimistic by at least 250–450 bps annually (200–300 bps from survivorship bias plus 50–150 bps from fill assumption optimism). These are not conservative estimates. They are the expected magnitude of bias under normal market conditions, before any tail events are encountered.

**The implementation team should not write a single line of backtest engine code until the following four items are resolved:**

1. Point-in-time data source secured and integrated
2. Gap-through fill logic implemented in the exit handler
3. $w_1$ sign and ranking direction explicitly locked down with a unit test
4. Walk-forward validation boundary locked with a commitment not to examine OOS data during development

Any backtest results presented without these four items resolved should be treated as illustrative fiction, not as evidence of a viable trading strategy.

---

*This review was conducted as a second-round pre-implementation peer review. It supersedes the v1 execution review where conclusions differ, and should be read in conjunction with `review_execution_methodology.md` (v1) and `review_signal_quality.md` (v1).*

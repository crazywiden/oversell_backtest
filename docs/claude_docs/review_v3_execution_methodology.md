# Third-Round Critical Review: Oversell Strategy v3 — Execution Logic, Risk Management & Backtesting Methodology

**Author**: Senior Quant Researcher (Internal Review)
**Date**: 2026-02-24
**Review Round**: v3 (Third Pass)
**Prior Reviews**: `review_execution_methodology.md` (v1), `review_v2_execution_methodology.md` (v2), `review_signal_quality.md` (v1), `review_v2_signal_quality.md` (v2)
**Status**: Pre-Implementation — Not for Distribution

---

## Preface

This is a third-round peer review of the Oversell Score strategy following the v3 specification update. Two prior review cycles identified a total of 15 distinct issues across signal quality, execution logic, and backtesting methodology. v3 introduces a substantive redesign of the exit logic — the 4-step hierarchical exit system — which directly addresses the gap-through fill problem flagged as critical since v1. This is the most consequential fix in any review cycle to date.

However, the fix introduces one new methodological problem (the stochastic fill model) and leaves six issues, including two critical ones, fully unresolved. This document provides a forensic assessment of the v3 exit redesign, a revised transaction cost model, updated risk and drawdown analysis, and a complete issue tracker spanning all three versions.

**The central finding of this review**: The 4-step exit hierarchy is a genuine improvement and correctly repairs the gap-through fill problem. However, the 50% random fill probability in Step 3 introduces non-determinism into the backtest, which is incompatible with rigorous research methodology. The two most dangerous structural problems — survivorship bias and the $w_1$ sign inversion risk — remain fully unaddressed. The strategy is not ready for capital deployment.

---

## Section 1: v2 to v3 Execution Delta — Assessment of the 4-Step Exit Hierarchy

### 1a. Step 1 — Gap-Down Stop-Loss Check

The Step 1 rule reads: if $\text{Open}_t < p(1 - \text{stop\_loss\_rate})$, fill at $\text{Open}_t$.

**Assessment: Correctly specified. This is the primary fix from v1 and v2.** The gap-through problem identified in round one was that the backtest would record a fill at the stop-loss level when the stock had in fact opened far below it. Step 1 resolves this by checking the open price before the intraday range, and using the open price as the actual fill when the gap is confirmed.

One minor boundary condition remains: the condition uses strict inequality. If $\text{Open}_t = p(1 - \text{stop\_loss\_rate})$ exactly — the open is precisely at the stop level — the condition does not fire, and the trade falls through to Step 3 for an intraday bracket check. The economically correct behavior is to fill the stop-loss when price equals the stop level, not only when it breaches it. Recommend changing the condition to $\leq$ for the stop-loss (fire when open is at or below the stop) and $\geq$ for the take-profit (fire when open is at or above the target). This is a minor precision issue but eliminates an edge case that could appear in real OHLC data without being unrealistic.

### 1b. Step 2 — Gap-Up Take-Profit Check

The Step 2 rule reads: if $\text{Open}_t > p(1 + \text{win\_take\_rate})$, fill at $\text{Open}_t$.

**Assessment: Correctly specified, and importantly, conservative.** When the open exceeds the take-profit target, the actual fill ($\text{Open}_t$) is better than the target price. This means the strategy captures the full gap-up windfall rather than capping the gain at the limit level. In practice, this is consistent with holding a long position overnight — the gap-up benefits the holder, and exiting at open captures the entire gap. No look-ahead bias is introduced since the exit decision is based on observed open data for day $t$, not future intraday data.

The operational note is that this requires a market-at-open exit order submitted before the opening auction. This is feasible via MOC or MOO order types with most prime brokers. The specification is complete and implementable.

### 1c. Step 3 — The 50% Fill Probability: A New Critical Methodology Issue

The Step 3 rule applies the intraday bracket check $[\text{Low}_t, \text{High}_t]$ and applies a 50% fill probability when either exit level falls within this range.

**This is the most significant new issue introduced in v3, and it must be resolved before any backtest is run.**

**The core problem: a valid backtest must be deterministic.** If two researchers run the same strategy on the same data with the same parameters, they must obtain the same result. The 50% random fill model violates this requirement. Every independent run of the backtest will produce a different equity curve, a different Sharpe ratio, a different maximum drawdown, and a different set of exit events. The consequences cascade through the research workflow:

- **Parameter selection is corrupted.** If a grid search across 27 parameter combinations produces Sharpe ratios that vary by $\pm 0.2$ across runs for the same parameter set, the researcher cannot determine whether parameter set A genuinely outperforms parameter set B, or whether A merely had a lucky random seed during the evaluation run.

- **Reported metrics are ambiguous.** Which run's Sharpe do you report? The best one (cherry-picking), the average of many runs (operationally undefined for a trading strategy), or a single representative run (arbitrary)? None of these approaches is satisfactory.

- **Drawdown analysis is unreliable.** The maximum drawdown is a path-dependent statistic: a single run may be lucky or unlucky in its fill outcomes. The "true" maximum drawdown of the strategy is some expectation over fill-path distributions, which is not what a single run reports.

The theoretical grounding for the 50% model is the Parlour (1998) result on limit order execution probability: a limit order submitted at the current best bid or ask fills approximately 50% of the time when price touches the level. However, this result applies specifically to orders at the inside spread, not to resting take-profit or stop-loss orders placed well away from the current market price. For a resting limit order in a position (e.g., a take-profit at $p \times 1.03$ when the stock is currently trading at $p \times 1.005$), the execution probability when price touches the level depends on queue position, order flow asymmetry, and time-of-day effects — not the simple 50% inside-spread result. The theoretical underpinning for 50% in this context is weaker than the specification implies.

**Recommended alternatives, in order of preference:**

| Model | Description | Deterministic | Conservative Bias | Recommendation |
|-------|-------------|:---:|:---:|------|
| Fixed random seed | Keep 50% probability, set `numpy.random.seed(42)` before all simulations | Yes (per run) | Neutral | Acceptable minimum fix — cheap to implement |
| 100% fill when in range | Fill at the target price whenever it is within $[\text{Low}_t, \text{High}_t]$ | Yes | Slightly optimistic | Preferred: standard assumption across most commercial backtesting systems |
| 50% deterministic proxy | When price touches level, fill at the midpoint of target and close | Yes | Moderate | Acceptable: approximates average fill across the distribution |
| Next-day open | When the bracket check triggers, exit at open of day $t+1$ | Yes | Conservative | Most conservative: appropriate for illiquid names or uncertainty analysis |
| 0% fill (gap-only) | Only fill via Steps 1 and 2; otherwise, hold until K-day exit | Yes | Highly conservative | Too conservative for most reasonable stock universes |

**Recommended fix**: Replace the stochastic 50% model with a 100% deterministic fill at the target price when the bracket check fires. This is the standard assumption in Zipline, Backtrader, and most institutional backtesting platforms. Document the assumption explicitly in the strategy specification and note that it produces a slight upward bias in TP capture rates (the backtest wins more TP exits than live trading will achieve). Sensitivity test by re-running with the next-day open model to bound the uncertainty.

If the author has a strong preference for the 50% model for theoretical reasons, the minimum acceptable implementation is a fixed random seed applied at the start of each backtest run, with the seed value logged alongside the results.

### 1d. Step 3 — SL Priority When Both Levels Are in Range

v3 specifies that when both the take-profit and stop-loss levels fall within $[\text{Low}_t, \text{High}_t]$ on the same day, the stop-loss takes priority. **This is correct and appropriately conservative.**

The economic logic is sound: for a mean-reversion strategy, if the stock traded wide enough to visit both the stop level and the target level on the same day, we cannot determine from OHLC data alone which was visited first. Awarding the stop-loss (the pessimistic outcome) is the right choice for an honest backtest. This avoids the v1/v2 problem where TP was always awarded in the ambiguous case, producing systematic upward bias.

Two simpler non-ambiguous cases: if only the SL level is within range (TP level is above High), only the SL fires; if only the TP level is within range (SL level is below Low), only the TP fires. These are unambiguous and presumably handled correctly. No issue.

### 1e. Step 4 — K-Day Count Definition Ambiguity

The specification states: "If held for K days, sell at close." The definition of "held for K days" is ambiguous and must be pinned down precisely.

The canonical definition recommended here: buy at the close of day $T$ (day 0). The position is first tradeable on day $T+1$ (day 1). On day $T+k$, the position has been held for $k$ trading days. The Step 4 condition fires when $k = K$: sell at the close of day $T+K$.

Under this definition with $K=5$: the position enters at the close of day $T$, is checked on days $T+1, T+2, T+3, T+4$, and is forcibly closed at the close of $T+5$. The position is held for exactly 5 trading days. This is the most natural and unambiguous interpretation.

Three explicit clarifications the specification must include:
1. Is $K$ counted in trading days or calendar days? Trading days is strongly preferred; calendar days would produce variable holding periods across holiday-adjacent periods.
2. On the K-th day, are Steps 1–3 still applied before Step 4? The answer should be yes — if the stock gaps down on day $T+K$, exit at the gap-down open, not the close. The K-day exit is a fallback to prevent indefinite holds, not a scheduled event that overrides protective stops.
3. What happens if day $T+K$ is a trading halt or the stock is suspended? The spec should specify next-business-day close as the fallback.

The current behavior implied by "applied each trading day $t \geq T+1$" suggests Steps 1–3 are checked before Step 4, which is correct. This should be made explicit rather than implied.

---

## Section 2: Transaction Costs — Revised Analysis with the V Filter

### 2a. Dollar Volume Filter Impact on Cost Structure

The v3 specification names $V$ (minimum daily volume) as a hyperparameter but does not quantify it. For this analysis, the reference threshold is ADDV > $50M (approximately the top 500–800 most liquid U.S. equities), which represents the optimistic cost scenario.

With a $500K portfolio and 3 equal-weight positions, each position is approximately $167K. The square-root market impact model gives:

$$\text{Market Impact (per leg)} \approx \sigma_d \sqrt{\frac{Q}{\text{ADV}}} = 0.02 \times \sqrt{\frac{167{,}000}{50{,}000{,}000}} \approx 11.6 \text{ bps}$$

Full round-trip cost breakdown at ADDV > $50M:

| Cost Component | Estimate | Notes |
|---|---|---|
| Bid-ask spread (per leg) | 2–4 bps | Compressed in liquid names; wider on high-volatility days |
| Market impact (per leg) | ~12 bps | Square-root model at $167K / $50M ADV |
| Commission (per leg) | ~1 bp | Interactive Brokers tiered; negligible |
| **Round-trip total** | **~30–34 bps** | Optimistic; signal days have wider spreads |

Important qualification: stocks qualifying for the OS signal have just experienced an anomalously large move on anomalously large volume. On these days, the stock's effective liquidity is lower than its trailing average would suggest — market makers widen quotes in response to order flow imbalance. A realistic on-signal-day cost estimate adds a 50% liquidity haircut, raising the effective round-trip to approximately 45–52 bps on entry. Exit costs (TP or SL) on normal days revert toward the 30-bps baseline.

### 2b. Annual Turnover and Transaction Cost Drag

Approximate annual turnover for a 3-position portfolio:

$$\text{Annual trades} \approx \frac{252 \times 3}{\bar{K}}$$

where $\bar{K}$ is the average hold period in trading days. At $K=5$ (maximum hold), with some positions exiting early via TP/SL, a realistic average hold of 3–4 days gives approximately 189–252 trades per year.

Annual transaction cost drag:

$$\text{Annual cost} \approx \text{Annual trades} \times \text{Round-trip cost} \approx 220 \times 50 \text{ bps} \approx 11{,}000 \text{ bps} \times \frac{1}{3} \approx 3{,}667 \text{ bps of position notional}$$

Translating to portfolio-level: since each position is $1/3$ of the portfolio, and assuming 220 full round-trips per year across all 3 positions:

$$\text{Annual portfolio cost drag} \approx 220 \times \frac{1}{3} \times 50 \text{ bps} \approx 367 \text{ bps/year} \approx 3.7\%$$

This is the minimum gross alpha the strategy must generate annually to break even after costs. Any parameter configuration that does not produce at least 3.7% expected gross alpha is a losing strategy before the first trade. This hurdle rate should be stated explicitly as a filter in the strategy evaluation framework.

### 2c. Gap-Fill Execution Costs

When Step 1 or Step 2 fires, the exit occurs at the opening auction price. Opening auction fills have characteristics distinct from regular-hours limit orders:

- The opening auction is a call auction with imperfect price discovery; the realized fill may differ from the official open print by 2–5 bps in liquid names.
- For distressed stocks (the strategy's universe on high-signal days), the opening auction may be delayed or thin, with a spread of 10–20 bps around the auction midpoint.
- In extreme gap events (flash crash, material news), the opening auction may not occur at the official open time, and the reported open price in OHLC data may not be achievable.

Recommended implementation: add a flat 5-bps gap-fill slippage surcharge to all Step 1 and Step 2 exits. This is small enough to be conservative but non-negligible at high trade frequency. The backtest should separately track Step 1 and Step 2 exit counts so the gap-fill slippage assumption can be audited.

---

## Section 3: Risk Management

### 3a. Effective Stop-Loss Rate Under the Gap Model

The 4-step hierarchy correctly captures gap-throughs at the open. However, the gap-through events produce stop-losses at prices worse than the stated stop level. The effective stop-loss rate experienced by the portfolio exceeds the stated hyperparameter value.

Define:
- $p_{g|SL}$ = probability of a gap-through event given that a stop-loss exit occurs
- $\bar{g}$ = average additional gap loss beyond the stated stop level, conditional on a gap occurring

For stocks in the OS strategy universe (recent large losers), overnight gap-down probability on the following open is elevated relative to the broad market. A conservative empirical estimate based on short-term reversal literature: $p_{g|SL} \approx 15\%$, $\bar{g} \approx 2\%$.

Effective stop-loss rate:

$$\text{eff\_stop\_loss} = \text{stop\_loss\_rate} + p_{g|SL} \cdot \bar{g} = 2\% + 0.15 \times 2\% = 2.3\%$$

This is 30 bps worse than the stated stop-loss per average losing trade. For a strategy targeting a 3% take-profit, this 30 bps increase in average loss shifts the cost-adjusted break-even win rate upward by approximately 1.5 percentage points. Not catastrophic, but meaningful over hundreds of trades.

### 3b. Expected P&L Per Trade — Full Decomposition

Let $p_{TP}$, $p_{SL}$, and $p_K$ denote the probabilities of exiting via take-profit, stop-loss, and max-hold respectively ($p_{TP} + p_{SL} + p_K = 1$). Expected P&L per trade before transaction costs:

$$E[\text{PnL}] = p_{TP} \cdot \text{win\_take\_rate} - p_{SL} \cdot \text{eff\_stop\_loss} + p_K \cdot E[r_K]$$

where $E[r_K]$ is the expected return conditional on neither TP nor SL firing within K days. For a mean-reversion signal, $E[r_K]$ should be mildly positive (the signal has some mean-reversion value, just not strong enough to hit the TP within K days), but it is typically small and near zero.

The cost-adjusted break-even win rate (assuming $p_K \approx 0$ for simplicity):

$$p_{TP}^{\min} = \frac{\text{eff\_stop\_loss} + \text{TC}}{\text{win\_take\_rate} + \text{eff\_stop\_loss}} = \frac{2.3\% + 0.5\%}{3.0\% + 2.3\%} \approx 53.8\%$$

where TC = 50 bps round-trip expressed as 0.5%. A break-even win rate of approximately 54% is a realistic but non-trivial hurdle. The academic short-term reversal literature reports win rates of 55–65% for strong signals on liquid names. The strategy sits at the margin of viability — it requires genuine signal quality in the upper half of what the literature documents.

### 3c. Drawdown Analysis — Worst-Case Scenarios

With 3 equal-weight positions and equal-size stop-losses:

**Scenario 1 — Normal concurrent stop-outs (no gaps):**
All 3 positions hit their stop-loss on the same day. Portfolio loss = $\text{stop\_loss\_rate} = 2\%$.

**Scenario 2 — Gap-through concurrent stop-outs:**
All 3 positions gap through the stop on the same morning. Portfolio loss = $3 \times \frac{1}{3} \times \text{eff\_stop\_loss} = 2.3\%$.

**Scenario 3 — Cascade scenario (5 consecutive loss days with recycling):**
Each day's stop-outs are replaced with new positions that also stop out. Geometric compounding:

$$\text{5-day cumulative loss} = 1 - (1 - 0.023)^5 \approx 11.0\%$$

**Scenario 4 — 2020 COVID analog (20 consecutive trading days of stop-outs):**
$$\text{20-day cumulative loss} = 1 - (1 - 0.023)^{20} \approx 37.0\%$$

A 37% drawdown over 20 trading days is plausible and represents the tail risk of the strategy in a sustained market dislocation. This drawdown would be partially self-healing (some positions exit via TP as market stabilizes) but the scenario is realistic for a strategy with no regime filter.

### 3c. Portfolio Circuit Breaker — Absent From All Three Versions

This is the third consecutive review cycle in which a portfolio-level circuit breaker appears in the recommendations and is absent from the specification. This is not a nice-to-have feature — it is an operational risk control that separates a survivable drawdown scenario from a fund-ending one.

The cascade scenario above shows 37% drawdown is achievable over 20 trading days with no rule changes. Without a circuit breaker, the strategy will continue entering new positions throughout this period, each of which has a materially elevated probability of failure (because the market regime that triggered the cascade is ongoing).

**Minimum required specification**: Define a maximum peak-to-trough drawdown threshold (e.g., 15% from the most recent portfolio high-water mark). When this threshold is breached, halt all new position entries. Resume entries only after the portfolio recovers to within 10% of the high-water mark (a "reset" buffer). This is simple to implement, requires no forward-looking information, and prevents the strategy from trading its way into an unrecoverable position.

---

## Section 4: Capital Recycling — Re-Entry Logic Still Undefined After Three Rounds

This issue was flagged in v1, flagged again in v2, and remains unaddressed in v3. The consequence is that the backtest's capital recycling behavior is implementation-defined rather than specification-defined — different developers will implement it differently, producing different results from the same specification.

**Required definitions, stated precisely:**

**4a. Same-Day Re-Entry Candidates**

When a position exits on day $t$, the capital becomes available for redeployment at the close of day $t$. The replacement candidate is selected from the pre-computed day-$t$ OS ranking (using data through $t-1$, satisfying the no-look-ahead requirement). The eligible candidate pool is:

1. Ranked in the top-$M$ by $OS_{t-1}$ (where $M$ is an expansion buffer, e.g., top-10)
2. Not currently held in the portfolio
3. Not the stock that just exited on day $t$ (self-replacement prohibition)
4. With $v_{t-1} > V$ (liquidity filter satisfied)
5. Not subject to any other exclusion rule (e.g., earnings filter if implemented)

**4b. Rank Expansion for Replacement**

With 3 positions held and 1 exiting, the eligible replacement is the highest-ranked stock not currently held and not just exited. In the degenerate case where positions 1, 2, and 3 of the daily ranking are all still held (the exiting stock was, say, rank 4), the replacement would be rank 5. The specification must define the maximum rank from which a replacement can be drawn — unlimited expansion risks deploying capital into very low-quality signals.

Recommended: expand to at most the top-10 ranked stocks. If no eligible candidate exists within the top-10, hold cash until the next day's ranking.

**4c. Edge Case: No Eligible Replacement**

If all stocks within the expansion limit are either currently held or subject to exclusion, the released capital sits as cash until the following day's signal. This cash drag is real and must be modeled in the backtest — not patched by forcing a replacement from an arbitrary rank.

The backtest should track the number of days with suboptimal capital deployment (fewer than 3 positions held) and report this as a strategy metric. If the strategy runs with 2 positions for 20% of trading days, the reported AUM utilization is only 80%, which understates the effective transaction costs per deployed dollar.

---

## Section 5: Backtesting Methodology — Persistent Unresolved Issues

### 5a. Survivorship Bias — Critical, Unresolved Through All Three Rounds

This issue has been flagged as critical in every review round. It remains the single most dangerous structural defect in the strategy's backtesting framework, and it has not been addressed in any version.

The mechanism is direct and severe for this strategy type: stocks that score highest on the OS signal are, by construction, stocks that recently experienced large price declines on large volume. This population is disproportionately represented among names that subsequently went bankrupt, were acquired at distressed prices, or were delisted. A backtest using a current-day ticker list (e.g., via Yahoo Finance or any non-point-in-time source) will never encounter these names because they no longer exist in the dataset.

The survivorship bias impact is not symmetric — it selectively removes the worst outcomes from the backtested universe. Published estimates for mean-reversion strategies targeting recent losers range from 200 to 500 bps of annual performance inflation due to survivorship bias alone. Over a 10-year backtest, this compounds to a cumulative equity curve that is 22% to 63% higher than a survivorship-bias-free backtest would produce.

**Minimum acceptable data sources** (must include delisted stocks and point-in-time constituent history):

| Provider | Approximate Cost | Coverage | Notes |
|---------|:---:|---|---|
| Sharadar (Nasdaq Data Link) | ~$300/year | Russell 3000, 20+ years | Delisted tickers included; suitable for this strategy |
| Polygon.io (institutional tier) | ~$200/month | All U.S. exchanges, real-time + historical | Comprehensive delistings coverage |
| CRSP (via WRDS) | Institutional pricing | All U.S. equities, 1925-present | Academic gold standard; full corporate action history |
| Yahoo Finance / yfinance | Free | Current tickers only | **Not acceptable for this strategy under any circumstances** |

**This issue must be resolved before the first backtest run is presented to any stakeholder. No result produced with survivorship-biased data should be used to make capital allocation decisions.**

### 5b. Walk-Forward Validation Structure

The following structure is recommended for the 10-year backtest. The boundaries must be set before any data is examined:

| Period | Dates | Purpose |
|--------|-------|---------|
| Warm-up | Year preceding backtest start | Initialize $N$-day rolling windows; no trades |
| In-sample (IS) | 2015-01-01 to 2019-12-31 | Hyperparameter selection; signal validation |
| Out-of-sample (OOS) | 2020-01-01 to 2024-12-31 | True performance evaluation; do not touch during IS work |
| Stress period: COVID crash | 2020-02-20 to 2020-04-30 | Regime-specific analysis |
| Stress period: 2022 bear | 2022-01-01 to 2022-12-31 | Sustained mean-reversion failure test |

**Critical rule**: The OOS period must not be examined for parameter tuning at any stage of development. Even visually inspecting the equity curve before parameters are finalized converts the OOS period into additional IS data and invalidates the test. The IS Sharpe and OOS Sharpe must be reported separately. If the OOS Sharpe is less than 50% of the IS Sharpe, the strategy is overfit and should not receive capital.

### 5c. Multiple Testing — Now Seven Hyperparameters, a Worsened Situation

v3 adds $V$ (the liquidity threshold) to the hyperparameter set, bringing the total to seven: $N$, $w_1$, $w_2$, win\_take\_rate, stop\_loss\_rate, $K$, and $V$.

A moderate grid with 3 values per parameter yields:

$$3^7 = 2{,}187 \text{ parameter combinations}$$

At a standard 5% significance threshold without correction, the expected number of false discoveries is:

$$\text{Expected false discoveries} = 2{,}187 \times 0.05 \approx 109$$

This is catastrophic: for every parameter combination that is genuinely profitable, there are potentially dozens of combinations that appear profitable by pure random chance. The Bonferroni-corrected significance threshold for this search space is:

$$\alpha_{\text{corrected}} = \frac{0.05}{2{,}187} \approx 0.0023\%$$

This threshold is so stringent that almost no empirical mean-reversion strategy will clear it over a 10-year backtest sample. The practical solution is not a post-hoc statistical correction but pre-commitment to a parameter set on economic grounds, before running any backtest.

**Recommended parameter reduction approach:**

Fix the following parameters on economic priors, leaving only three to be tested:

| Parameter | Fixed Value | Economic Rationale |
|-----------|-------------|-------------------|
| $N$ | 20 trading days | One calendar month; consistent with short-term reversal literature on signal half-life |
| $w_1$ | $-1$ (normalized) | Negative weight required to rank oversold stocks highest; see Section 6 below |
| $w_2$ | $+1$ (normalized) | Positive weight on volume deviation; amplifies the signal monotonically |
| $V$ | ADDV > $50M | Economic prior: sufficient liquidity for a $500K fund; avoids small-cap noise |

With these fixed, only 3 free parameters remain: win\_take\_rate, stop\_loss\_rate, $K$. A grid with 3 values each yields $3^3 = 27$ combinations. Expected false discoveries at 5%: $27 \times 0.05 \approx 1.35$ — manageable and honest.

---

## Section 6: Report Completeness Review

### 6a. v3 Additions Assessment

The v3 addition of a "hold duration" column to the trade log is a genuine improvement. This field enables:
- Turnover calculation: average holding period translates directly to annual trade frequency
- Exit mechanism analysis: comparing hold duration across TP, SL, and K-day exits reveals whether the exit hierarchy is calibrated appropriately
- Signal decay validation: a distribution of hold durations skewed toward 1–2 days suggests the signal is weak (positions exit via SL early) or the TP is too tight; a distribution skewed toward K days suggests the signal is strong but the TP is too wide

No other changes to the report were introduced in v3.

### 6b. Still Missing From the Report

The following items were identified in v1 and v2 and remain absent from the v3 specification:

| Missing Item | Why It Matters |
|---|---|
| Benchmark comparison (SPY total return) | Absolute returns are uninterpretable without a benchmark; alpha vs. beta cannot be separated |
| In-sample vs. out-of-sample return curves | The single most important overfitting diagnostic; must be reported separately |
| Sortino ratio | More appropriate than Sharpe for negatively skewed payoffs (capped upside via fixed TP, unbounded downside via gaps) |
| Calmar ratio (CAGR / MDD) | Primary metric for fund manager assessment; links return to worst-case scenario |
| Win rate by exit type | TP win rate, SL loss rate, K-day win/loss rate — separately; validates the exit hierarchy calibration |
| Annual turnover | Validates the transaction cost model; high turnover strategies need explicit cost sensitivity analysis |
| Exit type breakdown (TP / SL / K-day) | If K-day exits dominate, TP and SL levels are miscalibrated; if SL dominates, the signal has no edge |
| Drawdown time series (not just max) | Shows temporal structure of losses; reveals regime sensitivity |
| Rolling 12-month Sharpe | Shows performance consistency across market regimes; the critical diagnostic for regime dependency |
| Monthly return heatmap | Year × month grid; immediately identifies crisis periods and seasonal clusters |
| Sector/industry concentration | If the strategy systematically concentrates in Energy or Biotech, the alpha may be factor exposure, not signal quality |
| Profit factor (gross profit / gross loss) | Must exceed 1.5 to be viable after realistic costs; fundamental strategy characteristic |

### 6c. Recommended Interactive Chart Additions

For the HTML5 report using Plotly, the following charts should be added beyond the currently specified daily return and total asset curves:

1. **Equity curve vs. SPY on shared log-scale axis** — makes the benchmark comparison visual and immediate
2. **Underwater (drawdown) chart** — plots $(V_t - \max_{s \leq t} V_s) / \max_{s \leq t} V_s$ continuously; shows drawdown depth and recovery duration
3. **Rolling 6-month and 12-month Sharpe ratio** — on a separate subplot below the equity curve; flat or near-zero rolling Sharpe periods indicate regime failure
4. **Exit type pie or stacked bar chart** — TP%, SL%, K-day%; should be computed separately for IS and OOS periods
5. **Hold period histogram** — distribution of holding days; reveals whether the $K$-day cap is binding
6. **Return distribution histogram with normal overlay** — shows the actual return distribution; fixed TP creates a right-censored distribution, fixed SL creates a left-censored distribution; the tail behavior reveals the gap-through risk empirically
7. **Sector breakdown** — bar chart of trade count and total P&L by GICS sector; if Biotech or Tech dominate, flag as a sector concentration risk

---

## Section 7: Complete Issue Tracker — All Versions

The following table is the authoritative issue register spanning all three review rounds. Issues are numbered for traceability.

| ID | Issue | Severity | v1 | v2 | v3 | Action Required |
|----|-------|:---:|:---:|:---:|:---:|---|
| C1 | $D(r)$ uses $\|r_T\|$ — direction lost | Critical | Open | Fixed | Fixed | No further action |
| C2 | $w_1$ sign unspecified — ranking inversion risk | Critical | — | Open | **Still open** | Fix $w_1 < 0$ in formula; unit test required |
| C3 | Survivorship bias — no point-in-time universe | Critical | Open | Open | **Still open** | Procure Sharadar or Polygon; no backtest without this |
| C4 | Gap-through fills — stop filled at limit, not open | Critical | Open | Open | **Fixed** | 4-step hierarchy resolves this |
| C5 | TP/SL ordering ambiguity (TP first = optimistic) | Major | Open | Open | **Fixed** | SL priority in Step 3 is correct |
| C6 | Stochastic 50% fill model | Major | — | — | **New in v3** | Replace with 100% fill + fixed seed; see Section 1c |
| C7 | K-day count definition ambiguous | Minor | — | — | **New in v3** | Define precisely: trading days from close of $T$; see Section 1e |
| C8 | Capital recycling — re-entry logic undefined | Major | Open | Open | **Still open** | Define fully per Section 4; self-replacement prohibition required |
| C9 | Liquidity filter $V$ — named but unquantified | Major | Open | Partial | **Still open** | Fix to ADDV > $50M as economic prior |
| C10 | Multiple testing — 7 unconstrained hyperparameters | Critical | Open | Open | **Worsened** (7th param added) | Fix 4 params on priors; test only 3 |
| C11 | No portfolio circuit breaker | Major | Open | Open | **Still open** | Add 15% drawdown halt rule; see Section 3c |
| C12 | No benchmark in report | Major | Open | Open | **Still open** | Add SPY total return to all equity charts |
| C13 | Missing report metrics (Sortino, Calmar, win rate, etc.) | Moderate | Open | Open | **Partially addressed** (hold duration added only) | Add all items in Section 6b |
| C14 | Log-volume for $D(v)$ not applied | Minor | Open | Open | **Still open** | Apply $\log(v)$ before z-scoring |
| C15 | Re-entry exclusion after stop-loss | Major | Open | Open | **Still open** | Spec must prohibit same-day re-entry of exiting stock |
| C16 | Boundary conditions in Step 1 and Step 2 | Minor | — | — | **New in v3** | Change to $\leq$ for SL, $\geq$ for TP; see Section 1a |
| C17 | No regime filter | Major | Open | Open | **Still open** | Add VIX > 30 or SPY 200-day MA filter |
| C18 | No earnings/catalyst filter | Major | Open | Open | **Still open** | Exclude stocks within 2 days of earnings announcement |
| C19 | IS vs. OOS metrics not reported separately | Major | Open | Open | **Still open** | Mandatory split per Section 5b |
| C20 | Walk-forward structure not defined | Major | Open | Open | **Still open** | Fix IS/OOS boundary at 2019-12-31 before any run |

**Status summary across versions:**

| Round | Issues Resolved | Issues Introduced | Net Open |
|-------|:---:|:---:|:---:|
| v1 → v2 | 1 (C1 directional fix) | 3 (new critical + moderate + minor) | +2 net |
| v2 → v3 | 2 (C4 gap-through, C5 TP/SL order) | 3 (C6 stochastic fill, C7 K-count, C16 boundary) | +1 net |

The issue count is growing, not shrinking. This is partly explained by increasing specification detail revealing previously implicit ambiguities, but it is also a signal that critical issues are being deferred rather than resolved.

---

## Conclusion

v3 represents a genuine and material improvement in the strategy's exit logic. The 4-step hierarchical exit system correctly handles the gap-through problem that had been flagged as critical since the first review round. The decision to give stop-loss priority over take-profit in the ambiguous intraday case is conservative and correct. These are meaningful contributions to the specification's quality.

However, the 50% stochastic fill model introduced in Step 3 is a new methodological flaw that undermines the reproducibility of any backtest produced under this specification. It must be replaced before a single backtest result is used for decision-making.

More importantly, the two most consequential structural issues — survivorship bias (C3) and the $w_1$ sign ambiguity (C2) — remain unresolved through three complete review rounds. These are not edge cases or refinements. Survivorship bias alone can inflate the backtest's CAGR by 200–500 bps annually, compounding to a 22–63% cumulative overstatement over 10 years. An incorrect $w_1$ sign means the strategy buys overbought stocks instead of oversold ones — an implementation that produces the exact opposite of the intended signal.

**The implementation team must not run a backtest under any of the following conditions:**

1. Using Yahoo Finance or any non-point-in-time data source (C3 unresolved)
2. Without an explicit, tested assertion that the top-3 ranking selects the most oversold stocks with $w_1 < 0$ (C2 unresolved)
3. Without locking IS/OOS boundaries before examining any data (C20 unresolved)
4. With the stochastic 50% fill model and no fixed random seed (C6 unresolved)

Any result produced in violation of these four conditions should be considered illustrative at best and misleading at worst. The number of resolved issues now totals three out of twenty. Fourteen critical and major issues remain open. The specification requires another revision cycle before it is ready for implementation.

---

*This document reflects a third-round pre-implementation peer review based on the v3 strategy specification. It supersedes the v2 execution review where conclusions differ, and should be read in conjunction with all four prior review documents. All critical and major issues must be resolved before backtest engine implementation begins.*

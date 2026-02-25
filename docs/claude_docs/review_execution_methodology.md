# Critical Review: Oversell Strategy — Execution Methodology & Backtesting Design

**Author**: Senior Quant Researcher (Internal Review)
**Date**: 2026-02-24
**Status**: Pre-Implementation Peer Review
**Classification**: Internal — Not for Distribution

---

## Preface

This document is a rigorous analytical review of the proposed "Oversell Score" mean-reversion strategy prior to any implementation. The goal is to identify all structural flaws, execution assumptions, and methodological risks before a single line of backtest code is written. Every concern raised here, if unaddressed, represents either (a) a silent bias that will make backtest performance meaningless, or (b) a live-trading failure mode that will destroy capital.

The review is organized from the most critical issues (execution and bias) down through risk management, performance metrics, and operational concerns. Read section 9 first if you want the prioritized action list.

---

## 1. Execution Logic & Market Microstructure

### 1.1 Buying at the Close of Day T

The strategy computes a signal using data through day $T-1$ and executes a buy at the **close price of day $T$**. The authors frame this as participation in the "closing auction." This framing requires careful scrutiny.

**The closing auction is real but constrained.** U.S. equity exchanges (NYSE, Nasdaq) run a formal closing auction beginning roughly 3:50–4:00 PM. Market-on-close (MOC) and limit-on-close (LOC) orders participate. For liquid stocks this is feasible. However:

1. **Order submission deadline**: NYSE MOC orders must be submitted by 3:45 PM and LOC orders by 3:58 PM. A strategy that computes signals at the open (using prior-day data) and submits MOC orders before 3:45 PM has a clean, realistic workflow. The document must explicitly state this workflow, or the execution assumption is undefined.

2. **Auction participation risk**: Closing auction prices can differ materially from the last trade price, particularly for stocks experiencing the kind of high-volume, high-return deviations the OS score targets. A stock scoring high on both return deviation and volume deviation has, by definition, experienced unusual activity that day — the closing auction for such a stock may be disorderly, with wide spreads and high impact.

3. **Feasibility verdict**: Buying at day $T$ close using day $T-1$ signals is **operationally feasible** provided the workflow is explicitly: compute signal at open using prior-day data, submit MOC orders by 3:45 PM. This is the correct interpretation and must be locked in before implementation. The alternative — computing the signal intraday and buying at close — would be infeasible for most practitioners without real-time infrastructure.

**Bottom line**: No look-ahead bias here *if the workflow is correct*, but the workflow must be documented precisely. The backtest should use the official closing price (adjusted for dividends/splits), not the "last trade" price.

### 1.2 Look-Ahead Bias in Signal Construction

The OS score for day $T-1$ is:

$$OS_{T-1} = w_1 \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}$$

where both deviations use rolling $N$-day windows ending at $T-1$. The trade executes at day $T$ close. **There is no look-ahead bias in the signal itself** — the signal is clean by construction.

However, there are three subtle look-ahead risks in the implementation:

1. **Adjusted price data**: If using split/dividend-adjusted prices downloaded from a provider (e.g., yfinance), the adjustment factors are applied retrospectively using *current* corporate action data. A stock that underwent a 10-for-1 split in 2020 will have its 2018 prices adjusted using 2020 information. This is not exploitable in live trading but inflates backtest consistency. **Use raw prices with point-in-time adjustment factors from a clean source (CRSP or Polygon.io).**

2. **Rolling window initialization**: The first $N$ days of the backtest have insufficient history to compute the rolling statistics. These rows must be dropped entirely or the strategy must not trade during the warmup period. Silently carrying forward NaN values, or using `min_periods=1` in pandas rolling functions, introduces unstable early-period signals.

3. **Volume data normalization**: If daily volume is normalized using a rolling window, that window must be anchored to $T-1$ with no future volume data bleeding in. This is straightforward in pandas using `.shift(1)` on the volume series before computing rolling statistics, but is a common implementation mistake.

### 1.3 Sell Execution: The Intraday Price Path Problem

The take-profit and stop-loss conditions check whether the target price falls within $[\text{Low}_t, \text{High}_t]$ for that day. This is the **most significant execution assumption in the entire strategy design**, and it deserves extended treatment.

**The assumption being made**: If the target price lies between the day's low and high, the order was filled at exactly the target price. This is equivalent to assuming:
- The stock price visits every level within $[\text{Low}_t, \text{High}_t]$ at some point during the day.
- The order can be filled at precisely the target level with no slippage.
- There is no gap-through risk.

**Why this is problematic**:

*Gap risk*: If a stock gaps through the stop-loss level (e.g., opens at $p \cdot (1 - 2 \cdot \text{stop\_loss\_rate})$ when the stop is at $p \cdot (1 - \text{stop\_loss\_rate})$), the backtest will record a fill at the stop price. In reality, the fill would be at the open, incurring a much larger loss. This will systematically **understate losses** and make the stop-loss appear more effective than it is. Gap-through events are disproportionately common in exactly the oversold stocks this strategy targets.

*Intraday path assumption*: Daily OHLC data provides only four points of the intraday path. The Low and High bracket the range but do not imply the price visits every point in between. A stock could open at the high, sell off to the low, and close in the middle — or vice versa. For limit orders, the probability of fill given price touching the level is roughly 50% for a limit at the exact touch (market microstructure result). The backtest treats it as 100%.

*Order precedence*: The strategy checks take-profit before stop-loss. If both levels are within the daily range, the backtest assumes the take-profit was hit first. This is an optimistic assumption — there is no way to determine from OHLC data which level was visited first. In practice, for volatile stocks, the lower bound (stop-loss) is equally likely to have been visited first.

**Recommendation**: Use the following hierarchy of assumptions in increasing order of conservatism:
1. Fill at target if target within range (current assumption — optimistic)
2. Fill at target if target within range, but assume 50% gap-through probability for stop-losses
3. Use next-day open as a proxy for exits (conservative but realistic for non-limit orders)

For a mean-reversion strategy on oversold stocks, using next-day open for exits would be significantly more conservative and more representative of actual execution, particularly for stop-loss scenarios where the stock may continue to decline overnight.

### 1.4 Same-Day Capital Recycling

When a position exits intraday (via take-profit or stop-loss), the strategy reinvests that capital into a new position bought at the same day's close. This creates a logical sequencing problem:

- The new stock's OS score was computed using $T-1$ data (the day before). The selection is not based on current-day information — this is fine.
- However, the capital freed from the exited position needs to be allocated to the new position at close. This requires that (a) the new signal was already computed at the open, (b) the exit happened intraday, and (c) an MOC order for the new stock was submitted before the 3:45 PM deadline.

**The operational challenge**: If a stop-loss triggers at 2:30 PM and the trader wants to recycle into a new position at close, they need a pre-ranked watchlist of backup candidates ready before 3:45 PM. This is operationally feasible with automation but requires explicit design — it does not happen automatically.

**The backtest assumption**: The backtest likely assumes perfect capital recycling with zero friction. In practice, there will be days where recycling is either impossible (all candidates already held) or undesirable (no qualifying stocks). The backtest should include a "cash drag" cost for recycled capital that doesn't find a home.

### 1.5 Long-Only and Position Overlap

The strategy is implicitly long-only. Several structural questions arise:

- **What if the same 3 stocks appear on consecutive days?** If the top-3 stocks today are identical to yesterday's holdings, the strategy should not churn — it should hold. The implementation must explicitly handle this case.
- **Overlap between candidates and existing positions**: When recycling capital, the new top candidate might already be held. The code must filter out existing holdings from the candidate selection pool.
- **Universe concentration risk**: If the universe is not carefully filtered (e.g., including only stocks above some liquidity threshold), the top-3 OS candidates may cluster in a single sector or industry, creating hidden concentration risk despite the equal-weight allocation.

---

## 2. Transaction Cost Modeling

### 2.1 Realistic Cost Estimates for a $500K Fund

With 3 equal positions of approximately $167K each, the all-in transaction cost per round trip must be estimated:

**Bid-ask spread**: For liquid mid-cap equities (market cap $2B–$10B), typical bid-ask spreads are 2–8 bps. For the oversold stocks this strategy targets — which have just experienced anomalous volume and returns — spreads may widen to 10–20 bps on the day of entry. Use 10 bps (1 bp = 0.01%) as a conservative baseline, applied to both buy and sell, yielding 20 bps per round trip from spread alone.

**Market impact**: A $167K order in a mid-cap stock with average daily volume (ADV) of, say, $10M represents 1.67% of ADV. The square-root market impact model gives:

$$\text{Impact} \approx \sigma_{\text{daily}} \cdot \sqrt{\frac{\text{Order Size}}{\text{ADV}}}$$

For a stock with daily volatility of 3% (typical for an oversold stock in the signal's universe) and participation rate of 1.67% of ADV:

$$\text{Impact} \approx 0.03 \cdot \sqrt{0.0167} \approx 0.03 \cdot 0.129 \approx 39 \text{ bps}$$

This is per leg, so round-trip impact is approximately 78 bps. For smaller, more illiquid stocks in the universe, this number rises significantly.

**Commission**: At modern retail/institutional brokers (Interactive Brokers, etc.), commissions are effectively negligible — approximately 0.5 bps per leg, or ~1 bp round trip. This is immaterial compared to spread and impact.

**Total estimated round-trip cost**: Approximately **100–150 bps** per trade under realistic assumptions, possibly higher for illiquid or volatile names.

### 2.2 Required Alpha to Overcome Costs

If average holding period is $K$ days and total round-trip cost is 125 bps, the strategy needs to generate more than 1.25% per trade *before* any other consideration. Annualizing: if the strategy turns over each position roughly every $K = 10$ days (trading days), annual turnover is approximately:

$$\text{Annual turnover} = \frac{252}{K} \times 3 \text{ positions} = \frac{252}{10} \times 3 \approx 75 \text{ position changes per year}$$

At 125 bps per round trip, the annual drag from transaction costs alone is:

$$75 \times 0.0125 = 93.75\% \text{ of notional portfolio}$$

This cannot be right for a position-count-normalized fund. Recalculating properly: if each of the 3 positions turns over $252/K$ times per year, and each represents $1/3$ of capital, the annual cost drag as a fraction of total portfolio value is:

$$\text{Annual cost} = \frac{252}{K} \times 0.00125 \approx \frac{3.15\%}{K}$$

For $K = 10$: approximately 31.5 bps per year in cost drag on the total portfolio, expressed per position. For 3 positions simultaneously: **94.5 bps total annual drag**. This is significant but not fatal if the gross alpha per trade exceeds 1.5–2%.

**Minimum alpha requirement**: The strategy needs approximately **1.5–2.5% gross alpha per trade** (before costs) to be viable after transaction costs, depending on holding period and universe liquidity.

---

## 3. Position Sizing & Capital Allocation

### 3.1 Equal Weight vs. Signal-Proportional Sizing

The current design uses equal-weight allocation across 3 positions regardless of OS score differences. Consider two stocks with OS scores of 5.0 and 1.2 — the equal-weight rule treats them identically. This is a significant inefficiency.

**The case for equal weight**: Simple, robust, avoids overfitting the sizing model to noisy signal estimates. In practice, Kelly-optimal sizing frequently fails out-of-sample because the input parameters (expected return, variance) are estimated with large uncertainty.

**The case for signal-proportional sizing**: If the OS score has a genuinely monotonic relationship with expected return, allocating more capital to higher-score stocks improves the information ratio. This should be tested empirically during signal validation, not assumed.

**Kelly criterion context**: The full Kelly fraction for a single position is:

$$f^* = \frac{\mu}{\sigma^2}$$

where $\mu$ and $\sigma^2$ are the per-trade expected return and variance. For typical mean-reversion parameters (e.g., $\mu = 2\%$, $\sigma = 4\%$ per trade), $f^* = 0.02 / 0.0016 = 12.5$, which is obviously absurd (12.5x leverage). This illustrates why raw Kelly is never used in practice. Fractional Kelly (e.g., 25% Kelly) is typical, which gives $f^* = 3.125$ — still implying significant concentration. The equal-weight-across-3 approach implicitly assumes much more modest conviction, which is appropriate for an early-stage strategy without robust out-of-sample validation.

**Recommendation**: Start with equal weight. After generating a validated signal with confirmed out-of-sample alpha, revisit proportional sizing.

### 3.2 Idle Capital and Partial Portfolio States

The strategy holds exactly 3 positions when possible. Several states require explicit handling:

- **Fewer than 3 qualifying stocks**: Define a minimum OS score threshold below which no trade is taken. Holding cash is preferable to forcing trades with weak signals.
- **Position exits without immediate replacements**: Capital sits idle until the next closing auction. This creates a cash drag that must be modeled in the backtest — it is not trivial for a concentrated 3-position book.
- **First N days of backtest**: During the rolling window warmup period, no trades should be taken. The backtest should mark these days explicitly.

---

## 4. Risk Management Analysis

### 4.1 Take Profit Design

The take-profit rule:

$$\text{Exit Price}_{\text{TP}} = p \cdot (1 + \text{win\_take\_rate})$$

For a mean-reversion strategy, capping upside at a fixed rate is economically sound: the thesis is that the stock is temporarily oversold and will revert toward fair value, not that it will trend indefinitely. Taking profit at a fixed reversion target is consistent with the thesis.

**Appropriate values**: For mean-reversion in U.S. equities, typical take-profit targets are 2–5% above entry. A 2% target is achievable within 2–5 days for a stock that genuinely reverts; a 5% target may require holding through multiple volatility cycles. Given that the OS score targets stocks with anomalous single-day moves, a 2–3% take-profit aligns well with the empirical mean-reversion literature (e.g., DeBondt-Thaler short-term reversals, which document 1–3% reversals over 1–5 day horizons).

**Negative skew warning**: A fixed take-profit with an unlimited downside (before the stop-loss triggers) creates negative skew in the return distribution. More importantly, if take-profit is set too tight, the strategy will be *right* on direction more often but leave money on the table when strong reversals occur. The win rate will appear high, but the profit per winner will be capped. This makes the strategy appear better than it is in aggregate if the tail of large winners is systematically clipped.

**Skew consideration**: With a fixed take-profit at $w\%$ and a stop-loss at $-s\%$, the maximum gain is bounded but losses can still exceed $s\%$ in gap scenarios. This is a structurally negatively-skewed payoff profile — common in income/short-vol strategies. It is not inherently bad, but the fund manager must be aware and the Sharpe ratio must be interpreted in this context (high Sharpe with negative skew often collapses during tail events).

### 4.2 Stop Loss Design

The stop-loss rule:

$$\text{Exit Price}_{\text{SL}} = p \cdot (1 - \text{stop\_loss\_rate})$$

**Alignment with mean-reversion thesis**: This is conceptually sound. If the stock continues to fall beyond the entry point by a meaningful amount, the mean-reversion thesis may be invalidated (or the reversion will take longer than the hold period allows), so cutting losses is appropriate.

**Win rate vs. risk/reward calibration**: For a strategy targeting approximately 60% win rate (a reasonable expectation for short-term mean-reversion in oversold stocks with a well-constructed signal), the minimum win\_take\_rate / stop\_loss\_rate ratio to achieve positive expected value is:

$$\frac{w}{s} > \frac{1 - p_w}{p_w}$$

where $p_w$ is the win rate. At 60% win rate: $\frac{w}{s} > \frac{0.40}{0.60} = 0.667$. So the ratio only needs to exceed 0.667 for positive expected value. A common configuration of 3% take-profit and 2% stop-loss gives a ratio of 1.5, which provides a meaningful margin of safety above the break-even threshold.

However, this calculation ignores gap risk. If 10% of losing trades gap through the stop-loss by an average of 2x the stop distance, the effective loss-per-loser increases, and the required win\_take\_rate / stop\_loss\_rate ratio rises. **This makes realistic stop-loss execution modeling critical.**

**Parameter interaction**: The six hyperparameters ($N$, $w_1$, $w_2$, win\_take\_rate, stop\_loss\_rate, $K$) are heavily interdependent. For example, a tight stop-loss combined with a long max-hold period will produce many stop-outs early but then an idle position waiting for close — this is a degenerate strategy configuration. The team should map the interaction surface explicitly, not tune parameters independently.

### 4.3 Maximum Hold Period

The max-hold exit at day $K$ serves as a time stop and is conceptually sound for a mean-reversion strategy: if the stock has not reverted within $K$ days, the original thesis was likely wrong, and continued holding introduces momentum-reversal risk (the "value trap" problem at short horizons).

**Alpha decay analysis**: The expected return of the oversell signal should decay over time. Empirically, short-term reversal signals (which this is) tend to peak within 1–3 days and largely decay by day 5–10. If the signal's alpha is exhausted by day 5 but $K = 20$, the last 15 days of holding contribute negative alpha (unnecessary exposure with no compensated risk). The optimal $K$ should be estimated from the signal's empirical half-life, which requires constructing an "average return by holding day" curve — a standard signal decay analysis.

**Interaction with take-profit/stop-loss**: If take-profit and stop-loss are well-calibrated, the max-hold should trigger only infrequently (for positions where the stock neither recovered to target nor fell to stop). These "stuck" positions are the most informationally interesting — they suggest the signal was wrong or the stock is in a new regime. Tracking what fraction of positions exit via each mechanism (TP, SL, max-hold) is a key diagnostic.

---

## 5. Backtesting Methodology Critique

### 5.1 Survivorship Bias

This is a **critical flaw risk**. If the backtest universe is constructed using current-day S&P 500 or Russell 3000 constituent lists, every stock in the universe has survived to the present — the universe is free of delisted companies, bankruptcies, and stocks that were acquired. For a strategy that specifically targets *distressed-appearing* stocks (high return deviation, high volume deviation), this bias is severe:

- Many stocks that scored high on the OS metric in 2014–2018 subsequently went bankrupt or were delisted at near-zero prices.
- Including only survivors means the backtest never encounters the catastrophic losses that would have occurred in those names.
- The result is a systematically upward-biased equity curve.

**Requirement**: The universe must be constructed using **point-in-time constituent lists**. Acceptable sources:
- CRSP (academic, expensive, gold standard)
- Compustat (institutional, via Bloomberg or direct)
- Sharadar (via Nasdaq Data Link, ~$300/year, covers Russell 3000 point-in-time)
- Polygon.io (covers listed/delisted tickers with historical data, ~$200/month for institutional tier)

**Under no circumstances** should yfinance be the primary data source for the universe definition, as it only returns data for currently-active tickers and provides no point-in-time constituent list.

### 5.2 Look-Ahead Bias Checklist

The following are all potential sources of look-ahead bias, ranked by likelihood of occurring in an implementation using common Python libraries:

| # | Source | Severity | Common Cause |
|---|--------|----------|--------------|
| 1 | Adjusted price data using future corporate actions | High | yfinance, any data provider using current adjustments |
| 2 | Universe defined by current constituents (survivorship) | Critical | Using static ticker lists |
| 3 | Rolling window using `min_periods < N` | Medium | Pandas default behavior with insufficient warmup |
| 4 | Signal computed with same-day close price | Low | Misuse of `shift()` |
| 5 | Volume normalization using future data | Medium | Incorrect window alignment in pandas |
| 6 | Financial ratios from quarterly reports using filing dates vs. report dates | N/A (not applicable to this strategy, but note for future) | — |

### 5.3 Data Requirements

| Data Item | Source Options | Notes |
|-----------|---------------|-------|
| Daily OHLCV | Polygon.io, CRSP, Refinitiv | Must include delisted names |
| Point-in-time universe | Sharadar, CRSP, Compustat | Critical for survivorship bias |
| Dividend/split adjustments | CRSP, Polygon.io | Point-in-time preferred |
| Company metadata (name, sector, industry) | Polygon.io, Compustat | For trade log and attribution |

### 5.4 Walk-Forward Validation

With a 10-year backtest (approximately 2014–2024), the following structure is recommended:

- **In-sample (IS)**: 2014–2019 (6 years) — used for parameter selection
- **Out-of-sample (OOS)**: 2020–2024 (5 years) — held out, evaluated once only

Within the IS period, use **rolling walk-forward optimization**:
- Train on first 2 years, test on year 3
- Train on first 3 years, test on year 4
- Continue forward, never allowing future data into training windows

**Critical rule**: The OOS period (2020–2024) must not be touched during development. Any parameter adjustments based on OOS performance convert it to IS and invalidate the test. This is the most commonly violated rule in quant research.

### 5.5 The Multiple Testing Problem

The strategy has 6 hyperparameters: $N$, $w_1$, $w_2$, win\_take\_rate, stop\_loss\_rate, $K$. Even with modest grid search:
- $N$: 5 values (10, 20, 30, 60, 90)
- $w_1, w_2$: 3 weight configurations each, normalized to sum to 1
- win\_take\_rate: 5 values (0.01, 0.02, 0.03, 0.04, 0.05)
- stop\_loss\_rate: 5 values (0.01, 0.015, 0.02, 0.03, 0.05)
- $K$: 5 values (3, 5, 7, 10, 15)

Total combinations: $5 \times 3 \times 5 \times 5 \times 5 = 1,875$ parameter sets. With a 5% significance threshold and 1,875 tests, the expected number of false positives is $1,875 \times 0.05 = 93.75$. The backtest will almost certainly find parameter sets that appear highly profitable purely by chance.

**Remedies**:
1. **Bonferroni correction**: Require $p < 0.05 / 1875 = 0.000027$ for any parameter set to be considered significant. This is extremely strict and likely no parameter set will pass.
2. **Combinatorial Purged Cross-Validation (CPCV)**: As described in López de Prado (2018), this method properly accounts for the multiple testing problem in financial time series.
3. **Parameter robustness criterion**: Select parameters based on *neighborhood performance*, not peak performance. A parameter set that works at $(N=20, K=10)$ but fails at $(N=19, K=9)$ and $(N=21, K=11)$ is likely overfit. Require that the best parameter set remains profitable across at least 60–70% of nearby configurations.
4. **Economic prior**: Fix as many parameters as possible using economic reasoning before any optimization. For example, $N = 20$ (one calendar month) is a natural choice grounded in the behavioral finance literature on short-term reversals. Reducing the free parameter count from 6 to 3 or 4 reduces the multiple testing severity dramatically.

---

## 6. Performance Metrics Review

### 6.1 Sharpe Ratio

$$\text{Sharpe} = \frac{\bar{R}_p - R_f}{\sigma_p} \cdot \sqrt{252}$$

The proposed daily Sharpe ratio is appropriate for monitoring but has known limitations for strategies with non-normal return distributions (which this strategy will have due to the fixed take-profit and stop-loss structure). Specifically:

- **Daily Sharpe overestimates quality** for strategies with infrequent but large losses (negative skew). A strategy can have a high daily Sharpe that collapses to a low weekly/monthly Sharpe due to autocorrelation in returns.
- **Recommendation**: Report Sharpe at daily, weekly, and monthly frequencies. Significant divergence across frequencies signals non-normality or autocorrelation.
- **Threshold for this strategy type**: A Sharpe above 1.0 is acceptable; above 1.5 is strong; above 2.0 should be treated with skepticism and examined for latent biases.

### 6.2 Maximum Drawdown and Calmar Ratio

$$\text{MDD} = \max_{t \in [0,T]} \left(\frac{W_t - \max_{s \leq t} W_s}{\max_{s \leq t} W_s}\right)$$

$$\text{Calmar} = \frac{\text{CAGR}}{|\text{MDD}|}$$

For a $500K–$10M fund, the **maximum tolerable drawdown** is a function of investor psychology and redemption risk:
- At $500K (personal capital), a 25–30% drawdown may be tolerable.
- At $1M–$10M (external capital), professional norms suggest 15–20% max drawdown before investors redeem.

A Calmar ratio above 1.0 is considered acceptable; above 2.0 is strong. Any strategy showing Calmar below 0.5 in a backtest is unlikely to survive live trading where drawdowns are deeper than historical analogs suggest.

**Additional drawdown metrics to report**:
- Average drawdown duration (in trading days)
- Number of drawdowns exceeding 10%
- Recovery time from maximum drawdown
- Drawdown distribution (plot of all drawdown periods sorted by depth)

### 6.3 Missing Metrics — Required Additions

The proposed HTML5 report includes return curve, total asset curve, Sharpe, and MDD. This is insufficient for a strategy assessment. The following must be added:

| Metric | Formula / Description | Why It Matters |
|--------|----------------------|----------------|
| Sortino Ratio | $(\bar{R}_p - R_f) / \sigma_{\text{downside}} \cdot \sqrt{252}$ | Penalizes only downside volatility; more relevant for asymmetric strategies |
| Calmar Ratio | $\text{CAGR} / |\text{MDD}|$ | Links return to worst-case drawdown |
| Win Rate | Fraction of trades with positive PnL | Core diagnostic for TP/SL calibration |
| Average Win / Average Loss | Mean return per winner vs. per loser | Validates risk/reward assumptions |
| Profit Factor | Gross profit / Gross loss | Single number capturing overall trade quality; must exceed 1.5 to be viable |
| Average Holding Period | Mean days from entry to exit | Signal of TP/SL tightness vs. market behavior |
| Annual Portfolio Turnover | Total notional traded / AUM | Converts to cost drag estimate |
| Maximum Consecutive Losses | Longest losing streak | Capital adequacy and psychology diagnostic |
| Exit Mechanism Breakdown | % of trades exiting via TP, SL, max-hold | Critical for diagnosing strategy mechanics |
| Rolling 3-Month Sharpe | Time-series of Sharpe | Identifies regime dependency |

---

## 7. Reporting Requirements Analysis

### 7.1 Charting Library Recommendation

**Plotly** is the correct choice for this project and is already listed in `requirements.txt`. Specifically:

- `plotly.graph_objects` provides the full API for interactive charts with hover, zoom, and filtering.
- `plotly.express` is faster for prototype charts.
- For the HTML export, use `fig.write_html("report.html", include_plotlyjs='cdn')` to keep file sizes manageable.

**Avoid**: D3.js (requires significant JavaScript expertise, no Python API), Bokeh (less polished for financial charts), plain matplotlib (no interactivity).

### 7.2 Benchmark Selection

The strategy should be benchmarked against multiple references:

1. **Primary**: SPY (S&P 500 total return ETF) — the default U.S. equity benchmark. Calculate the strategy's alpha and beta relative to SPY.
2. **Secondary**: IWM (Russell 2000 ETF) — if the universe tilts toward smaller-cap names, IWM is a more appropriate benchmark.
3. **Style-matched**: MTUM (momentum ETF) or a custom equal-weight long-only benchmark constructed from the same universe without the OS filter — this isolates the signal's contribution from pure market beta.

### 7.3 Trade Log Table Requirements

The trade log is described as including: ticker, company name, industry, buy/sell price, trade date, $r_{T-1}$, $v_{T-1}$, $D(r)_{T-1}$, $D(v)_{T-1}$, $OS_{T-1}$.

**Required additions to the trade log**:
- Exit date and exit type (TP, SL, max-hold)
- Holding period (days)
- PnL ($) and return (%)
- Transaction cost estimate per trade
- Net PnL after estimated costs

**Table functionality**: The table must be sortable, filterable, and searchable. In Plotly/Dash this requires `dash_table.DataTable`. If a static HTML is preferred (no server), use an embedded JavaScript library such as DataTables.js (can be included via CDN with no build step).

### 7.4 Additional Visualizations

Beyond the proposed daily return and total asset curves:

1. **Drawdown subplot**: Drawdown depth over time plotted below the equity curve.
2. **Rolling 12-month Sharpe**: Reveals regime dependency — does the strategy work in all market conditions?
3. **Monthly returns heatmap**: Calendar-format grid of monthly returns (year vs. month). Immediately reveals seasonal patterns and crisis periods.
4. **Return distribution histogram**: Show the distribution of per-trade returns with a normal overlay. This will reveal the fixed-TP clipping and the gap-through tail.
5. **Exit mechanism pie/bar chart**: Fraction of exits by type (TP, SL, max-hold) with average return for each category.
6. **Sector/industry concentration**: Bar chart of trade count and aggregate PnL by sector. If the strategy is implicitly a sector bet, this will expose it.
7. **Annual return comparison**: Bar chart of strategy annual return vs. SPY annual return, year by year.
8. **OS score distribution**: Histogram of OS scores at the time of trade entry. Verify the scores are meaningfully distributed and not degenerate.

---

## 8. Operational Considerations for Live Trading

### 8.1 Signal Computation Workflow

The recommended daily workflow for live trading:

1. **6:00 AM ET**: Previous day's OHLCV data finalized and ingested from data provider.
2. **6:30 AM ET**: Signal computation runs. OS scores computed for all universe constituents. Top-3 candidates ranked and identified.
3. **Pre-market**: Evaluate current holdings. Determine which positions to exit (if hold period exceeded, or if next-day signals are contradictory).
4. **3:30 PM ET**: Final candidate list locked. Check for any breaking news, halt notices, or corporate actions on candidates.
5. **3:45 PM ET**: MOC orders submitted for new buys. Limit-on-close (LOC) orders submitted for take-profit and stop-loss targets if intraday execution is desired.
6. **4:00 PM ET**: Closing auction. Fills received.
7. **4:30 PM ET**: PnL reconciliation. Update portfolio state. Log all fills.

### 8.2 Data Latency Requirements

The strategy requires only end-of-day data (previous day's close by 6:00 AM ET), which is the minimum latency tier available from virtually all data providers. Real-time or intraday data is not required for signal generation. However, intraday price monitoring is required if intraday stop-loss execution is desired (as opposed to executing stops at close or next-day open).

### 8.3 Monitoring Requirements

- **Daily**: Portfolio PnL reconciliation, signal recalculation, order fill verification.
- **Weekly**: Rolling Sharpe and drawdown metrics vs. backtest expectations. Alert if live Sharpe falls more than 1 standard deviation below backtest rolling average.
- **Monthly**: Universe refresh (add new listings, remove delistings), signal correlation stability check, factor exposure analysis.
- **Quarterly**: Full strategy audit against original backtest assumptions. Capacity reassessment if AUM changes.

---

## 9. Summary of Concerns & Recommendations

### 9.1 Issue Severity Rankings

**Critical — Must be resolved before any backtest code is written:**

| # | Issue | Impact |
|---|-------|--------|
| C1 | Survivorship bias in universe construction | Entire backtest is invalid without point-in-time universe data |
| C2 | Stop-loss fill assumption ignores gap risk | Losses systematically understated; strategy will appear better than it is |
| C3 | Intraday path assumption for TP/SL (OHLC bracket) | Fills assumed at exact levels; order precedence unknown from OHLC |
| C4 | Multiple testing problem with 6 hyperparameters | High probability of finding a spuriously overfit parameter set |

**Major — Must be addressed before trusting backtest results:**

| # | Issue | Impact |
|---|-------|--------|
| M1 | Adjusted price look-ahead (point-in-time corporate actions) | Subtle upward bias in long-term returns |
| M2 | Transaction cost model not specified | Backtest alpha may be entirely consumed by realistic costs |
| M3 | Same-day capital recycling is operationally optimistic | Models more trades per day than are executable in practice |
| M4 | No signal decay analysis (optimal K unknown) | Max-hold period $K$ is free parameter without empirical grounding |
| M5 | Insufficient performance metrics in proposed report | Cannot assess strategy quality from return curve + Sharpe alone |
| M6 | Missing OOS validation structure | In-sample optimization masquerading as genuine performance |

**Minor — Address before live deployment:**

| # | Issue | Impact |
|---|-------|--------|
| m1 | Equal weight vs. signal-proportional sizing | Leaves alpha on the table if OS score is predictive |
| m2 | No benchmark comparison in proposed report | Cannot assess whether strategy generates genuine alpha |
| m3 | Trade log missing exit type, PnL, and cost columns | Debugging and audit capability limited |
| m4 | Universe concentration risk not monitored | Hidden sector bets possible |
| m5 | No alert system for live strategy degradation | Live drawdowns may exceed tolerable levels before detection |

### 9.2 Prioritized Action List for Implementation Team

1. **Secure point-in-time universe data** (Sharadar or Polygon.io) before writing any data ingestion code. This cannot be retrofitted later.
2. **Lock execution assumptions in writing**: Define the exact fill model for TP, SL, and max-hold exits. Recommended: use next-day open for stop-loss exits, intraday bracket for take-profit (with acknowledgment of gap risk).
3. **Define the universe precisely**: Minimum market cap, minimum ADV, minimum price. Exclude OTC stocks, REITs, and ADRs unless explicitly desired.
4. **Fix parameters using economic priors** before any grid search: $N = 20$ (one trading month), $w_1 = w_2 = 0.5$ (equal weight, test sensitivity later), $K = 5$ (signal decay literature suggests ~5-day half-life for short-term reversal).
5. **Build signal decay analysis first**: Before building the full backtest engine, compute the average return by holding day (1, 2, ..., 20 days) using the base signal. This informs the optimal $K$ with evidence.
6. **Implement transaction cost module**: Model each trade with bid-ask spread (10 bps), market impact (function of order size / ADV), and commission (1 bp). Run the backtest with costs from day one, not as an afterthought.
7. **Structure walk-forward correctly**: IS = 2014–2019, OOS = 2020–2024. Do not touch OOS until all IS optimization is complete.
8. **Implement all performance metrics** from section 6.3 before presenting any results. A report showing only Sharpe and MDD is insufficient for strategy assessment.

### 9.3 Suggested Initial Parameters for First Backtest

The following parameter configuration is chosen to be economically motivated (not optimized) and to minimize hyperparameter degrees of freedom:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| $N$ | 20 | One trading month; natural short-term reversal lookback |
| $w_1$ | 0.5 | Equal weight; no prior for dominance of return vs. volume |
| $w_2$ | 0.5 | Equal weight |
| win\_take\_rate | 0.03 | 3% take-profit; consistent with 1–5 day reversal magnitude |
| stop\_loss\_rate | 0.02 | 2% stop-loss; gives win/loss ratio of 1.5, break-even at ~40% win rate |
| $K$ | 5 | 5-day max-hold; consistent with short-term reversal alpha decay |

Run this configuration first, examine the signal decay curve, exit mechanism breakdown, and cost-adjusted performance before any parameter optimization. If the unoptimized configuration shows no alpha, optimization will produce a backtest artifact, not a real strategy.

---

## Appendix: Key Formulas Reference

**Oversell Score**:
$$OS_{T-1} = w_1 \cdot \frac{|r_{T-1}| - \overline{|r|}_{T-1}}{\sigma(|r|)_{T-1}} + w_2 \cdot \frac{v_{T-1} - \bar{v}_{T-1}}{\sigma(v)_{T-1}}$$

**Square-root market impact model**:
$$\text{Impact (bps)} \approx \sigma_{\text{daily}} \cdot \sqrt{\frac{\text{Trade Size}}{\text{ADV}}} \cdot 10000$$

**Kelly fraction (single bet)**:
$$f^* = \frac{\mu}{\sigma^2}$$

**Break-even win rate given fixed TP and SL**:
$$p_w^{\min} = \frac{s}{w + s}$$

where $w$ = win\_take\_rate, $s$ = stop\_loss\_rate.

**Calmar Ratio**:
$$\text{Calmar} = \frac{\text{CAGR}}{|\text{MDD}|}$$

**Sortino Ratio**:
$$\text{Sortino} = \frac{\bar{R}_p - R_f}{\sigma_{\text{downside}}} \cdot \sqrt{252}, \quad \sigma_{\text{downside}} = \sqrt{\frac{1}{T}\sum_{t=1}^{T} \min(R_t - R_f, 0)^2}$$

---

*This review was conducted as a pre-implementation peer review. All concerns should be addressed and documented before the backtesting engine is built. No results generated without resolving Critical issues C1–C4 should be trusted or presented externally.*

# Critical Review: Oversell Score Strategy — Signal Quality Assessment

**Date:** 2026-02-24
**Reviewer:** Quant Research (Senior)
**Status:** Pre-Implementation Peer Review
**Backtest Period:** ~2014–2024 (10 years)
**Initial Capital:** $500,000

---

## Executive Summary

The proposed strategy attempts to exploit short-term mean reversion following abnormal price moves accompanied by abnormal volume — a well-documented behavioral phenomenon in academic literature. The core economic intuition is sound. However, the mathematical formulation as written contains a **fundamental directional ambiguity** that transforms the "oversell" hypothesis into a generic "extreme move" detector, treating panic selling and euphoric buying identically. This is not a minor refinement issue; it is a critical flaw that invalidates the strategy's stated thesis.

Beyond the directional problem, the strategy exhibits five additional material concerns: extreme concentration risk (3 stocks), survivorship bias exposure, subtle look-ahead bias in the entry price assumption, high hyperparameter dimensionality with significant overfitting risk, and an unstable normalization scheme during volatility regime shifts. Several of these issues are fixable with targeted redesign. The remainder of this document provides a rigorous treatment of each concern with concrete recommendations.

---

## 1. Factor Validity and Economic Rationale

### The Hypothesis

The strategy's implicit thesis is: **stocks that experience abnormally large price declines on abnormally large volume have been oversold by panic or forced sellers, creating a temporary price dislocation that will mean-revert over the subsequent $K$ trading days.**

This is a coherent and empirically grounded hypothesis. The behavioral finance literature offers several reinforcing mechanisms:

- **Liquidity provision premium**: When forced sellers (margin calls, redemptions, stop-loss cascades) dump shares into a thin market, prices overshoot fundamentals. Patient capital earns a liquidity premium by stepping in.
- **Overreaction hypothesis** (De Bondt and Thaler, 1985): Investors systematically overreact to negative news, creating reversals. Short-horizon reversals (1–5 days) are among the most replicated anomalies in the empirical finance literature.
- **Microstructure effects**: High-volume down days often reflect inventory imbalance in market makers. Market maker inventory rebalancing over 1–3 days mechanically creates short-term upward price pressure.
- **Post-earnings announcement drift (PEAD)** as a confound: If extreme moves coincide with earnings, the mean-reversion hypothesis may be overwhelmed by fundamental information. The signal does not distinguish these cases.

### Conditions Under Which the Factor Works

The mean-reversion mechanism is strongest when:
1. The price move is driven by **non-fundamental noise or forced selling**, not genuine information.
2. Market liquidity is adequate for entry and exit at reasonable spreads.
3. The broader market regime is calm (VIX in a normal range). In severe bear markets, "extreme down moves" are trending, not mean-reverting.
4. The holding period $K$ is short enough to capture the reversion before new fundamental information arrives.

### Conditions Under Which the Factor Fails

- **Momentum regimes**: In trending markets, extreme moves are often the beginning of a new trend, not a reversal.
- **Crisis periods**: 2008, March 2020, and October 2022 saw persistent selling where mean reversion failed repeatedly over multi-week horizons.
- **Small/micro-cap stocks**: Extreme moves in illiquid names often reflect genuine information (fraud, SEC investigation, contract loss) that is permanent, not transient.
- **Post-catalyst stocks**: Earnings misses, guidance cuts, and FDA rejections produce permanent repricing, not mean reversion.

The strategy has no regime filter, no catalyst screen, and no fundamental quality filter. It will systematically buy into both temporary dislocations (correct) and permanent value destructions (incorrect). This is the most important practical limitation.

---

## 2. Mathematical Formulation Critique

### 2.1 The Directional Ambiguity — A Critical Flaw

The return deviation is formulated as:

$$D(r)_T = \frac{|r_T| - \overline{|r|}_T}{\sigma(|r|)_T}$$

The use of absolute value $|r_T|$ means the signal is **symmetric with respect to direction**. A stock that rises +8% on extreme volume and a stock that falls -8% on extreme volume will receive identical $D(r)$ scores.

This is a fundamental mismatch between the stated hypothesis and the mathematical implementation. The strategy is named "Oversell" and the thesis is that panic selling creates mean-reverting opportunities. But the signal as written is an **"extreme move detector"** — it selects the most anomalous price changes regardless of whether those changes were up or down.

The consequence is that the backtest will systematically include a population of recently-surged stocks alongside recently-crashed stocks. These two groups have opposite expected return profiles under the mean-reversion hypothesis. Mixing them will dilute — and potentially invert — the alpha of the strategy.

**The correct formulation for an oversell signal should use signed returns:**

$$D(r)_T = \frac{r_T - \overline{r}_T}{\sigma(r)_T}$$

where $r_T$ is the **signed** daily return. Under this formulation, large negative returns receive highly negative $z$-scores, and selecting stocks with the **lowest** (most negative) $D(r)$ scores correctly identifies abnormal down-movers.

Alternatively, if the symmetric formulation is retained intentionally to capture both oversold and overbought conditions, the strategy must be **bifurcated**: a long-short design where top scorers with negative returns are bought and top scorers with positive returns are sold short. As a long-only strategy, the symmetric formulation is not defensible.

### 2.2 Volume Formulation — Redundant Absolute Value

$$D(v)_T = \frac{|v_T| - \overline{|v|}_T}{\sigma(|v|)_T}$$

Volume is a strictly non-negative quantity by definition: $v_T \geq 0$ always. Therefore $|v_T| \equiv v_T$, and the absolute value is mathematically redundant. This is not a bug that affects output, but it reflects imprecision in the specification that warrants correction in the code. The formula should be written as:

$$D(v)_T = \frac{v_T - \bar{v}_T}{\sigma(v)_T}$$

More importantly, volume $z$-scores have well-known distributional properties that the current formula ignores. Raw volume is highly right-skewed — a single block trade or short squeeze can produce a $z$-score of 20+ while the distribution of normal days clusters near zero. This means $D(v)$ is dominated by extreme outliers and is **not** well-approximated by a Gaussian. The log transformation is standard practice:

$$D(v)_T = \frac{\log(v_T) - \overline{\log(v)}_T}{\sigma(\log(v))_T}$$

The log transformation compresses the right tail, produces a more Gaussian distribution, and makes the $z$-score a more stable and interpretable measure of abnormal volume.

### 2.3 The Linear Combination — Appropriateness and Limitations

$$OS_{T-1} = w_1 \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}$$

The linear combination is parsimonious and defensible as a first-order approximation. However, the economic hypothesis suggests an **interaction effect** is more appropriate: extreme price moves on normal volume may reflect algorithmic noise or index rebalancing and are less likely to represent genuine overselling. Extreme price moves on extreme volume are the clearest signal of panic selling.

The interaction term captures this:

$$OS_{T-1} = D(r)_{T-1} \cdot D(v)_{T-1}$$

or equivalently in a regression form:

$$OS_{T-1} = w_1 \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1} + w_3 \cdot D(r)_{T-1} \cdot D(v)_{T-1}$$

The multiplicative form has the property that both conditions must simultaneously be extreme for the score to be high, which better matches the stated hypothesis. The additive form allows a very large volume spike on an ordinary price day (e.g., a spin-off distribution date) to rank highly, which is not economically meaningful for mean reversion.

The choice between additive and multiplicative should be tested empirically, but the interaction term has a clear prior economic justification.

### 2.4 Statistical Properties of $D(r)$ and $D(v)$

Both $z$-score transformations assume approximate normality in the underlying distribution, but equity returns and volumes are well-documented to be non-Gaussian:

- **Returns**: heavy tails (kurtosis typically 5–15 for daily returns), slight negative skew. The rolling $z$-score of absolute returns will itself be right-skewed because $|r|$ is a folded normal that approximates a half-normal, not a normal.
- **Volume**: strongly right-skewed (log-normal is a far better model). Without log transformation, a single outlier day (e.g., earnings announcement volume 10x normal) will dominate the $z$-score for the entire $N$-day window.
- **Outlier sensitivity**: The rolling mean and standard deviation used in both $D(r)$ and $D(v)$ are non-robust estimators. A single extreme event within the $N$-day window inflates the rolling mean and standard deviation, making subsequent $z$-scores understated. Robust alternatives (rolling median and MAD, or winsorized moments) would produce more stable signals.

Winsorizing the inputs at the 1st and 99th percentile before $z$-scoring is a practical and widely-used solution that does not require changing the fundamental formula structure.

---

## 3. Lookback Window and Stationarity

### 3.1 Effect of the Lookback Window $N$

The choice of $N$ governs what "normal" means for each stock. This has profound implications:

- **Short $N$ (e.g., 5–20 days)**: The baseline adapts quickly to recent volatility. In a volatile market, a large move will normalize against other recent large moves and receive a lower score. This creates a **regime-following** behavior that reduces signal during crises — potentially desirable (avoids buying into sustained downtrends) or undesirable (misses genuine oversold conditions).
- **Long $N$ (e.g., 60–252 days)**: The baseline is stable and reflects the stock's long-run average behavior. A move that is extreme relative to its 1-year history will score highly even if recent weeks have been volatile. This creates **regime-contrarian** behavior, giving higher scores during volatility spikes — potentially undesirable if the volatility reflects a fundamental regime change.

Neither choice is universally correct. The appropriate $N$ depends on the holding period $K$ and the economic mechanism. For a 1–5 day mean reversion hypothesis, a medium window ($N$ = 20–60 days) is likely most appropriate, but this conclusion should be validated empirically.

**Interaction with the 2020 COVID crash**: During March 2020, daily moves of 5–15% became routine. A short $N$ window would normalize these against each other, suppressing scores. A long $N$ window would flag every day as extreme. Neither behavior is ideal. This argues for incorporating a **VIX-based regime filter** that deactivates or adjusts the signal during crisis periods.

### 3.2 Rolling Normalization Stationarity

The rolling $z$-score is adaptive by construction, which provides a form of pseudo-stationarity. However, stationarity is not guaranteed:

- During volatility regime shifts (low to high, or high to low), the first $N$ days after the shift will contain a mix of old-regime and new-regime data. The $z$-score will be miscalibrated during this transition period.
- The distribution of $D(r)$ and $D(v)$ is itself time-varying, which means the top-3 selection threshold (implicitly at the 99th+ percentile of the cross-sectional distribution) changes over time. Normalizing cross-sectionally at each $T$ — ranking stocks relative to each other on the same day — is more robust than relying on each stock's time-series $z$-score alone.

### 3.3 Fat-Tailed Return Behavior and $z$-Score Instability

When equity returns exhibit fat tails (kurtosis >> 3), the empirical standard deviation computed over $N$ days can vary dramatically depending on whether extreme events fall inside or outside the window. This creates the following pathology:

- After a large single-day move, the stock's $\sigma(|r|)$ increases sharply, causing the $z$-score to **decrease** for subsequent moves of the same magnitude.
- The signal therefore tends to **fade** precisely when mean reversion is most warranted — immediately after the initial extreme move — and **increase** several weeks later when the event exits the window and the baseline normalizes downward.

This timing mismatch between signal strength and expected return opportunity is a material weakness of the $z$-score normalization approach in the presence of fat tails.

---

## 4. Signal Timing and Look-Ahead Bias

### 4.1 The Stated Data Flow

The specification states: compute $OS_{T-1}$ using data through day $T-1$, rank stocks at the start of day $T$, and **buy at the close of day $T$**.

At first pass, this appears clean: the signal uses yesterday's data, and the trade executes today. There is no future data contamination in the signal itself.

### 4.2 The Subtle Bias in Entry Price

The critical question is: **can you actually buy at the close of day $T$?**

Buying "at close" in a backtest means the execution price equals the official exchange closing print. In live trading, this requires submitting a Market-on-Close (MOC) order before the MOC order cutoff (typically 3:45–3:50 PM ET for NYSE/NASDAQ). This is achievable, but it introduces the following consideration:

During day $T$, price action is evolving. If the stock selected by yesterday's OS score happens to continue declining intraday on day $T$ (a momentum continuation rather than a reversal), buying the close means buying into continued weakness — which is consistent with the mean-reversion thesis and not a bias.

However, if the **close price on day $T$ is itself included in the returns that inform the next day's OS score**, there is a subtle downstream consistency requirement: the backtest must ensure that $r_T$ (used to compute $OS_T$ for signals on day $T+1$) uses the actual close of day $T$, not an assumed execution price. This is a data consistency requirement, not a look-ahead bias per se, but it is a common source of subtle errors in backtesting frameworks.

### 4.3 Practical Execution Concern — More Material Than Bias

The larger practical concern is not look-ahead bias but **execution realism**. Buying at exactly the closing price every day is an optimistic assumption:

- MOC orders receive the official closing price with high reliability for large-cap stocks. For small/mid-cap stocks, the closing auction can be thin and the realized fill may differ from the official print.
- Transaction cost assumptions must include both commissions and the bid-ask spread at the close. For small-cap stocks, the spread at the close can be 20–50 basis points or more.
- For a $500,000 portfolio split across 3 positions, each position is approximately $167,000. Market impact is modest for large-caps but potentially significant for stocks with average daily dollar volume below $5–10 million.

---

## 5. Universe and Data Considerations

### 5.1 Universe Definition

The strategy description notes the universe is "presumably all liquid U.S. stocks." This ambiguity must be resolved before any backtest is conducted. The universe definition is not a stylistic choice — it is a fundamental determinant of strategy behavior and estimated capacity.

**Micro/nano-cap stocks should be excluded.** Stocks with market cap below $300M or average daily dollar volume below $1M are:
- More likely to have extreme moves driven by information (penny stock manipulation, news catalysts) rather than forced selling
- Illiquid enough that a $167K position creates meaningful market impact
- Subject to survivorship bias: many extreme-move small-caps from 2014 no longer exist in the data

A reasonable minimum liquidity filter: **average daily dollar volume > $5M over the prior 20 days**, plus **market cap > $500M**. This retains several thousand stocks while excluding the most problematic names.

### 5.2 Data Adjustments

The backtest must use **split-adjusted and dividend-adjusted (total return) prices** for all calculations. Using unadjusted prices will produce spurious return calculations around corporate actions. This is table stakes, not optional.

Specifically:
- Dividend-adjusted prices prevent the signal from flagging ex-dividend drops as "extreme negative moves" — a stock that drops 3% on its ex-dividend date with its $3% dividend simultaneously captured is not oversold.
- Split adjustments prevent artificial return spikes (a 2-for-1 split looks like a -50% return on an unadjusted basis).

### 5.3 Survivorship Bias

This is a critical and often-underestimated source of backtest inflation. If the stock universe used in the backtest consists of companies that **currently exist** (i.e., are trading today in 2024), the historical backtest will implicitly exclude:

- Companies that went bankrupt (whose extreme down-moves were permanent)
- Companies that were acquired (which sometimes remove stocks mid-recovery)
- Companies that were delisted for non-compliance

A mean-reversion strategy is **particularly vulnerable** to survivorship bias. The extreme-move stocks that did **not** recover are precisely the ones excluded from a survivorship-biased universe. The backtest will show higher win rates on the long side than would have been achievable historically.

The correct approach requires a **point-in-time universe** — a historical database that includes all stocks that were trading on each date, including those that subsequently ceased to exist. Sources for this include Compustat (via WRDS), CRSP, or Sharadar. Using Yahoo Finance or a similar free data source without a point-in-time universe introduces survivorship bias by construction.

### 5.4 Additional Data Filters

- **Penny stocks**: Exclude stocks trading below $1 (or $5 for a more conservative filter). Extreme percentage moves are mechanically more common in low-priced stocks.
- **Recent IPOs**: Exclude stocks within 6–12 months of their IPO. Price discovery during this period is fundamentally different, and volume baselines are unreliable.
- **Halted stocks**: Ensure data handling correctly identifies stocks that were trading halts; a halt followed by a reopening creates a synthetic "extreme move" that is not mean-reverting in the standard sense.

---

## 6. Factor Concentration Risk

### 6.1 Extreme Concentration

Holding exactly 3 stocks at all times is an extremely concentrated portfolio. At $500,000 AUM, each position is approximately $167,000. The portfolio has essentially zero diversification in the classical sense.

The Sharpe ratio of a 3-stock portfolio is dominated by idiosyncratic risk. For context: a random 3-stock portfolio of U.S. equities has a standard deviation approximately 3× higher than the market portfolio (roughly 50–60% annualized vs. 15–20% for the market). The strategy's realized volatility will likely be in the 40–80% annualized range, and drawdowns of 30–50% from peak are plausible even for a strategy with genuine alpha.

This is not inherently fatal for a small fund — concentrated positions with high conviction are a legitimate strategy — but the risk parameters must be calibrated to this reality. Presenting Sharpe ratios or drawdown statistics for a 3-stock portfolio without contextualizing the concentration risk would be misleading.

### 6.2 Correlation Structure of Top-Ranked Stocks

The scoring mechanism ranks stocks cross-sectionally, which means the top-3 stocks share the property of having experienced simultaneous extreme moves. On many days, this will imply:

- **Sector clustering**: Market-wide sector rotations (e.g., tech selloff, energy dump) affect many stocks simultaneously. The top-3 by OS score on a given day may all be technology stocks, all be energy stocks, or all be from the same sector that experienced a news-driven selloff.
- **Market beta clustering**: During broad market selloffs, the highest OS scores will cluster in high-beta stocks. The portfolio will systematically load up on high-beta names immediately after market drops — which is a bet on market mean reversion, not individual stock mean reversion.
- **Implicit factor loading**: Without controlling for sector or factor exposures, the strategy likely carries significant and time-varying exposure to market beta, size, momentum (reversal), and sector factors. These exposures are not by design — they are accidental byproducts of the scoring and selection process.

A sector diversification constraint (no more than 1 stock from the same GICS sector) or a factor-neutral construction would improve the signal's purity.

### 6.3 Position Sizing

The strategy as specified uses equal weighting across the 3 selected stocks. There is no differentiation based on signal strength, expected volatility, or correlation. A signal-strength-weighted or inverse-volatility-weighted approach would improve the risk-adjusted allocation without adding significant complexity.

---

## 7. Hyperparameter Sensitivity and Overfitting Risk

### 7.1 Parameter Count

The strategy has the following free parameters:

| Parameter | Role | Typical Range |
|-----------|------|---------------|
| $N$ | Lookback window | 10–252 days |
| $w_1$ | Return deviation weight | 0–1 (with $w_1 + w_2 = 1$) |
| $w_2$ | Volume deviation weight | 0–1 |
| $\text{win\_take\_rate}$ | Take-profit level | 2%–20% |
| $\text{stop\_loss\_rate}$ | Stop-loss level | 1%–15% |
| $K$ | Maximum holding period | 1–30 days |

This is 6 degrees of freedom (or 5 if $w_1 + w_2 = 1$ is enforced). With a 10-year backtest and a short-horizon strategy generating hundreds or thousands of trades per year, there is sufficient data to fit these parameters in-sample — which means the overfitting risk is real and significant.

The number of distinct parameter combinations in a reasonable search grid is easily in the thousands. Even if no deliberate data mining is performed, the researcher's natural tendency to examine results and "tune" toward better outcomes constitutes implicit multiple testing. Standard corrections (Bonferroni, Benjamini-Hochberg) should be applied, but more practically, **walk-forward optimization** is the correct methodology.

### 7.2 The Weights $w_1$ and $w_2$ Are Likely Unidentifiable

Because $D(r)$ and $D(v)$ are both $z$-scores with mean ~0 and standard deviation ~1, they are on comparable scales. However, their information content is asymmetric: the return signal is more directly tied to the economic hypothesis (mean reversion after large price moves), while the volume signal is a conditioning variable. In many empirical studies of short-term reversal, adding volume as a filter improves precision but volume alone has limited predictive power.

This suggests a reasonable prior that $w_1 >> w_2$. Testing whether $w_2 > 0$ adds significant out-of-sample value is an important validation step. If the strategy performs similarly with $w_2 = 0$, the volume component is adding noise rather than signal and should be dropped or redesigned.

### 7.3 Walk-Forward Optimization Framework

Correct procedure for this strategy:

1. Split the 10-year sample into a rolling training window (e.g., 3 years) and a forward test window (e.g., 6 months).
2. On the training window, optimize parameters using a robust objective (e.g., Sharpe ratio, but penalized for in-sample overfitting via information ratio of simulated OOS).
3. Apply the resulting parameters **without modification** to the forward test window. Record performance.
4. Roll forward by 6 months and repeat.
5. The reported performance is the concatenation of the forward test windows only.

The walk-forward test will reveal parameter stability (or instability) over time. If optimal parameters change dramatically across windows, the strategy is not robust. If parameters are stable and OOS performance is consistent with in-sample expectations, the signal has genuine predictive content.

---

## 8. Summary of Concerns and Recommendations

### 8.1 Issues Ranked by Severity

**CRITICAL**

1. **Directional ambiguity in $D(r)$**: The use of $|r_T|$ means the signal is symmetric — it selects both large up-movers and large down-movers. This directly contradicts the "oversell" hypothesis. The strategy as formulated is an "extreme move detector," not an "oversell detector." Fix: use signed returns and select stocks with the most negative $z$-scores, or bifurcate into a long-short strategy.

2. **Survivorship bias exposure**: If the stock universe is not point-in-time, the backtest results are fiction. Mean-reversion strategies are particularly vulnerable because they buy falling stocks, many of which went to zero or were delisted. Fix: use a point-in-time universe (CRSP, Compustat, or Sharadar).

**MAJOR**

3. **No regime filter**: The strategy will systematically buy into sustained downtrends during bear markets and crises. Without a VIX-based or trend-based regime filter, the strategy will produce deep, extended drawdowns in 2015–2016, 2018 Q4, March 2020, and 2022. Fix: deactivate or reduce position size when VIX > 30 or when SPY is below its 200-day moving average.

4. **Extreme concentration (3 stocks)**: Idiosyncratic risk will dominate portfolio returns. The strategy needs to be framed as a high-risk, high-conviction approach, and risk management (position limits, portfolio-level stop losses) must be explicit. Fix: increase to 5–10 stocks minimum, or implement portfolio-level stop logic.

5. **No liquidity or universe filter**: Without minimum market cap and volume filters, the backtest will include illiquid small-caps where the strategy's extreme-move signal fires most frequently but where execution is worst and permanent-impairment risk is highest. Fix: minimum $5M average daily dollar volume and $500M market cap.

6. **No catalyst filter**: Extreme moves on earnings, FDA decisions, and M&A announcements are not driven by panic selling — they reflect genuine information. Including these events inflates the false positive rate. Fix: implement an earnings calendar filter that excludes stocks in the 2-day window around scheduled announcements.

**MINOR**

7. **Log transformation missing from volume $z$-score**: Raw volume is right-skewed; log(volume) is approximately normal. The current formulation is dominated by outliers. Fix: apply $\log(v_T)$ before computing the $z$-score.

8. **Absolute value redundant in $D(v)$**: Volume is non-negative; $|v_T| = v_T$ always. This is cosmetic but reflects specification imprecision.

9. **Non-robust statistics**: Rolling mean and standard deviation are sensitive to outliers. Fix: use rolling median and MAD (median absolute deviation), scaled to be comparable to standard deviation under normality.

10. **Linear combination vs. interaction**: The additive score can rank high on volume alone without a price move. The interaction term $D(r) \cdot D(v)$ better captures the joint condition of "extreme price move AND extreme volume." Fix: test multiplicative formulation.

### 8.2 Alternative Factor Formulations Worth Exploring

Several well-studied alternatives should be benchmarked against the proposed factor:

- **Signed short-term reversal (pure price)**: Rank on prior-day signed return. Simple, well-documented, Sharpe ~0.4–0.6 after costs in academic literature. Useful as a baseline.
- **Illiquidity-weighted reversal**: $OS = r_{T-1} \cdot \text{Illiquidity}_{T-1}$, where illiquidity is the Amihud (2002) ratio. Stocks with large price moves per unit of volume are more likely to be mispriced. Strongly supported empirically.
- **Rolling $z$-score on signed returns with volume as a filter** (rather than additive component): Rank by $D(r)$ on negative returns only, and require $D(v) > 1.0$ as a binary filter. This is more conservative and better matches the stated hypothesis.
- **Intraday reversal signal**: Use the intraday high-to-close ratio or the gap between the VWAP and closing price as a measure of late-day selling pressure. More complex but captures intraday dynamics not available in OHLCV data.

### 8.3 Priority Implementation Roadmap

If proceeding with development, the recommended sequence is:

1. Fix the directional ambiguity — use signed $r_T$ and select most-negative $z$-scores.
2. Build with a point-in-time universe and survivorship-bias-free data.
3. Apply minimum liquidity filters and exclude earnings-window stocks.
4. Implement log-volume $z$-score.
5. Add a VIX-based regime filter.
6. Test the multiplicative vs. additive score combination.
7. Expand the universe to 5–10 stocks with position sizing improvements.
8. Run full walk-forward optimization over the 10-year sample.
9. Benchmark against signed short-term reversal and Amihud illiquidity-weighted reversal as baselines.

---

## Appendix: Notation Summary

| Symbol | Definition |
|--------|-----------|
| $r_T$ | Signed daily return on day $T$ |
| $\|r_T\|$ | Absolute daily return on day $T$ |
| $\overline{\|r\|}_T$ | Rolling mean of absolute returns over prior $N$ days |
| $\sigma(\|r\|)_T$ | Rolling standard deviation of absolute returns over prior $N$ days |
| $v_T$ | Volume on day $T$ (always $\geq 0$) |
| $D(r)_T$ | Return deviation $z$-score on day $T$ |
| $D(v)_T$ | Volume deviation $z$-score on day $T$ |
| $OS_{T-1}$ | Oversell score computed using data through day $T-1$ |
| $N$ | Lookback window (hyperparameter) |
| $w_1, w_2$ | Weights in linear combination (hyperparameters) |
| $K$ | Maximum holding period in trading days (hyperparameter) |
| $p$ | Entry price (close of day $T$) |

---

*This document reflects a pre-implementation peer review based on the strategy specification. All conclusions are subject to revision upon examination of actual backtest results, code implementation, and data sources.*

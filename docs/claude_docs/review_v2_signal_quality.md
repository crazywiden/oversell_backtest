# Second-Round Critical Review: Oversell Score Strategy v2 — Signal Quality Assessment

**Date:** 2026-02-24
**Reviewer:** Senior Quant Researcher
**Review Round:** v2 (Second Pass)
**Prior Review:** `review_signal_quality.md` (v1)
**Status:** Pre-Implementation Peer Review

---

## Executive Summary

Version 2 of the Oversell Score strategy addresses the most visible issue from the v1 review — the loss of sign in the return deviation factor — but the fix is incomplete and introduces a new, equally serious problem. The sign has been restored to $D(r)_T$, which correctly distinguishes oversold from overbought stocks. However, the strategy then selects the **top 3** stocks by $OS$ score without specifying the signs of the weights $w_1$ and $w_2$. Under the most natural reading of the formula (both weights positive), the "top 3" selection picks the most **overbought** stocks, inverting the oversell thesis entirely. This is not a minor calibration issue — it is a directional inversion that would cause the strategy to systematically do the opposite of what it intends.

Beyond this critical new issue, four of the five remaining v1 concerns are entirely unaddressed: survivorship bias, regime filter absence, 3-stock concentration, and log-volume normalization. The liquidity filter ("large volume") is nominally present but operationally undefined, providing false specification confidence without actually constraining the universe.

This document examines each issue in full analytical detail. The strategy cannot be validly backtested until the directionality inversion is resolved and the weight sign convention is explicitly locked in.

---

## Section 1: Analysis of the D(r) Sign Fix

### 1a. What the New Formula Produces for Different Stock Types

The v2 return deviation formula is:

$$D(r)_T = \text{sign}(r_T) \cdot z\text{-score}(|r_T|) = \frac{r_T}{|r_T|} \cdot \frac{|r_T| - \overline{|r|}_T}{\sigma(|r|)_T}$$

To understand what this produces in practice, consider four representative cases. In each case, assume the rolling mean of absolute returns is $\overline{|r|} = 1.0\%$ and the rolling standard deviation of absolute returns is $\sigma(|r|) = 0.8\%$.

**Case 1 — Large drop (oversold candidate):** $r_T = -8\%$

$$\text{sign}(r_T) = -1, \quad z\text{-score}(|r_T|) = \frac{0.08 - 0.01}{0.008} = +8.75$$

$$D(r)_T = (-1) \cdot (+8.75) = \mathbf{-8.75}$$

**Case 2 — Large rise (overbought candidate):** $r_T = +8\%$

$$\text{sign}(r_T) = +1, \quad z\text{-score}(|r_T|) = \frac{0.08 - 0.01}{0.008} = +8.75$$

$$D(r)_T = (+1) \cdot (+8.75) = \mathbf{+8.75}$$

**Case 3 — Normal drop:** $r_T = -1\%$

$$\text{sign}(r_T) = -1, \quad z\text{-score}(|r_T|) = \frac{0.01 - 0.01}{0.008} = 0.0$$

$$D(r)_T = (-1) \cdot (0.0) = \mathbf{0.0}$$

**Case 4 — Normal rise:** $r_T = +1\%$

$$\text{sign}(r_T) = +1, \quad z\text{-score}(|r_T|) = \frac{0.01 - 0.01}{0.008} = 0.0$$

$$D(r)_T = (+1) \cdot (0.0) = \mathbf{0.0}$$

**Summary of sign behavior:**

| Stock Type | $r_T$ | $D(r)_T$ | Interpretation |
|------------|-------|-----------|----------------|
| Large drop (oversold) | $-8\%$ | $-8.75$ | Large **negative** value |
| Large rise (overbought) | $+8\%$ | $+8.75$ | Large **positive** value |
| Normal drop | $-1\%$ | $0.0$ | Near zero |
| Normal rise | $+1\%$ | $0.0$ | Near zero |

The v2 fix correctly restores directionality. An oversold stock (large negative return) now produces a large **negative** $D(r)_T$. An overbought stock produces a large **positive** $D(r)_T$. This is mathematically coherent and represents a genuine improvement over v1.

### 1b. CRITICAL DIRECTIONALITY ISSUE: The Ranking Inversion

The correction in Section 1a is necessary but not sufficient. The restored sign changes the interpretation of $D(r)_T$ — but then the strategy selects the **top 3** stocks by $OS_{T-1}$ score. Whether this selects oversold or overbought stocks depends entirely on the sign of $w_1$, which is not specified in the v2 strategy description.

To be explicit, consider an oversold stock: large negative return ($D(r) \ll 0$) with high volume ($D(v) \gg 0$). The OS score is:

$$OS = w_1 \cdot D(r) + w_2 \cdot D(v)$$

For a concrete example, let $D(r) = -8.75$ and $D(v) = +4.0$.

**Case A: $w_1 > 0$, $w_2 > 0$ (e.g., $w_1 = w_2 = 0.5$)**

$$OS = 0.5 \cdot (-8.75) + 0.5 \cdot (+4.0) = -4.375 + 2.0 = \mathbf{-2.375}$$

Selecting the **top 3** (most positive OS) excludes this stock. The strategy instead selects stocks with the most **positive** $D(r)$ — the largest recent **upward** movers. This is a momentum or overbought-buying strategy, which is the exact opposite of the stated oversell mean-reversion thesis.

**Case B: $w_1 < 0$, $w_2 > 0$ (e.g., $w_1 = -0.5$, $w_2 = +0.5$)**

$$OS = (-0.5) \cdot (-8.75) + 0.5 \cdot (+4.0) = +4.375 + 2.0 = \mathbf{+6.375}$$

Selecting the **top 3** now correctly identifies this stock as the highest-ranked oversold candidate. This is the only weight sign combination that implements the oversell mean-reversion hypothesis.

**Case C: $w_1 > 0$, $w_2 < 0$ (e.g., $w_1 = +0_5$, $w_2 = -0.5$)**

$$OS = 0.5 \cdot (-8.75) + (-0.5) \cdot (+4.0) = -4.375 - 2.0 = \mathbf{-6.375}$$

The strategy now selects stocks with the largest positive return and the lowest volume — a low-volume breakout pattern with no economic rationale for mean reversion.

**Formal analysis of all sign combinations:**

| $(w_1, w_2)$ | OS for oversold stock | "Top 3" selects | Thesis alignment |
|--------------|----------------------|-----------------|-----------------|
| $(+, +)$ | Negative (excluded) | Overbought stocks | INVERTED — opposite of thesis |
| $(-, +)$ | Positive (included) | Oversold stocks | CORRECT |
| $(+, -)$ | Negative (excluded) | Low-vol breakouts | No economic rationale |
| $(-, -)$ | Positive (included) | Oversold + low-vol | Partial — contradicts the volume-amplifies-signal intuition |

**The only combination that correctly implements the oversell thesis is $w_1 < 0$, $w_2 > 0$.**

The v2 specification does not state whether $w_1$ is positive or negative. The weights are described as unspecified hyperparameters. Without this specification, the strategy's direction is undefined. A developer implementing the strategy with the natural assumption that both weights are positive will build an overbought momentum strategy while believing they are building an oversell mean-reversion strategy. This is a critical correctness failure that the v2 update did not resolve.

### 1c. Alternative Formulations That Avoid the Ambiguity

Three cleaner formulations exist, each resolving the directionality ambiguity through structural design rather than weight sign convention.

**Option A — Define OS as most negative for oversold, select bottom 3:**

$$OS_{T-1} = D(r)_{T-1} - \lambda \cdot D(v)_{T-1}$$

where $\lambda > 0$. An oversold stock ($D(r) \ll 0$, $D(v) \gg 0$) will produce the most negative OS scores. The strategy selects the **bottom 3** (most negative). This makes the sign convention self-documenting: the formula structure itself makes clear that low scores are "most oversold."

Advantage: The factor structure directly encodes the hypothesis — oversold means large negative deviation on both price and volume dimensions (using the minus sign to make them reinforce). The selection rule ("bottom 3") matches the economic intuition ("most oversold").

Disadvantage: The minus sign on $D(v)$ may seem counterintuitive — it reads as "high volume is bad for the score," when economically it should be "high volume amplifies the oversold signal." This requires careful documentation.

**Option B — Negate $D(r)$, retain top 3:**

$$OS_{T-1} = -|w_1| \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}, \quad w_2 > 0$$

Selecting the **top 3** now correctly identifies oversold stocks. The sign convention is explicit: the negative on $D(r)$ is structural (written as $-|w_1|$), not an optimization variable that could accidentally be flipped. This is equivalent to Case B above but with the sign fixed in the formula structure rather than left to the weight optimizer.

**Option C — Use standard signed z-score of raw returns:**

$$D(r)_T = \frac{r_T - \bar{r}_T}{\sigma(r)_T}$$

This is the standard z-score of raw (signed) returns, not of absolute returns. Select the **bottom 3** by OS score.

This formulation has important differences from the v2 formula:
- The distribution is centered on $\bar{r}$ (typically near zero), so a -5% return on a stock with average 0% return gives the same z-score as a -5% return on a stock with average -1% return
- The standard deviation $\sigma(r)$ is computed on signed returns, so volatile stocks with large swings in both directions will have high $\sigma$ and smaller z-scores for the same absolute move
- This is well-understood, symmetric, and directly interpretable as "how far below normal was today's return"

Compared to the v2 formula, which uses $z(|r|)$ with an attached sign: the difference is that the v2 formula calibrates the z-score against the distribution of absolute returns (a half-normal-like distribution), while Option C calibrates against the full signed return distribution. For large negative moves, both will give strongly negative scores, but the z-score scaling will differ.

**Recommendation:**

Option C (standard signed z-score of raw returns) is the cleanest formulation. It is:
1. Unambiguous in sign convention — no possibility of directional inversion
2. Statistically standard — any quant reviewer immediately understands what it means
3. Simpler to implement with no special-case handling for $r_T = 0$ (the denominator is $\sigma(r)$, not $|r_T|$)
4. Directly comparable to the extensive short-term reversal literature, which uses signed returns

If the author has a specific reason to prefer the v2 formula (e.g., separating the magnitude-deviation from the direction), Option B is acceptable but the weight signs must be fixed structurally as $(-|w_1|, +w_2)$.

---

## Section 2: Assessment of v1 Fixes

The following table evaluates each v1 issue against the v2 changes:

| Issue | v1 Problem | v2 Change | Status | Assessment |
|-------|-----------|-----------|--------|------------|
| C1: Directionality | `|r_T|` loses sign; extreme move detector, not oversell detector | Added `sign(r_T)` to $D(r)_T$ | **Partially fixed — new critical issue introduced** | Sign fix is correct but ranking inversion risk created. Without specifying $w_1 < 0$, strategy selects overbought stocks. See Section 1b. |
| C2: Survivorship bias | No point-in-time universe | No change | **Unaddressed** | Entire backtest remains invalid without point-in-time universe. This is the most operationally costly fix (data procurement) and should have been flagged as a prerequisite. |
| C3: No liquidity filter | No minimum volume or market cap threshold | Added "large volume" text filter | **Partially fixed — operationally undefined** | The text acknowledges the need for a filter but provides no numerical threshold. Developers have no implementable specification. See Section 4. |
| C4: MAD-based normalization | Rolling z-score sensitive to outliers | No change | **Unaddressed** | Non-robust statistics remain. Single outlier events inflate $\sigma(|r|)$ and suppress subsequent z-scores during the periods they are most needed. |
| C5: Log-volume transformation | Raw volume is log-normal; z-score dominated by outliers | Corrected redundant `|v_T|` in denominator (now `σ(v_T)`) | **Partially fixed — wrong fix** | Removing the redundant absolute value is cosmetically correct but misses the substance of C5. The log transformation was not applied. Volume z-scores remain dominated by earnings-day spikes with $D(v)$ values of 5–20+. |
| C6: No regime filter | Strategy buys into sustained downtrends | No change | **Unaddressed** | Strategy will systematically deploy capital into 2022-style bear markets and 2020-style crash regimes where the mean-reversion hypothesis fails. |
| C7: 3-stock concentration | ~50-80% idiosyncratic annual volatility | No change | **Unaddressed** | 3-stock portfolio remains. Every Sharpe ratio, drawdown, and return statistic should be interpreted in the context of near-total idiosyncratic exposure. |
| C8: No earnings/catalyst filter | Extreme moves on earnings are fundamental repricing, not mean-reverting | No change | **Unaddressed** | The strategy will systematically buy post-earnings losers, which is the most well-documented permanent repricing scenario. Earnings filter is cheap to implement and material in impact. |

**Summary:** Of 8 v1 issues, 1 was genuinely addressed (redundant `|v_T|` removal), 1 was partially addressed but with a new critical problem introduced (directionality), 1 was partially addressed but inadequately (liquidity filter), and 5 remain entirely unaddressed.

---

## Section 3: Remaining Statistical and Mathematical Issues

### 3a. $D(r)$ is Undefined When $r_T = 0$

The v2 formula contains:

$$\text{sign}(r_T) = \frac{r_T}{|r_T|}$$

When $r_T = 0$, this is $0/0$ — undefined. In a Python implementation using `numpy.sign()`, this returns 0, which would yield $D(r)_T = 0$ regardless of how extreme the stock's history is. In a manual implementation using division, it raises a `ZeroDivisionError` or produces `NaN`.

How often does $r_T = 0$ occur? More often than intuition suggests:

- **Halted stocks**: Stocks under extended trading halts show unchanged prices in the data, producing $r_T = 0$ for each halted session.
- **Illiquid names**: Stocks with thin float may have days with no trades; the data provider may carry forward the last close, producing $r_T = 0$.
- **Index component price resets**: In some data sources, corporate action adjustments can occasionally produce exactly zero daily returns.
- **Frequency**: In a universe of several thousand stocks over 10 years, zero-return days number in the thousands to tens of thousands. They are not rare enough to ignore.

**Required handling**: Define explicitly how $D(r)_T$ should behave when $r_T = 0$. The most defensible convention for an oversell strategy is $D(r)_T = 0$ (a flat day is neutral, neither oversold nor overbought), which `numpy.sign()` conveniently implements but the division-form does not. The implementation must use `numpy.sign()` explicitly, not the division definition, and document this choice.

### 3b. Asymmetric Z-Score Structure

The v2 formula is mathematically interesting but creates an asymmetry that deserves explicit acknowledgment. The formula:

$$D(r)_T = \text{sign}(r_T) \cdot \frac{|r_T| - \overline{|r|}_T}{\sigma(|r|)_T}$$

calibrates the z-score against the distribution of **absolute returns**, then attaches a sign. This means:

- The z-score magnitude $z(|r_T|) = (|r_T| - \overline{|r|})/\sigma(|r|)$ is always non-negative when $|r_T| > \overline{|r|}$ (by construction)
- Attaching $\text{sign}(r_T)$ makes it negative for drops and positive for rises
- A -2% return and a +2% return receive the same magnitude z-score, scaled by $\pm 1$

Compare this to the standard signed z-score (Option C from Section 1c):

$$D(r)_T^{\text{std}} = \frac{r_T - \bar{r}_T}{\sigma(r)_T}$$

The difference is that $\overline{|r|}_T > 0$ always (mean of absolute values is positive), whereas $\bar{r}_T \approx 0$ (mean of signed returns is near zero for most stocks over short windows). This means:

- Under the v2 formula, a zero return ($r_T = 0$) gives $D(r)_T = 0$, but actually $|r_T| = 0 < \overline{|r|}$, so the z-score numerator is negative — this is a below-average absolute move that would yield a negative z-score before the sign is applied. The sign is then zero (or 0 by convention), producing $D(r) = 0$.
- Under the standard formula, $r_T = 0$ gives $D(r) = -\bar{r}/\sigma(r) \approx 0$ (since $\bar{r} \approx 0$).

The behavior near zero is similar in both cases, but the interpretations differ subtly for small moves. The v2 formula says: "a small positive return is equally unremarkable as a small negative return, both receiving near-zero scores." The standard formula says the same thing but through a different path.

**The key question is whether the author wants the z-score to reflect deviation from the mean absolute return (v2) or deviation from the mean signed return (Option C).** These are not the same distribution. The absolute return distribution is right-skewed (a folded normal), while the signed return distribution is approximately symmetric around zero. The v2 approach will give slightly different z-scores for the same absolute move depending on whether the stock's history has been trending, but for most liquid stocks over a 20-60 day window, the practical difference is small.

This is a design choice, not a bug — but it must be documented and the author must consciously choose between the two interpretations.

### 3c. Volume Z-Score: Std(|v_T|) Denominator and Log-Skewness

The v2 volume formula is:

$$D(v)_T = \frac{v_T - \overline{v}_T}{\sigma(|v_T|)_T}$$

Since $|v_T| = v_T$ for all $v_T \geq 0$, this simplifies to the standard volume z-score:

$$D(v)_T = \frac{v_T - \overline{v}_T}{\sigma(v_T)_T}$$

This is algebraically correct but statistically problematic. Daily volume is empirically well-described by a log-normal distribution, not a normal distribution. The consequences:

- On a typical day, $D(v)_T$ is small and roughly symmetrically distributed around zero.
- On an earnings announcement day, volume may be 8-15x average. This produces $D(v)$ values of 7–14 standard deviations.
- A single earnings day with $D(v) = 10$ will contribute $w_2 \cdot 10$ to the OS score, swamping the return signal (whose typical range is $[-3, +3]$ for non-extreme days and $[-10, +10]$ for extreme days).

The earnings-day contamination is the most material consequence: a stock on its earnings day will have an enormous $D(v)$ regardless of whether the price move was oversell-driven. The OS score will be dominated by earnings-day volume spikes, not by panic selling on normal days. This is precisely the scenario where mean reversion is least likely to occur (post-earnings repricing is typically permanent).

The log transformation resolves this:

$$D(v)_T = \frac{\log(v_T) - \overline{\log(v)}_T}{\sigma(\log(v_T))_T}$$

Under log-volume z-scoring, a 10x volume day produces $\log(10x) = \log(10) + \log(x) \approx 2.3 + \log(x)$, and the z-score will be approximately 3-4 standard deviations above normal (since $\log$ of a typical daily variation in volume is roughly 0.5-0.7 sigma). This still flags the day as notable but does not produce a score of 10-15 that overwhelms the return signal.

### 3d. Interaction Between D(r) and D(v) in the Additive Formula

The additive OS score has a specific failure mode that is worth quantifying. Consider three scenarios with $w_1 = -0.5$, $w_2 = 0.5$ (the correct orientation for oversell):

**Scenario 1 — True oversell (target condition):**
Large drop on high volume: $D(r) = -8$, $D(v) = +4$
$$OS = (-0.5)(-8) + (0.5)(4) = 4.0 + 2.0 = +6.0$$
This stock ranks high. Correct.

**Scenario 2 — Volume-dominated false positive:**
Minor drop on extreme volume: $D(r) = -0.5$, $D(v) = +12$ (earnings day)
$$OS = (-0.5)(-0.5) + (0.5)(12) = 0.25 + 6.0 = +6.25$$
This stock ranks higher than a genuine oversell candidate. The signal is driven entirely by volume, not by the price dislocation hypothesis. This is the earnings-day contamination problem.

**Scenario 3 — Large drop on thin volume:**
Large drop on below-average volume: $D(r) = -6$, $D(v) = -1.5$ (thin-market drop)
$$OS = (-0.5)(-6) + (0.5)(-1.5) = 3.0 - 0.75 = +2.25$$
The low volume reduces the OS score, correctly identifying this as a less reliable signal (low-volume moves are more likely to reverse intraday and less likely to represent forced selling). The additive form handles this correctly.

The problematic case is Scenario 2. A multiplicative formulation:

$$OS_{T-1} = D(r)_{T-1} \cdot D(v)_{T-1}$$

would handle Scenario 2 differently. For a minor drop on extreme volume: $D(r) = -0.5$, $D(v) = +12$ gives $OS = -0.5 \times 12 = -6.0$, which with a "bottom 3" selection rule correctly de-prioritizes this stock (because the price move is small). However, the multiplicative form has its own pathologies: if $D(r) < 0$ and $D(v) < 0$ (large drop on thin volume), the product is positive, ranking the stock as "oversold" — which contradicts the hypothesis that high volume is required.

The cleanest approach is a **conditioned additive**: require $D(v) > $ threshold as a binary filter, then rank purely by $D(r)$. This separates the "volume confirmation" role from the "rank determination" role and avoids the additive interaction problem entirely.

---

## Section 4: "Large Volume" Filter — Specification Required

The v2 strategy states "only trade stocks with large volume" without defining what "large volume" means. This is operationally useless — a developer cannot implement it, a reviewer cannot evaluate it, and a trader cannot apply it consistently.

The v2 change introduces false confidence: the liquidity concern is nominally acknowledged but the specification is no more actionable than having no filter at all. Consider the specific ambiguity: does "large volume" refer to:

(a) The raw volume $v_T$ on the signal day (a stock that happened to trade a lot yesterday)?
(b) The volume deviation $D(v)_{T-1}$ (a stock with above-normal volume for itself)?
(c) The average daily dollar volume (ADDV) over a trailing window (a measure of the stock's liquidity tier)?

These are fundamentally different filters with different effects on the strategy.

**Proposed concrete definitions and their implications:**

**Option A — ADDV threshold applied to universe construction (pre-filter):**
Require ADDV > $X million over the trailing 20 days, applied to define the tradeable universe. This is the standard institutional approach.

- Example thresholds: ADDV > $5M (liquid small-caps), ADDV > $50M (mid-caps and above)
- Effect: Removes illiquid names from the universe entirely. The OS score is then computed and ranked only within the liquid universe.
- Advantage: Clean separation of "who is eligible" from "who is ranked highest." The liquidity filter and the signal are independent.
- Recommended threshold: $5M ADDV for a $500K fund (where each position is ~$167K, representing ~3.3% of ADV — manageable market impact). At $10M AUM, raise to $30–50M ADDV minimum.

**Option B — $D(v)_{T-1} > 0$ filter (above-average volume day):**
Require that yesterday's volume was above the stock's rolling average before the stock is eligible to trade.

- Effect: Only stocks with above-average volume on signal day are considered. This partially implements the "volume confirmation" idea.
- Weakness: This is a weaker version of the $D(v)$ term already in the OS score. If $D(v) > 0$ is required as a binary filter AND the OS score includes $w_2 \cdot D(v)$, the filter is partially redundant.

**Option C — $D(v)_{T-1} > 1.0$ filter (notably above-average volume):**
Require at least 1 standard deviation above-average volume to be eligible.

- Effect: More selective than Option B. Focuses the strategy on days with genuinely abnormal volume.
- Advantage: Filters out the "large drop on thin volume" case entirely.
- Risk: During the first part of the ADDV-based trading day, this filter may exclude too many stocks in low-volatility periods.

**Option D — Cross-sectional volume rank:**
Require the stock to be in the top quintile of volume across all stocks on signal day.

- Effect: Time-varying; in high-volume market days, the threshold rises; in quiet days, it falls.
- Weakness: In broad market selloffs (the scenario most relevant to the strategy), many stocks have above-normal volume simultaneously. This filter would admit a large number of candidates.

**Recommended specification:**

Apply two filters in sequence:
1. **Universe filter**: ADDV (20-day) > $5M and price > $5 and market cap > $300M. This defines the eligible universe on any given day using only data available before the signal day.
2. **Signal filter**: $D(v)_{T-1} > 0$ (yesterday's volume above the stock's own 20-day average). This is a binary confirmation that the OS score's volume component is meaningful.

Note that the volume threshold problem is partially self-solving: the $D(v)$ term in the OS score already gives higher scores to stocks with above-normal volume. If $w_2 > 0$ (correct orientation), the top-ranked stocks will naturally tend to have high volume. The ADDV filter is the more important of the two, as it governs the universe rather than the ranking.

---

## Section 5: Unchanged Issues That Still Apply

### 5.1 Survivorship Bias — Critical, Unaddressed

The strategy description contains no reference to point-in-time universe construction. The v2 update made no changes to the universe specification beyond the undefined "large volume" filter.

For a mean-reversion strategy that specifically targets large recent losers, survivorship bias is particularly severe:

- The stocks that score highest on an oversell signal in any historical period are disproportionately represented among names that subsequently went bankrupt, were delisted, or became distressed for fundamental reasons.
- A point-in-time universe from CRSP, Sharadar, or Compustat will include these failures; a current-ticker universe from yfinance or similar will not.
- The expected inflation in win rate from survivorship bias for a strategy of this type is in the range of 5-15 percentage points on win rate and 20-50% upward bias on CAGR, based on comparable studies in the academic literature.

This issue was flagged as Critical in v1. It remains unaddressed in v2. No backtest conducted without a point-in-time universe should be trusted or presented.

### 5.2 No Regime Filter — Major, Unaddressed

The strategy buys stocks experiencing large drops on large volume without any market-context filter. During sustained bear markets and crash regimes, this systematically buys into confirmed downtrends:

- **October–December 2018**: SPY declined ~20%. The strategy would have been fully deployed long throughout the decline.
- **February–March 2020**: SPY declined ~34% in 23 trading days. The strategy would have generated maximum OS scores (large drops on extreme volume) precisely as the market accelerated lower.
- **2022 bear market**: SPY declined ~25% over the full year. The strategy would have repeatedly bought recent losers that continued to lose.

In each of these periods, the "forced selling creates mean-reversion" hypothesis was overwhelmed by macro fundamental repricing. The strategy has no mechanism to distinguish a panic-sell dislocation (recovers in 1-5 days) from the beginning of a sustained downtrend.

A VIX-based filter is a standard and well-tested approach: when VIX > 30 (or when SPY is below its 200-day moving average), reduce position size to 50% or halt new entries. This filter will reduce the number of trades and modestly reduce gross returns in calm periods, but will substantially improve the drawdown profile and risk-adjusted returns by avoiding the worst regime-mismatch losses.

### 5.3 3-Stock Concentration — Major, Unaddressed

Holding exactly 3 positions at $500K AUM means each position is approximately $167K. The analytical implications:

- **Idiosyncratic volatility**: A random 3-stock portfolio of U.S. equities has annualized volatility approximately 3x higher than the market — roughly 45-60% annualized vs. 15-20% for SPY. For stocks selected by an extreme-move criterion, the individual names will have higher-than-average volatility (they were selected because of anomalous recent moves), meaning portfolio volatility may be 60-80% annualized.
- **Sharpe ratio context**: A 60% annualized volatility portfolio generating 20% CAGR has an annualized Sharpe of approximately 0.33. The same 20% CAGR with a 20% vol portfolio has a Sharpe of 1.0. The concentration penalty to Sharpe is enormous.
- **Drawdown risk**: With 3 positions and 60% portfolio vol, drawdowns of 30-50% from peak are mathematically expected under normal log-normal return assumptions, with no model error at all. Deep drawdowns are a feature, not a bug, of this portfolio structure.

This is not necessarily fatal if the strategy is sized appropriately and the fund manager has the risk tolerance for it. But presenting results from this strategy without emphasizing the concentration context is misleading. A strategy with Sharpe 0.6 and max drawdown 40% at 3-stock concentration may actually be producing excellent signal alpha that a more diversified version (10-15 positions) would express with Sharpe 1.2 and max drawdown 20%.

**The 3-stock constraint is the single most limiting design decision in the strategy.** The v1 review recommended expanding to 5-10 stocks. This recommendation was not addressed in v2.

### 5.4 No Earnings/Catalyst Filter — Major, Unaddressed

The academic literature on short-term reversal is clear: the mechanism works on non-information-driven price moves (forced selling, liquidity provision, market maker inventory imbalance). It does not work — and in fact is reliably wrong — on moves driven by genuine fundamental information.

The primary source of genuine fundamental information events is earnings announcements. A stock that drops -12% after reporting a 40% earnings miss has been fundamentally repriced, not temporarily oversold. The strategy will flag this stock as a high OS scorer and initiate a long position that faces ongoing fundamental headwinds.

Implementation of an earnings filter is straightforward:
- Maintain a calendar of scheduled earnings announcement dates (available from Compustat, Bloomberg, or free sources like Earnings Whispers)
- Exclude any stock from the candidate pool if it announced earnings within the prior 2 trading days
- Optionally, exclude stocks scheduled to announce in the next 2 trading days (avoids entering a position before a catalyst that could produce a fundamental repricing)

Estimated impact: approximately 20-30% of the largest single-day drops in U.S. equities occur on or immediately after earnings announcement days. Removing these cases substantially reduces the false positive rate and improves the average trade quality.

### 5.5 Log-Volume Normalization — Major, Not Fixed in v2

As detailed in Section 3c, the removal of the redundant `|v_T|` in the v2 formula is a cosmetic correction that does not address the substance of C5 from v1. The log transformation was explicitly recommended in v1 and was not implemented.

The practical consequence: earnings-day volume spikes will produce $D(v)$ values of 8-15+ on raw volume z-scores. Under log-volume, those same events produce z-scores of 3-5. The difference between $D(v) = 12$ and $D(v) = 4$ is enormous when these numbers are weighted in the OS score — the raw volume z-score can produce a scenario where volume dominates the signal for the entire lookback window that includes the spike.

---

## Section 6: New Issues Introduced in v2

### 6.1 Directionality Inversion Risk (New — Critical)

As analyzed in Section 1b, the v2 fix creates a new critical risk that did not exist in v1. In v1, the strategy was an "extreme move detector" — wrong, but at least symmetric and therefore less systematically biased in one direction. In v2, the strategy is either:

(a) Correctly directional with $w_1 < 0$ (intended behavior)
(b) Systematically buying overbought stocks with $w_1 > 0$ (directional inversion)

The v2 specification is ambiguous on which case applies. If a developer implements the strategy with positive weights (the natural default), they will build an overbought momentum strategy that loses money systematically on the mean-reversion thesis. This failure mode is worse than the v1 symmetric case, because the losses will be directionally consistent (not noise) and may be harder to diagnose without explicitly examining the sign of $w_1$.

**This is the most dangerous issue in v2 because the fix appears correct at a surface reading but contains a critical hidden trap.**

### 6.2 Division by Zero When $r_T = 0$ (New — Moderate)

The v2 formula introduces $\text{sign}(r_T) = r_T / |r_T|$ as an explicit operation. In v1, the formula used $|r_T|$ directly and had no sign operation. The new sign operation is undefined at $r_T = 0$. This is a new implementation trap introduced by the v2 fix that did not exist in v1 (since v1 used `|r_T|`, which is perfectly defined at zero).

### 6.3 False Confidence from Undefined Liquidity Filter (New — Minor)

The v2 specification acknowledges the liquidity issue by adding the text "only trade stocks with large volume." This is an improvement over v1 (which had no acknowledgment at all), but it may actually be worse than silence from an implementation standpoint.

A developer reading the v2 specification sees a liquidity filter and assumes the concern is addressed. They may implement an arbitrary threshold (e.g., "volume > 1 million shares" without dollar-volume adjustment) that does not achieve the intended purpose. The undefined text creates a false checkpoint — the issue is visible but the resolution is deferred to an unspecified time, risking that it is never properly defined.

In v1, the absence of any liquidity filter was clear and would be caught in code review. In v2, the presence of an undefined filter may pass code review as "addressed."

---

## Section 7: Recommendations

### MUST FIX (Critical Correctness Issues)

**MF1 — Lock the weight sign convention for $w_1$.**
The strategy description must explicitly state that $w_1 < 0$ when using top-3 selection, or alternatively restructure the formula as $OS = -|w_1| D(r) + w_2 D(v)$ to make the sign structural. This is not an optimization decision — it is a fundamental correctness requirement. Implementing this with positive weights produces an overbought momentum strategy, not an oversell mean-reversion strategy.

**MF2 — Handle $r_T = 0$ explicitly.**
Add a convention: when $r_T = 0$, set $D(r)_T = 0$. Use `numpy.sign()` (which returns 0 for input 0) rather than the division form $r_T / |r_T|$. Document this convention explicitly in the code.

**MF3 — Secure a point-in-time universe (from v1, critical, still unaddressed).**
No backtest should be run with a survivorship-biased universe. Procure Sharadar, CRSP, or Polygon.io data that includes delisted tickers and historical constituent lists before writing any backtesting code.

### SHOULD FIX (Major Issues Affecting Strategy Validity)

**SF1 — Apply log-volume transformation before z-scoring.**
Replace $\sigma(v_T)$ with $\sigma(\log(v_T))$ and normalize log-volume. This prevents earnings-day volume spikes from dominating the OS score.

**SF2 — Define the liquidity filter numerically.**
Replace "large volume" with a concrete, implementable specification: minimum ADDV (20-day trailing average daily dollar volume) > $5 million AND price > $5 AND market cap > $300 million. Apply as a pre-filter before computing OS scores.

**SF3 — Add an earnings calendar filter.**
Exclude stocks that announced earnings within the prior 2 trading days from the candidate pool. This removes the single largest source of permanent repricing events from the signal.

**SF4 — Add a regime filter.**
Deactivate or halve position size when: VIX > 30 OR SPY is below its 200-day moving average. This prevents systematic deployment into sustained downtrend regimes where the mean-reversion hypothesis fails.

**SF5 — Expand from 3 stocks to 5-10 stocks.**
The concentration risk at 3 positions dominates all other considerations. A 5-stock portfolio reduces idiosyncratic volatility by ~35%; a 10-stock portfolio by ~50%. Use equal weight initially, then test signal-proportional sizing after confirming alpha.

### NICE TO FIX (Robustness Improvements)

**NF1 — Consider replacing the v2 formula with a plain signed z-score of raw returns (Option C from Section 1c).**
The standard z-score of signed returns is simpler, unambiguous, and directly comparable to the academic literature on short-term reversal. The v2 formula's asymmetric construction (z-score of absolute values plus sign) offers no clear advantage and adds the $r_T = 0$ edge case.

**NF2 — Test multiplicative interaction term.**
Test $OS = D(r) \cdot D(v)$ (after adjusting signs) as a complement or alternative to the additive formula. The multiplicative form better captures the joint condition of "large drop AND high volume" and prevents volume-only false positives.

**NF3 — Apply robust normalization (rolling median and MAD).**
Replace rolling mean and standard deviation in both $D(r)$ and $D(v)$ with rolling median and MAD (median absolute deviation, scaled by 1.4826 to be comparable to standard deviation under normality). This reduces the influence of historical outliers on current-day scores.

**NF4 — Run signal decay analysis before full backtesting.**
Before optimizing any hyperparameter, compute the average holding-day return curve (holding period 1-20 days) for the base signal. This reveals the empirical signal half-life and provides an economically grounded basis for setting $K$ rather than treating it as a free parameter to optimize.

---

## Summary Comparison Table: v1 Issues vs. v2 Status

| Issue ID | Description | Severity (v1) | v2 Change | v2 Status |
|----------|-------------|---------------|-----------|-----------|
| C1 | Directionality: `|r_T|` loses sign | Critical | Added `sign(r_T)` | **Partially fixed — ranking inversion risk introduced (see Section 1b)** |
| C2 | Survivorship bias — no point-in-time universe | Critical | None | **Unaddressed** |
| C3 | No liquidity filter | Major | Added undefined "large volume" text | **Partially addressed — operationally undefined** |
| C4 | Non-robust statistics (rolling mean/std) | Minor | None | **Unaddressed** |
| C5 | Log-volume transformation missing | Minor | Removed redundant `|v_T|` (cosmetic only) | **Wrong fix — substance unaddressed** |
| C6 | No regime filter | Major | None | **Unaddressed** |
| C7 | 3-stock concentration | Major | None | **Unaddressed** |
| C8 | No earnings/catalyst filter | Major | None | **Unaddressed** |
| — | Ranking inversion ($w_1$ sign unspecified) | — (new in v2) | Introduced by v2 sign fix | **New Critical Issue** |
| — | Division by zero when $r_T = 0$ | — (new in v2) | Introduced by v2 sign fix | **New Moderate Issue** |
| — | Undefined liquidity filter creates false confidence | — (new in v2) | Introduced by v2 text filter | **New Minor Issue** |

**Score: 1 properly fixed, 1 cosmetically fixed but substantively wrong, 1 partially addressed with new issues introduced, 5 unaddressed, 3 new issues introduced.**

The v2 update touched the right problem (directionality) but resolved it incompletely. The weight sign specification is the single most important correction needed before any implementation work proceeds. Without it, the strategy direction is undefined and any backtest results are uninterpretable.

---

*This document reflects a second-round pre-implementation peer review based on the v2 strategy specification. Review conducted against prior review `review_signal_quality.md` (v1). All critical issues must be resolved before backtest implementation begins.*

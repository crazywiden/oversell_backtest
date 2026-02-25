# Third-Round Critical Review: Oversell Score Strategy v3 — Signal Quality, Exit Logic & Methodology

**Date:** 2026-02-24
**Reviewer:** Senior Quant Researcher
**Review Round:** v3 (Third Pass)
**Prior Reviews:** `review_signal_quality.md` (v1), `review_v2_signal_quality.md` (v2), `review_v2_execution_methodology.md` (v2)
**Status:** Pre-Implementation Peer Review — Not for Distribution

---

## Executive Summary

Version 3 delivers one meaningful structural improvement and one meaningful partial improvement, while introducing two new issues and leaving the two most dangerous pre-existing flaws entirely untouched.

The genuine improvement is the 4-step exit hierarchy. Replacing the flat `[Low, High]` bracket check with explicit gap-open handling directly addresses the most material execution bias from prior rounds. This fix is architecturally correct and was the highest-priority actionable recommendation from v2. The partial improvement is the formal naming of the volume filter as $V$ — it is now a named hyperparameter, which is marginally better than undefined text, but it remains operationally unquantified and theoretically underspecified.

The new issues are significant. First, the 50% fill probability in Step 3 introduces stochasticity into the backtest, making results non-deterministic and statistically uncomparable across runs. This is a methodology flaw that undermines the entire backtest's evidentiary value. Second, the volume filter is applied inconsistently across the spec — once using $v_T$ (today's volume, not yet observable at signal time) and once using $v_{T-1}$ — introducing a potential look-ahead bias that was not present in prior versions.

The two most dangerous pre-existing critical flaws — the $w_1$ sign ambiguity and survivorship bias — are completely unaddressed for the third consecutive round. The $w_1$ sign ambiguity means the strategy's directional orientation remains undefined: a developer implementing with both weights positive will build a momentum strategy while believing they are building a mean-reversion strategy. Survivorship bias means every backtest result produced so far is optimistically biased by an estimated 200–500 basis points annually.

The bottom line: v3 is incrementally better on execution logic and materially worse on backtest reproducibility. The strategy still cannot be validly implemented or trusted as a backtest until C1 ($w_1$ sign) and C2 (survivorship bias) are resolved.

---

## Section 1: Delta Analysis — What v3 Changed and Whether It Is Correct

### 1a. Exit Logic Overhaul — Step-by-Step Assessment

The 4-step exit hierarchy directly implements the gap-check recommendation from the v2 execution review. The structure is assessed below.

**Step 1 — Gap-down stop check:**

$$\text{If } \text{Open}_t < p(1 - \text{stop\_loss\_rate}): \text{ fill at } \text{Open}_t$$

This is correct. The open price is the first observable price of day $t$ and is available before any intraday bracket check. Filling at $\text{Open}_t$ (worse than the stop level) is realistic — it properly models gap-through slippage. This fix eliminates the single largest source of execution-level optimism from v1 and v2.

One edge case is unaddressed: what if $\text{Open}_t = p(1 - \text{stop\_loss\_rate})$ exactly? The condition uses strict less-than (`<`). The boundary case (open exactly at stop level) falls through to Step 3, where the stop level is within the day's range by definition (Low $\leq$ Open = stop level $\leq$ High). This is a degenerate case that almost never occurs with real data but should be specified for completeness. Recommend: use less-than-or-equal (`≤`) for both gap checks, so the boundary case is handled at the open.

**Step 2 — Gap-up take-profit check:**

$$\text{If } \text{Open}_t > p(1 + \text{win\_take\_rate}): \text{ fill at } \text{Open}_t$$

This is correct and economically sound for a long position. A gap-up above the take-profit level is profitable — the position exits at a price better than the target. Filling at $\text{Open}_t$ (which is above the take-profit) is the correct realistic assumption.

A design question worth raising: is a gap-up take-profit exit actually desirable for an oversell mean-reversion strategy? The thesis is that a stock has been temporarily oversold and will recover. If it gaps up past the take-profit level overnight, the recovery has occurred — an early exit is entirely consistent with the thesis. The only question is whether a gap-up signals that more upside is available. Empirically, for short-term reversal strategies, overnight gap-ups on stocks that reversed from oversold conditions do not reliably continue higher the next day. Exiting at the open is therefore defensible. No change required here, but the reviewer flags it as an empirical question worth checking in the trade log once data is available.

**Step 3 — Normal intraday bracket check (50% fill probability):**

This step is discussed at length in Section 3, as it is the most consequential new issue in v3. The ordering rule (SL priority when both levels are in range) is assessed here.

The SL-priority rule when both TP and SL fall within $[\text{Low}_t, \text{High}_t]$ is the conservative choice for backtesting. The prior v2 review criticized the TP-priority rule as systematically optimistic. The v3 fix directly addresses that criticism.

However, there is a substantive objection to SL-priority that goes beyond conservatism. For a mean-reversion strategy entering an oversold stock, the realistic intraday path on a recovery day is: stock opens near prior close (slightly lower), falls briefly toward stop level, then reverses and rallies through take-profit. In this scenario, the TP was hit last — meaning SL priority produces an incorrect outcome (models a stop-loss when the stock actually recovered through take-profit). SL priority is pessimistic in the scenario most favorable to the mean-reversion thesis.

Neither SL-first nor TP-first is universally correct. The honest answer is that OHLC data does not carry sufficient information to determine intraday order. This ambiguity should be acknowledged explicitly in the backtest methodology documentation and treated as a sensitivity test: run the backtest under both rules and report the range of outcomes.

**Step 4 — Max-hold exit at Close:**

$$\text{If held for } K \text{ days: sell at } \text{Close}_t$$

This is correct in principle. One ambiguity remains: when does the $K$-day count begin?

The spec says "buy at close price of day $T$." The earliest sell is "day after purchase." If $K = 5$ and the count starts from day $T$ (the buy day), then the forced exit fires at the close of day $T+5$, meaning the stock has been held through 5 tradeable days after purchase. If the count starts from day $T+1$ (the first tradeable day), the forced exit fires at the close of day $T+5$ as well — the same result. However, if $K$ is computed inclusive of the buy day, the forced exit fires at the close of day $T+4$, one day earlier.

This must be made unambiguous with a concrete example in the spec. Recommend: define $K$ as the number of trading days the position is held after the buy close, so that a position bought at close of day $T$ and held for $K = 5$ is force-exited at the close of day $T+5$. The holding period in the trade log should be $t_{\text{sell}} - t_{\text{buy}}$ in calendar trading days, where $t_{\text{buy}}$ is the day the position was opened (day $T$) and $t_{\text{sell}}$ is the day the exit fires.

### 1b. Volume Filter: $v_T > V$ vs. $v_{T-1} > V$ — Look-Ahead Bias Risk

The v3 spec contains two distinct statements about the volume filter:

**Universe definition**: "U.S. equities where daily volume $v_T > V$"

**Signal usage**: "Select top 3 stocks by $OS_{T-1}$ from stocks with $v_{T-1} > V$"

These are different. The universe definition uses $v_T$ (today's volume); the signal selection step uses $v_{T-1}$ (yesterday's volume). This inconsistency must be resolved.

The correct filter uses $v_{T-1}$ (or a rolling average ending at $T-1$). Today's volume $v_T$ is not known when the OS score is computed and the selection is made. Using $v_T$ in the universe definition or selection step is a look-ahead bias — we are conditioning on information not available at the time the decision is made.

Specifically, if a stock has $v_{T-1} < V$ (ineligible yesterday) but $v_T > V$ (becomes eligible today), a strategy using $v_T$ as the filter would include it in today's selection. In live trading, this is unknowable until the market closes. This is a subtle but real bias — stocks that happen to have high volume on the entry day are more likely to be in a high-activity state, which could systematically shift entry conditions relative to a pure $v_{T-1}$ filter.

Beyond the look-ahead issue, the filter as stated operates on single-day volume, which is noisy. A stock can have one day of abnormally high or low volume due to block trades, index rebalancing, or data errors. The recommended formulation uses a rolling average daily dollar volume (ADDV):

$$\text{ADDV}_{T-1} = \frac{1}{N} \sum_{i=1}^{N} v_{T-i} \cdot \text{Close}_{T-i}$$

where the filter applies to the $N$-day trailing ADDV, computed entirely from data available before day $T$. A dollar-volume threshold (e.g., ADDV > \$50M) is more meaningful than a share-count threshold because share volume is not comparable across stocks with different prices: a stock trading at \$5 requires 10 million shares to equal \$50M in dollar volume, while a stock at \$500 requires only 100,000 shares. Share-count thresholds are unstable across price changes and over time as stock prices drift.

Formally recommend: replace the current $V$ filter with:

$$\text{ADDV}_{T-1}(N) = \frac{1}{N} \sum_{i=1}^{N} v_{T-i} \cdot \text{Close}_{T-i} > V_{\$}$$

where $V_{\$}$ is expressed in dollars and computed using only data through day $T-1$. This resolves both the look-ahead bias and the share-count instability in a single specification change.

### 1c. Hold Duration in Trade Log

The v3 addition of holding days to the trade log is a practical improvement. The correct computation is:

$$\text{hold\_days} = t_{\text{sell}} - t_{\text{buy}}$$

where both dates are in trading days (not calendar days), $t_{\text{buy}}$ is day $T$ (the day the close-price entry occurs), and $t_{\text{sell}}$ is the day the exit fires (via any of Steps 1–4). A position that buys on Monday and stops out Tuesday morning (Step 1 gap check) has hold\_days = 1. A position that holds to the max-hold exit of $K = 5$ has hold\_days = 5. This is correct by construction under the recommended $K$ definition in Section 1a.

---

## Section 2: Critical Unresolved Issue — $w_1$ Sign Ambiguity (Third Round)

### 2a. Full Sign Table

This issue has been flagged in every prior round and remains unresolved. The mathematics are repeated here in their most complete form for the final record.

Under the v3 formula, $D(r)_{T-1}$ is the signed z-score of the absolute return, with sign inherited from the direction of the return. For a large negative return, $D(r) \ll 0$; for a large positive return, $D(r) \gg 0$. The OS score is:

$$OS_{T-1} = w_1 \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}$$

Using the numerical example from the v2 review (rolling mean of absolute returns $\overline{|r|} = 1.0\%$, rolling standard deviation $\sigma(|r|) = 0.8\%$, rolling mean of volume $\bar{v}$, rolling standard deviation $\sigma(v)$):

| Stock Type | $r_{T-1}$ | $D(r)_{T-1}$ | $D(v)_{T-1}$ | $OS$ ($w_1 > 0, w_2 > 0$) | Selected by top-3? |
|-----------|-----------|-------------|-------------|---------------------|-------------------|
| Oversold (large drop, high vol) | $-8\%$ | $-8.75$ | $+4.0$ | $0.5 \cdot (-8.75) + 0.5 \cdot (4.0) = -2.375$ | **No — excluded** |
| Overbought (large rally, high vol) | $+8\%$ | $+8.75$ | $+4.0$ | $0.5 \cdot (8.75) + 0.5 \cdot (4.0) = +6.375$ | **Yes — selected (WRONG)** |
| Normal decline, low vol | $-1\%$ | $0.0$ | $-0.5$ | $0.5 \cdot (0.0) + 0.5 \cdot (-0.5) = -0.25$ | No |
| Normal rise, low vol | $+1\%$ | $0.0$ | $-0.5$ | $-0.25$ | No |

With $w_1 > 0, w_2 > 0$ and a descending top-3 selection, the strategy systematically selects overbought stocks with large positive returns. The oversell thesis is inverted. The strategy as naturally implemented would be a momentum-long strategy, not a mean-reversion strategy.

The only weight configuration that correctly implements the oversell thesis under a top-3 descending selection is $w_1 < 0, w_2 > 0$:

$$OS = (-0.5) \cdot (-8.75) + (0.5) \cdot (4.0) = 4.375 + 2.0 = +6.375 \quad \text{(oversold stock ranks first)}$$

### 2b. Three Correct Formulations

The spec can be corrected in any of three equivalent ways:

**Option A — Negate $w_1$ structurally (recommended):**

$$OS_{T-1} = -|w_1| \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}$$

Select top 3 by $OS$. The negative sign on the return component is structural and visible in the formula. No ambiguity about what "large positive OS" means — it always indicates large negative return deviation (oversold) plus large positive volume deviation. A developer cannot accidentally flip the sign.

**Option B — Select bottom 3 with positive weights:**

$$OS_{T-1} = w_1 \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}, \quad w_1 > 0, w_2 > 0$$

Select the 3 stocks with the **most negative** $OS$ score. Mathematically equivalent to Option A, but relies on the selection direction being implemented correctly. Riskier from an implementation standpoint because it is easy to accidentally use a descending sort.

**Option C — Rename and clarify:**

Define $\text{OSS}$ (oversell score) as a quantity that is large and positive when a stock is genuinely oversold:

$$\text{OSS}_{T-1} = -D(r)_{T-1} + D(v)_{T-1}$$

Select top 3 by $\text{OSS}$. The negation of $D(r)$ is in the formula name, not hidden in a weight sign convention. Oversold stocks ($D(r) \ll 0$, $D(v) \gg 0$) produce the largest $\text{OSS}$ values.

Options A and C are preferred. They make the economic logic visible in the formula itself. Option B is acceptable but more error-prone.

### 2c. Impact of Getting This Wrong

If the strategy is implemented with $w_1 > 0$ and top-3 descending selection, the actual strategy being backtested is a short-term momentum strategy: it buys stocks that just had large positive returns on large volume. This is a completely different economic mechanism — a continuation-of-positive-momentum hypothesis, not a mean-reversion hypothesis. The resulting backtest would test the momentum hypothesis, not the oversell hypothesis.

If the momentum strategy happens to be profitable in the in-sample period, its results would be attributed to the mean-reversion mechanism, which is a factually incorrect attribution. If the backtested results are presented to investors as evidence that the oversell strategy works, this constitutes a material misrepresentation of the investment hypothesis. If the actual live trading strategy is then implemented correctly (with oversell selection), its live performance will be completely uncorrelated with the backtest results — not because of overfitting, but because they are testing different things.

This issue must be resolved before any implementation work proceeds. It requires a single unambiguous statement in the strategy specification and a corresponding unit test in the implementation.

---

## Section 3: New Issue — 50% Fill Probability Creates a Non-Deterministic Backtest

### 3a. What "50% Fill Probability" Means in Practice

Step 3 of the exit logic states: when both the TP and SL level are in $[\text{Low}_t, \text{High}_t]$ and Step 3 applies (no gap open), a fill occurs with 50% probability. Operationally, this means a random number $u \sim \text{Uniform}(0, 1)$ is drawn per trade per day, and the order fills if $u < 0.5$.

The theoretical motivation is correct: the Parlour (1998) result that limit orders at the inside quote fill approximately 50% of the time the price touches the limit level is a legitimate academic finding. The problem is that applying stochastic fills to a backtesting context creates a non-deterministic simulation. Two runs of the same backtest on the same dataset will produce different results — different P&L, different Sharpe ratios, different max drawdowns.

This violates the most basic requirement of a reproducible backtest. Consider the consequences:

1. A parameter set that looks attractive in one run may look unattractive in the next run due to lucky or unlucky random fills. Parameter selection becomes unreliable.

2. Comparing strategy v3 against strategy v3-with-a-tweak requires averaging over many runs to separate signal from random fill noise, adding significant computational overhead and analytic complexity.

3. Reporting the strategy's Sharpe ratio, max drawdown, or win rate from a single run has quantified uncertainty that is unknown (it depends on the random seed and the number of trades affected by the 50% rule).

4. Walk-forward validation is corrupted: a walk-forward result showing an OOS Sharpe of 0.8 might actually have a true OOS Sharpe of anywhere from 0.5 to 1.1 depending on fill randomness. The validation is not testing the strategy — it is testing the strategy mixed with random noise.

### 3b. Alternatives and Recommendation

| Option | Assumption | Deterministic? | Pros | Cons |
|--------|-----------|---------------|------|------|
| 100% fill at target | Price reaches target level → fill at that exact level | Yes | Simple, deterministic, consistent with most backtesting frameworks | Slightly optimistic (real limit orders fill at touch ~50% of the time) |
| 50% fill (random) | Microstructure theory | No | Theoretically motivated | Non-deterministic; two runs differ; unreliable for parameter selection |
| Fixed random seed + 50% | Microstructure theory with reproducibility | Yes (conditionally) | Deterministic given same seed; somewhat theoretically motivated | Seed choice is arbitrary; different seeds give different results; still unreliable across parameter grids |
| Conservative: SL priority, no TP intraday | When both levels are in range, assume worst outcome (stop fires) | Yes | Fully deterministic, maximally conservative | Understates TP capture on genuine recovery days |
| Fill at midpoint of target and next close | Price touches level → fill at mid(target, next\_close) | Yes | Deterministic, conservative, captures partial fill realism | Requires defining "next price" (next tick approximated as close); computationally minor addition |

**Recommendation:** Replace the 50% random fill with 100% fill at the target level and document this as a slightly optimistic assumption that is standard in academic backtesting. Alternatively, if the 50% rule is retained for theoretical correctness, set a fixed random seed at the top of every backtest run, document the seed in every results file, and run a sensitivity analysis over 20 different seeds to characterize the distribution of outcomes. The seed must be reported alongside every metric. Neither approach is perfect; the deterministic 100% fill is strongly preferred for practical strategy development.

### 3c. Ordering Ambiguity When Both TP and SL Are In-Range

As noted in Section 1a, the SL-priority rule in Step 3 is the conservative choice but is not universally correct. For completeness, the sensitivity test is straightforward to implement: run the backtest with SL-priority and TP-priority, and report both. The difference quantifies the backtest's sensitivity to the intraday path assumption. If the Sharpe ratio changes by more than 0.2 or the total return changes by more than 10%, the strategy is materially sensitive to this assumption and the results should be presented as a range.

---

## Section 4: Remaining Unresolved Major Issues

### 4a. Capital Recycling — Re-Entry Logic Still Undefined

When a position exits on day $t$ via any of the four exit steps, the spec says capital can be reinvested at close of day $t$. Three ambiguities remain entirely unaddressed in v3:

**Self-replacement.** If the stock that just stopped out on day $t$ still ranks in the top-3 by $OS_{T-1}$ (computed using data through day $t-1$), the spec does not prohibit re-entering it. Buying back the same stock that just triggered a stop-loss is economically incoherent. The stop-loss was triggered because the stock moved adversely — the mean-reversion hypothesis was at minimum interrupted. Re-entry on the same day at a price close to the stop level provides essentially no margin before the stop fires again. This case must be explicitly prohibited in the spec with a rule such as: "If the exiting stock would otherwise qualify for selection, it is excluded from same-day capital deployment."

**Replacement stock selection.** When one of three positions exits on day $t$, the replacement stock is selected from the day-$t$ top-3 ranking (using $t-1$ data), excluding stocks already held and the exiting stock. This logic is the only coherent interpretation, but it is not stated explicitly in v3. It should be.

**Partial portfolio state.** If fewer than 3 qualifying stocks exist after exclusions (held stocks + exiting stock excluded), the recycled capital remains in cash until the next day. The spec does not address how the portfolio behaves during these cash-holding periods. The backtest must model this correctly — a portfolio temporarily holding 2 positions and cash should not have the cash earning any return (or should earn the risk-free rate if the simulation includes financing).

### 4b. Survivorship Bias — Still Unaddressed, Third Round

No change from v1 or v2. This remains the single most dangerous methodological flaw in the strategy. For a mean-reversion strategy targeting large recent losers, survivorship bias operates through the most direct mechanism possible: the stocks most likely to score highest on the OS signal in any historical period are disproportionately represented among names that subsequently went bankrupt, became distressed, or were delisted. A backtest using a current-ticker universe will never encounter these permanent losses.

Estimated bias magnitude for a strategy of this type: 200–500 basis points of annualized performance inflation, based on studies of comparable strategies in the academic literature (see Shumway, 1997; Kothari et al., 1995). Over a 10-year backtest, a 3% annual survivorship bias compounds to a 34% cumulative overstatement of total return. This is not a rounding error.

The fix requires procuring point-in-time universe data from a source that includes delisted stocks: Sharadar via Nasdaq Data Link, CRSP via WRDS, or Polygon.io institutional tier. Any backtest conducted without this data source is producing fiction, not evidence.

### 4c. No Regime Filter — Still Unaddressed

Unaddressed across all three versions. During bear market regimes (2018 Q4, COVID March 2020, 2022), the strategy's signal — large drop on large volume — fires most frequently and selects the worst possible trades: stocks entering sustained downtrends, not temporary dislocations. The mean-reversion mechanism fails systematically in these regimes because the "forced selling" is not forced by temporary liquidity constraints but by genuine fundamental repricing.

A VIX > 30 or SPY < 200-day moving average filter is the minimum viable regime check. When either condition is true, new entries are paused. This reduces trade count modestly in calm markets and prevents the drawdown cascades that OHLC data from the 2020 and 2022 periods show would have been severe for this strategy type.

---

## Section 5: Volume Filter $V$ as a Seventh Hyperparameter

The formalization of $V$ as a named hyperparameter in v3 brings the total hyperparameter count to 7: $\{N, w_1, w_2, \text{win\_take\_rate}, \text{stop\_loss\_rate}, K, V\}$.

The multiple testing problem, first raised in the v2 execution review, is now materially worse. Adding even 3 candidate values of $V$ to the parameter grid:

$$N \in \{10, 20, 40\} \times (w_1, w_2) \in \{3\text{ configs}\} \times \text{TP} \in \{2\%, 3\%, 5\%\} \times \text{SL} \in \{1\%, 2\%, 3\%\} \times K \in \{3, 5, 7\} \times V \in \{3 \text{ values}\}$$

yields $3^6 = 729$ configurations at minimum. At a 5% significance threshold, approximately 36 of these will appear statistically significant purely by chance, with no underlying edge.

The correct approach is to fix $V$ via market convention rather than treating it as a free optimization parameter. A defensible and standard institutional choice is ADDV > \$50M for a fund targeting mid-cap liquidity, or ADDV > \$10M for broader small-cap coverage. Fixing this value before running any backtest eliminates one degree of freedom from the search space and is supported by the economic rationale that the threshold should reflect the fund's actual market impact constraint, not an in-sample optimization target.

---

## Section 6: Issue Tracker — v1 Through v3

### Full Issue History Table

| Issue | Severity | v1 | v2 | v3 | Notes |
|-------|----------|----|----|----|----|
| $D(r)$ uses $\|r\|$ — no direction | Critical | Open | **Fixed** (added sign) | Fixed | Full fix in v2 |
| $w_1$ sign unspecified → strategy inversion | Critical | N/A | Open | **Still open** | Not addressed in any version; three rounds outstanding |
| Survivorship bias | Critical | Open | Open | **Still open** | Three rounds outstanding; most dangerous unfixed flaw |
| Gap-through fills at stop/TP level | Critical | Open | Open | **Fixed** | 4-step hierarchy correctly addresses this |
| Ordering ambiguity (TP vs. SL priority) | Major | Open | Open | **Fixed (SL priority)** | Conservative but see Section 1a caveat |
| Intraday fill probability unrealistic | Major | Open | Open | **Introduced 50% rule** | New stochasticity issue — see Section 3 |
| Liquidity filter undefined | Major | Open | Partial | **V named, still unquantified** | Named but not operationally defined |
| Look-ahead bias in volume filter ($v_T$ vs. $v_{T-1}$) | Major | N/A | N/A | **Newly introduced** | Universe uses $v_T$; selection uses $v_{T-1}$; inconsistent |
| Capital recycling re-entry logic undefined | Major | Open | Open | **Still open** | Self-replacement, partial portfolio, replacement selection all unspecified |
| No regime filter | Major | Open | Open | **Still open** | Three rounds outstanding |
| Log-volume transformation missing | Minor | Open | Open | **Still open** | Raw volume z-scores susceptible to earnings-day domination |
| Non-robust statistics (mean/std) | Minor | Open | Open | **Still open** | |
| No earnings/catalyst filter | Major | Open | Open | **Still open** | |
| 3-stock concentration | Major | Open | Open | **Still open** | |
| K-day hold count start not specified | Minor | N/A | N/A | **Newly introduced** | From buy day $T$ or first tradeable day $T+1$? |

### New Issues Introduced in v3

| New Issue | Severity | Description |
|-----------|----------|-------------|
| Non-deterministic backtest (50% fill probability) | Major | Stochastic fills make results non-reproducible; two runs on identical data produce different P&L |
| Look-ahead bias in volume filter specification | Major | Universe definition uses $v_T$ (not yet observable at signal time); selection uses $v_{T-1}$; inconsistent |
| $K$-day hold count ambiguity | Minor | Start of $K$ count (day $T$ vs. day $T+1$) unspecified; affects when forced exit fires |
| Gap-check boundary case ($\text{Open}_t$ exactly at stop level) | Minor | Strict `<` in Step 1 means boundary case falls to Step 3; recommend `≤` |

### Score Summary by Version

| Metric | v1 | v2 | v3 |
|--------|----|----|-----|
| Critical issues open | 3 | 3 | 2 |
| Major issues open | 7 | 8 | 8 |
| Minor issues open | 3 | 3 | 4 |
| New issues introduced | — | 3 | 4 |
| Issues properly fixed | — | 2 | 2 |

---

## Section 7: Summary and Priority Recommendations

### Must Fix Before Any Backtest Is Run

**MF1 — Resolve $w_1$ sign ambiguity (three rounds outstanding).**

Choose one of the three correct formulations in Section 2b and write it explicitly into the spec. Recommended: $OS_{T-1} = -|w_1| \cdot D(r)_{T-1} + w_2 \cdot D(v)_{T-1}$, select top 3 by $OS$. Add a unit test that verifies: given a stock with $r = -8\%$ and above-average volume, it ranks in the top 3.

**MF2 — Secure point-in-time universe data (three rounds outstanding).**

No backtest should be run until a survivorship-bias-free data source is confirmed. Acceptable sources: Sharadar, CRSP, Polygon.io institutional tier. yfinance and any source returning only currently-listed tickers is not acceptable for this strategy type.

**MF3 — Fix volume filter look-ahead bias.**

Change the universe definition from $v_T > V$ to $\text{ADDV}_{T-1}(N) > V_{\$}$, where ADDV is computed entirely from data through day $T-1$ and expressed in dollar volume terms. Ensure the same filter condition is used consistently across both the universe definition and the signal selection step.

**MF4 — Eliminate stochastic fill probability.**

Replace the 50% random fill in Step 3 with 100% fill at the target level (deterministic and standard in academic backtesting), or if the 50% rule is retained, fix the random seed, document it in every results file, and run a 20-seed sensitivity analysis to characterize outcome variance.

### Should Fix Before Implementation Decisions Are Made

**SF1 — Define $V$ numerically and remove it from the optimization grid.**

Set ADDV threshold to a single value justified by fund size and market impact constraints (e.g., ADDV > \$50M for $500K–$2M AUM). Document the rationale. Do not treat $V$ as a free hyperparameter.

**SF2 — Specify K-day count convention explicitly.**

Add a concrete example: "A position bought at close of day $T$ with $K = 5$ is force-exited at close of day $T+5$. Hold days = 5."

**SF3 — Add SL-priority sensitivity test to the backtest report.**

Run under both TP-priority and SL-priority when both levels are in-range. Report the performance range. If the range is wide, the intraday path assumption is a material source of uncertainty.

**SF4 — Specify capital recycling logic unambiguously.**

Add three explicit rules: (1) the exiting stock is excluded from same-day re-entry, (2) replacement is selected from day-$t$ top-3 ranking excluding held stocks and the exiting stock, (3) if no qualifying replacement exists, capital remains in cash until the next day's ranking.

### Enhancements for Robustness (After Critical and Major Issues Are Resolved)

- Apply log-volume transformation before z-scoring $D(v)$
- Add VIX-based regime filter (halt new entries when VIX > 30)
- Add earnings calendar filter (exclude stocks in $\pm$2 day window around earnings)
- Expand from 3 to 5–10 positions to reduce idiosyncratic volatility
- Implement walk-forward validation with OOS period starting 2020-01-01

---

*This document reflects a third-round pre-implementation peer review. It supersedes prior reviews where conclusions differ and should be read in conjunction with `review_signal_quality.md` (v1), `review_v2_signal_quality.md` (v2), and `review_v2_execution_methodology.md` (v2). The strategy cannot be validly backtested until MF1 through MF4 are resolved.*

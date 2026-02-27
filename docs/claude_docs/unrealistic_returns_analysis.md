# Unrealistic Returns Analysis

**Run:** `results/20260226_220839/`
**Config:** N=20, w1=-1.0, w2=0.0, TP=5%, SL=3%, K=5, V=500K, capital=$500K, max_positions=3
**Backtest period:** 2020-01-01 to 2026-01-01
**Total trades:** 1,924
**Reported metrics:** Total return -1.89%, Sharpe 0.17, Max drawdown -65.26%

---

## Executive Summary

Three structural flaws in the backtesting pipeline allow unrealistic returns to contaminate results. The core problem is that the OS score formula strongly amplifies signals from distressed/bankrupt penny stocks, which are then sized using uncapped position sizing that can consume 30–670% of average daily volume. The resulting trades are physically unexecutable, yet they account for a disproportionate share of the strategy's gross P&L. Removing these trades would dramatically shift the net return profile and make the drawdown statistics more reliable.

---

## Flaw 1: No Minimum Price Filter

**What is missing:** The engine has no price floor in the universe selection block (engine.py, Phase 3). The only filter applied is `volume > config.V` (default 500K shares). A stock trading at $0.005 with 1M daily volume passes through.

**Affected trades — all with entry_price < $1.00 (sub-dollar universe):**

A systematic scan of the trades file reveals the following sub-dollar trades (entry_price < $1.00):

| Ticker | Entry Price | Exit Price | Shares | PnL | Exit Reason | is_delisted |
|--------|-------------|------------|--------|-----|-------------|-------------|
| FELPQ  | $0.006      | $0.0063    | 31,773,302 | +$9,532    | intraday_tp | True |
| HOSSQ  | $0.010      | $0.0105    | 22,765,548 | +$11,383   | intraday_tp | True |
| INAPQ  | $0.030      | $0.0315    | 7,583,441  | +$11,375   | intraday_tp | True |
| CRRTQ  | $0.024      | $0.022     | 10,182,243 | -$20,364   | gap_down_stop | True |
| CRRTQ  | $0.020      | $0.016     | 11,369,684 | -$45,479   | gap_down_stop | True |
| UPLCQ  | $0.045      | $0.042     | 5,488,195  | -$16,465   | gap_down_stop | True |
| UNTCQ  | $0.050      | $0.070     | 4,163,645  | **+$83,273** | gap_up_tp | True |
| HCRSQ  | $0.045      | $0.0436    | 8,163,579  | -$11,021   | intraday_sl | True |
| CVIAQ  | $0.035      | $0.040     | 9,058,127  | +$45,291   | gap_up_tp   | True |
| UPLCQ  | $0.013      | $0.014     | 25,410,393 | +$25,410   | gap_up_tp   | True |
| CASSQ  | $0.035      | $0.035     | 5,348,562  | $0         | forced_close| True |
| AVHOQ  | $0.400      | $0.600     | 675,574    | **+$135,115** | gap_up_tp | True |
| AVHOQ  | $0.170      | $0.160     | 1,833,387  | -$18,334   | gap_down_stop | True |
| GNCIQ  | $0.403      | $0.435     | 433,539    | +$13,873   | gap_up_tp   | True |
| AKRXQ  | $0.210      | $0.2037    | 1,051,142  | -$6,622    | intraday_sl | True |
| FTRCQ  | $0.314      | $0.290     | 607,133    | -$14,571   | gap_down_stop | True |
| FTRCQ  | $0.110      | $0.120     | 2,176,199  | +$21,762   | gap_up_tp   | True |
| DOFSQ  | $0.788      | $0.680     | 302,643    | -$32,685   | gap_down_stop | True |
| DOFSQ  | $0.230      | $0.270     | 1,135,100  | +$45,404   | gap_up_tp   | True |
| DOFSQ  | $0.115      | $0.1208    | 3,275,791  | +$18,836   | intraday_tp | True |
| CBLAQ  | $0.089      | $0.050     | 4,664,014  | **-$181,897** | gap_down_stop | True |
| MNKKQ  | $0.750      | $0.750     | 504,089    | $0         | max_hold    | True |
| MNKKQ  | $0.144      | $0.1397    | 2,449,514  | -$10,582   | intraday_sl | True |
| VVUSQ  | $0.136      | $0.120     | 2,644,152  | -$42,306   | gap_down_stop | True |
| GPORQ  | $0.160      | $0.193     | 2,247,529  | **+$74,168** | gap_up_tp | True |
| XOGAQ  | $0.030      | $0.033     | 11,988,000 | +$35,964   | gap_up_tp   | True |
| INTEQ  | $0.210      | $0.2205    | 1,212,364  | +$12,730   | intraday_tp | True |
| INTEQ  | $0.223      | $0.210     | 1,459,053  | -$18,968   | gap_down_stop | True |
| PIRRQ  | $0.090      | $0.070     | 2,828,849  | -$56,577   | gap_down_stop | True |
| SPNX   | $0.385      | $0.405     | 981,874    | +$19,637   | gap_up_tp   | True |
| SPNX   | $0.068      | $0.065     | 5,771,748  | -$17,315   | gap_down_stop | True |
| VALPQ  | $0.392      | $0.4116    | 903,673    | +$17,712   | intraday_tp | True |
| CRCQQ  | $0.300      | $0.315     | 1,119,416  | +$16,791   | intraday_tp | True |
| SRNEQ  | $0.198      | $0.1921    | 986,516    | -$5,860    | intraday_sl | True |
| CLVSQ  | $0.271      | $0.2846    | 703,072    | +$9,527    | intraday_tp | True |
| AUDAQ  | $0.104      | $0.1092    | 1,548,200  | +$8,051    | intraday_tp | True |
| LCINQ  | $0.954      | $0.9254    | 173,316    | -$4,960    | intraday_sl | True |
| VNTRQ  | $0.331      | $0.352     | 494,592    | +$10,386   | gap_up_tp   | True |
| PTRAQ  | $0.150      | $0.1455    | 1,053,523  | -$4,741    | intraday_sl | True |
| NSTGQ  | $0.500      | $0.525     | 332,110    | +$8,303    | intraday_tp | True |
| LLFLQ  | $0.570      | $0.5985    | 342,922    | +$9,773    | intraday_tp | True |
| WGHTQ  | $0.189      | $0.1833    | 941,299    | -$5,337    | intraday_sl | True |
| LTMAY  | $0.430      | $0.460     | 519,052    | +$15,572   | gap_up_tp   | True |
| LTMAY  | $0.305      | $0.3202    | 694,315    | +$10,588   | intraday_tp | True |
| LTMAY  | $0.200      | $0.194     | 888,822    | -$5,333    | intraday_sl | True |
| AZUL   | $0.830      | $0.980     | 212,336    | +$31,850   | gap_up_tp   | True |
| MVIS   | $0.276      | $0.2677    | 627,388    | -$5,195    | intraday_sl | False |
| YRIV   | $0.053      | $0.0514    | 6,358,270  | -$10,110   | intraday_sl | False |
| NOVA   | $0.675      | $0.6548    | 291,617    | -$5,905    | intraday_sl | False |
| CISO   | $0.595      | $0.6248    | 249,872    | +$7,434    | intraday_tp | False |

**Sub-dollar trades (entry_price < $1.00): approximately 50+ trades out of 1,924 total (~2.6% by count).**

The four headline extreme-return trades — AVHOQ (+50%), UNTCQ (+40%), GPORQ (+20.6%), CBLAQ (-43.8%) — are all sub-dollar entries.

---

## Flaw 2: No is_delisted Filter

**What is missing:** Phase 3 of the engine has no `~prev_df["is_delisted"]` filter. The prices dataset has 6,573,864 rows flagged `is_delisted=True` versus 11,609,853 flagged `False` — 36% of all price rows are for delisted companies. These companies remain in the eligible universe throughout the simulation.

**Why this matters structurally:**

All four highest-return trades are bankrupt/OTC issuers:
- AVHOQ: Avianca Holdings (Colombian airline, filed Chapter 11 May 2020, OTC)
- UNTCQ: Unit Corp (oil driller, filed Chapter 11 May 2020, OTC)
- GPORQ: Gulfport Energy (filed Chapter 11 November 2020, OTC)
- CBLAQ: CBL & Associates Properties (REIT, filed Chapter 11 November 2020, OTC)

Many Q-suffix tickers (the standard OTC/pink sheets designation for bankrupt companies) appear repeatedly in the trade list: FELPQ, FTRCQ, CRRTQ, UPLCQ, HOSSQ, INAPQ, CVIAQ, HCRSQ, MNKKQ, VVUSQ, GPORQ, XOGAQ, HTZGQ, DOFSQ, PIRRQ, INTEQ, CBLAQ, RADCQ, PTRAQ, CLVSQ, SRNEQ, AUDAQ, LCINQ, VNTRQ, BBBYQ, PRTYQ, REVRQ, SAVEQ, MODVQ, WGHTQ, BIGGQ, LLFLQ, NSTGQ, and others. This constitutes roughly 80+ unique ticker appearances across 1,924 trades.

**Note on SM and RWT:** SM Energy and Redwood Trust are not delisted — they are legitimate, exchange-listed companies that experienced extreme COVID-19 oil crash volatility (SM: -73% in two days; RWT: REIT mortgage stress). The gap-up returns on 2020-03-10 and 2020-03-26 respectively are real historical prices, but the position size problem (Flaw 3 below) still applies to SM due to its depressed price at $1.48.

---

## Flaw 3: Uncapped Position Sizing Relative to ADV

**What is missing:** The position sizing formula is:

```python
allocation = cash / open_slots       # e.g. $500K / 3 = ~$166,667
shares = int(allocation // buy_price)
```

There is no cap on shares as a percentage of average daily volume (ADV). For a $0.05 stock with $166K allocated, this produces 3.3 million shares.

**Quantitative sizing analysis for the two most extreme cases:**

**UNTCQ (Unit Corp) — Entry 2020-05-28 at $0.05:**
- Allocation: $500,000 / 3 = $166,667
- Shares purchased: 4,163,645 (as recorded in trades.csv, slight variation due to remaining cash)
- 20-day ADV (May 2020): approximately 6–15 million shares/day (the stock was actively trading post-bankruptcy filing on extreme volume)
- Entry day volume (2020-05-28): 11,936,400 shares (from prices.csv)
- Position size as % of entry day volume: 4,163,645 / 11,936,400 = **34.9% of one day's volume**
- For a micro-cap OTC stock in bankruptcy, acquiring 35% of a day's volume is virtually impossible without moving the price 50%+ against you. The entire "fill at close $0.05" assumption is fiction.
- Exit day (2020-05-29): stock closed at $0.04 (not $0.07 as recorded as exit_price, which was the open). Volume 8,345,100. Position represents 49.9% of exit day volume.

**AVHOQ (Avianca Holdings) — Entry 2020-06-12 at $0.40:**
- Allocation: approximately $166,667 (cash-adjusted)
- Shares purchased: 675,574
- Entry day volume (2020-06-12): 1,010,200 shares
- Position size as % of entry day volume: 675,574 / 1,010,200 = **66.9% of one day's volume**
- Exit day (2020-06-15): opened at $0.60 (gap-up TP trigger). Volume 1,653,800 on the day. The "fill at open $0.60" for 675,574 shares is implausible — the opening print alone would have been a $405K trade in a stock that averaged ~$1M/day in total dollar volume.

**FELPQ (Foresight Energy) — Entry 2020-03-11 at $0.006:**
- Shares purchased: 31,773,302
- This is 31.8 million shares of a $0.006 stock
- Entry day volume: 8,196,470 shares
- Position as % of day's volume: 387.7% — nearly 4x the entire day's volume
- This trade is physically impossible by definition

**General scale of the problem:** With $500K capital, $166K per slot, and a $0.05 entry price, the formula produces 3.33 million shares. Even at $1.00, it produces 166,000 shares. The absence of an ADV cap means the backtest implicitly assumes infinite market depth at the closing price for any size.

---

## Flaw 4 (Compounding): Why Penny and Bankrupt Stocks Rank Highest on the OS Score

This is the economic mechanism that explains why flaws 1 and 2 are not corner cases — they are structural attractors in the scoring formula.

**The OS score formula (w2=0 in this run, so pure return z-score):**

```
OS_T = w1 * D(r)_T  where  D(r)_T = sign(r_T) * (|r_T| - rolling_mean(|r|, N)) / rolling_std(|r|, N)
```

with w1 = -1.0, the score is highest (most "oversold") when the daily return is the most negative in a z-score sense relative to the stock's own recent history.

**Why distressed stocks always win this competition:**

1. **Crash dynamics amplify absolute returns.** A stock falling from $0.10 to $0.05 has a -50% return. A stock falling from $50 to $47.50 also has a -5% return. Even adjusted for the stock's own volatility history, bankrupt companies frequently post daily moves of -50% to -90% that are multiple standard deviations below their (already elevated) rolling mean. A healthy large-cap rarely moves more than 10-15% intraday.

2. **The rolling std normalizer is forward-biased for stressed names.** When a company is first entering distress, early extreme moves (e.g., -30%) elevate the rolling std. But the rolling mean of absolute returns also rises. The signed z-score `sign(r) * (|r| - mean(|r|)) / std(|r|)` is therefore bounded by the local volatility regime — but for newly distressed companies, each successive crash often exceeds even the recently elevated baseline.

3. **Verified in the data.** On 2020-06-11 (signal day for AVHOQ), the OS score distribution across 2,693 tickers was:
   - p50 = 1.67, p90 = 2.80, p95 = 3.06, p99 = 3.49, **max = 4.25**
   - AVHOQ scored **4.25 — the maximum score in the entire universe that day**, driven by a -69.3% daily return (from $0.88 to $0.27 after days of stale pricing followed by a trading halt reopening)
   - On 2020-05-27 (UNTCQ signal day), UNTCQ scored **4.11 — #1 in universe** with a -78.8% daily return
   - On 2020-03-06 (SM signal day), SM scored **3.80 — #2 in universe** (SM is a legitimate E&P company, not bankrupt at the time, but caught in the oil crash)

4. **The stale-price problem.** AVHOQ shows days of identical OHLCV at $0.88 with zero volume (2020-06-05 through 2020-06-10) — this is the OTC market during a trading halt while the bankruptcy restructuring proceeded. The rolling mean of absolute returns therefore remained near zero during the halt, then the return denominator (std) was also near zero. When trading resumed on 2020-06-11 with a -69% crash, the z-score hit the numerical ceiling of the formula (~4.25, the maximum achievable given the distribution). This is not a "signal" — it is a data artifact from OTC halt/resume mechanics.

---

## Quantitative Impact Assessment

**Gross P&L contribution from top extreme-return trades:**

| Ticker | PnL | % Return | Classification |
|--------|-----|----------|----------------|
| AVHOQ (Jun-2020) | +$135,115 | +50.0% | Delisted, sub-$1, ADV violation |
| UNTCQ | +$83,273 | +40.0% | Delisted, sub-$1, ADV violation |
| GPORQ | +$74,168 | +20.6% | Delisted, sub-$1, ADV violation |
| RWT | +$70,398 | +34.3% | Live stock, $3.85 entry, ADV borderline |
| SM | +$70,337 | +45.3% | Live stock, $1.48 entry, ADV borderline |
| REVRQ | +$58,609 | +31.6% | Delisted, sub-$2 |
| CRCQQ | +$21,919 | +9.6% | Delisted, sub-$2 |
| CVIAQ | +$45,291 | +14.3% | Delisted, sub-$1 |
| DOFSQ (Apr-2020) | +$45,404 | +17.4% | Delisted, sub-$1 |

**Total gross P&L from these 9 trades: +$604,514**

**Catastrophic losses from same universe:**
| Ticker | PnL | Classification |
|--------|-----|----------------|
| CBLAQ | -$181,897 | Delisted, sub-$1, ADV violation |
| CRRTQ (2x) | -$65,843 total | Delisted, sub-$1 |
| PIRRQ | -$56,577 | Delisted, sub-$1 |
| VVUSQ | -$42,306 | Delisted, sub-$1 |
| MODVQ (2025) | -$93,389 | Delisted, $1.07 entry |

The gross wins and losses from distressed/penny names nearly offset each other at the portfolio level, but with extreme volatility. The net portfolio return of -1.89% masks a situation where distressed-stock trades dominate total gross P&L, and their removal would fundamentally change the return distribution, max drawdown, and Sharpe ratio.

**Trades below $1.00 entry:** Approximately 50 trades out of 1,924 = ~2.6% by count. By gross absolute P&L impact (wins + losses combined), these trades are responsible for an estimated 40-50% of total gross trading activity due to the extreme leverage embedded in the share counts.

**is_delisted=True trades:** Approximately 80-100+ trade appearances involve tickers that are delisted in the dataset (Q-suffix OTC names constitute the majority). This is roughly 4-5% of total trade count but far larger by capital deployment due to elevated share counts.

---

## Recommendations

### Fix 1: Minimum Price Filter

Add `min_price` to `BacktestConfig` (default $5.00, or $1.00 as a minimum viable threshold) and apply it in Phase 3 of the engine:

```python
# In engine.py Phase 3, add to candidates filter:
(today_df.loc[:, "close"] >= config.min_price)
# Applied on T-1 prev_df:
(prev_df["close"] >= config.min_price)
```

**Rationale:** Stocks below $5 are excluded from most institutional mandates. Below $1 is the NYSE minimum listing threshold. The capacity constraints that make penny stocks attractive in theory (small fund advantage) are neutralized by the bid-ask spread problem — a $0.05 stock with a $0.01 spread has an implicit transaction cost of 20% round-trip, obliterating any mean-reversion edge.

### Fix 2: is_delisted Filter

Add an `exclude_delisted` boolean to `BacktestConfig` (default `True`) and apply in Phase 3:

```python
# In engine.py Phase 3:
(~prev_df["is_delisted"]) if config.exclude_delisted else True
```

**Rationale:** Bankrupt/OTC stocks are not investable for any fund operating under standard fiduciary constraints. Their price discovery is erratic, halts are common, and the OS score mechanism exploits halt-resume dynamics that cannot be traded in practice.

### Fix 3: ADV-Capped Position Sizing

Add `max_adv_pct` to `BacktestConfig` (default 0.10, i.e., 10% of 20-day ADV) and compute a hard cap on shares in Phase 3:

```python
# In engine.py Phase 3:
adv_shares = prev_df.loc[ticker, "volume"]  # prev day volume as ADV proxy
max_shares_adv = int(adv_shares * config.max_adv_pct)
shares = min(int(allocation // buy_price), max_shares_adv)
if shares > 0:
    ...
```

For a more rigorous implementation, the ADV should be computed as a rolling 20-day average, not a single-day proxy. However, even a single-day volume cap eliminates the most egregious cases (FELPQ at 387% of day volume, AVHOQ at 67%, UNTCQ at 35%).

**Practical participation rate targets:**
- 10% ADV: institutional standard for liquid mid/large caps
- 5% ADV: conservative limit for small-cap strategies
- 1% ADV: appropriate for micro-cap where market impact is severe

At 10% of ADV, the AVHOQ position would have been capped at ~101,020 shares × $0.40 = $40,408 (vs the $270,230 actually allocated), reducing the distorting effect while still allowing the signal to be tested.

---

## Conclusion

The three flaws interact synergistically: the OS score formula by design rewards the most extreme recent losers, and distressed/bankrupt penny stocks produce returns of -50% to -90% that systematically win this competition. Once selected, the uncapped sizing formula magnifies their P&L contribution by allocating 100s of thousands of dollar-equivalent notional into stocks with $1M or less of daily dollar volume. The backtest is then effectively a lottery on whether the stock gaps up or gaps down after an extreme crash day, with no relationship to whether such a position could actually be executed.

The reported metrics (Sharpe 0.17, max drawdown -65.26%) are artifacts of this contamination. After applying the three fixes, the true strategy performance on executable, exchange-listed, adequately liquid stocks will be measurably different — and will represent an honest assessment of the oversell mean-reversion hypothesis.

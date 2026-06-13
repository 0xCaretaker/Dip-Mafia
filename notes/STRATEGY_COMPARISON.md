# Strategy comparison - watchlist & Bollinger experiments

Timed HODL strategy, period 2010-01-04 → 2026-04-17 (16.3y), ₹24.7L invested.
"OLD list" = 62-symbol `stocks.txt` (commit `88bb51a`); "NEW list" = current 75-symbol `stocks.txt`.

> **ADOPTED (current default):** the **V4 idle-cash fallback** - see "Cash-deployment
> fallback" near the end. It is now the default in `simulate_timed_hodl` and is
> reflected in `backtest_output/`, the dashboard, and the README. The bb-variant /
> horizon tables below were computed with the *prior* held-only/42-day fallback (held
> constant across those comparisons, so their relative conclusions still hold); the
> dashboard's Horizon Returns now use V4.

| Run | Final (Timed) | XIRR | Sharpe | Max DD | Stocks | Signals / Bought |
|---|---|---|---|---|---|---|
| OLD list / bb-30 (archived baseline) | ₹207.1L | 27.6% | 1.27 | −55.5% | 61 | 152 / 46 |
| OLD list / bb-60 (isolate) | ₹241.8L | 29.3% | 1.29 | −62.6% | 62 | - |
| NEW list / bb-30 | ₹190.5L | 26.6% | 1.27 | −53.2% | 73 | 156 / 56 |
| NEW list / bb-60 (**current / live**) | ₹182.6L | 26.2% | 1.27 | −52.4% | 73 | 165 / 58 |
| NEW list / bb-60 + close<midline gate | ₹182.2L | 26.1% | 1.27 | −54.2% | 73 | 162 / 55 |

## Findings

- **Stock list is the dominant driver.** Holding bb-60 constant, the new 75-symbol list
  returns ₹182.6L vs ₹241.8L for the old list (−24%), with a shallower drawdown
  (−52.4% vs −62.6%). The added large/mid-cap financials (BAJFINANCE, CHOLAFIN,
  HDFCBANK, MCX…) are lower-return, lower-risk than the small-caps they joined.
- **Bollinger lookback effect is list-dependent.** On the OLD list, widening 30→60
  helped a lot (+₹34.7L). On the NEW list it slightly *hurt* (bb-30 ₹190.5L >
  bb-60 ₹182.6L). The current live config is bb-60.
- **The "close below BB midline" buy gate does not help.** Adding it to the
  signal-buy condition (NEW list / bb-60) gives ₹182.2L vs ₹182.6L - essentially
  identical, marginally worse on return and drawdown. Reason: when BB fires Buy
  (price touched the lower band) the close is almost always already below the
  midline, so the extra filter rarely changes the trade and only delays a few
  Watch-state entries. Flag retained as `BUY_REQUIRE_BELOW_MID` in `backtest.py`
  (default False).

## Horizon returns - old vs new watchlist

Timed HODL, bb-60, **flat ₹20k/month**, trailing windows ending 2026-04-17.
Signals are computed over full history (so the 200-bar Bollinger warmup is always
satisfied); only the investing/measurement window is the trailing horizon - that's
why a 1y horizon is valid even though it's shorter than the 200-day warmup.
Source: full-history price cache (`backtest_output/six7/_price_cache.pkl`).

"+mid" = bb-60 with the extra "close below BB midline" buy gate.

Best per row in **bold** (renders bold-red in the dashboard Iterations tab).

**XIRR (%)**

| Horizon | OLD bb-60 | OLD bb-30 | OLD bb-60+mid | NEW bb-60 | NEW bb-30 | NEW bb-60+mid |
|---|---|---|---|---|---|---|
| 1y   | 15.0 | 7.9  | 14.0 | 4.9  | 9.5  | **16.1** |
| 3y   | **10.1** | 9.8  | 8.5  | 7.6  | 6.9  | 9.6  |
| 5y   | 29.7 | **30.3** | 28.5 | 29.2 | 27.7 | 28.0 |
| Full | **27.5** | 26.5 | 27.3 | 25.0 | 25.3 | 24.9 |

**Wealth multiple (final ÷ invested)**

| Horizon | OLD bb-60 | OLD bb-30 | OLD bb-60+mid | NEW bb-60 | NEW bb-30 | NEW bb-60+mid |
|---|---|---|---|---|---|---|
| 1y   | 1.08x | 1.04x | 1.07x | 1.03x | 1.05x | **1.09x** |
| 3y   | **1.17x** | 1.16x | 1.14x | 1.12x | 1.11x | 1.16x |
| 5y   | 2.08x | **2.12x** | 2.02x | 2.06x | 1.99x | 2.00x |
| Full | **13.1x** | 11.9x | 12.8x | 10.3x | 10.6x | 10.2x |

**Max drawdown (%)** (shallowest = best)

| Horizon | OLD bb-60 | OLD bb-30 | OLD bb-60+mid | NEW bb-60 | NEW bb-30 | NEW bb-60+mid |
|---|---|---|---|---|---|---|
| 1y   | −10.6 | −10.2 | −10.3 | −10.0 | −10.3 | **−9.8**  |
| 3y   | −16.2 | −16.2 | −16.2 | −15.1 | **−13.9** | −14.3 |
| 5y   | −29.7 | **−26.5** | −30.2 | −32.6 | −31.8 | −31.6 |
| Full | −67.7 | −63.4 | −66.7 | **−59.4** | −60.7 | −60.9 |

(Full here uses flat ₹20k/mo, so its XIRR ≈ but not identical to the salary-model
headline run; the deeper Full MaxDD comes from flat contributions giving more
early-period exposure.)

**Reading:**
- **OLD list still leads NEW at most horizons** on the plain bb settings, biggest
  at 1y, nearly tied by 5y.
- **The Bollinger lookback effect is list-dependent and small beyond ~3y.** bb-60
  beats bb-30 at 1y on the OLD list (15.0 vs 7.9); on the NEW list it flips
  (bb-30 9.5 vs bb-60 4.9). From 3y out the gaps are within noise.
- **The midline gate is the standout in the recent year on the NEW list:**
  NEW bb-60+mid is the best 1y cell (16.1% vs 4.9% for plain NEW bb-60) - requiring
  close < midline avoided buying the recently-added names while they were still
  extended. But the edge **fades with horizon** and is neutral over Full (24.9 vs
  25.0). Over the full period it remains a wash, matching the salary-model run
  (₹182.2L vs ₹182.6L) - a recent-window improver, not a long-run one.

## Cash-deployment fallback (V4, adopted)

The headline cash-sitting problem (a **214-trading-day** idle stretch where no held
stock was below its midline) was attacked by widening the idle-cash fallback.
Current list, full period, salary model, bb-60, no buy-gate:

| Fallback variant | Final | XIRR | Sharpe | MaxDD | Cash drag | Longest idle | Fallback buys |
|---|---|---|---|---|---|---|---|
| Baseline: held, thr 42 (old default) | ₹184.3L | 26.2% | 1.27 | −53.6% | 5.7% | 214d | 41 |
| V1: watchlist, thr 42 | ₹172.8L | 25.5% | 1.28 | −49.6% | 5.4% | 201d | 57 |
| V2: watchlist, thr 21 | ₹184.3L | 26.2% | 1.29 | −52.0% | 5.3% | 201d | 209 |
| V3: watchlist+force, thr 42 | ₹178.0L | 25.8% | 1.31 | −47.3% | 1.9% | 42d | 229 |
| **V4: watchlist+force, thr 21 (ADOPTED)** | **₹190.4L** | **26.6%** | **1.31** | −51.1% | **1.2%** | **21d** | 590 |

(prototype figures, 71-stock cache universe; the committed full run on 73 stocks gives
Timed HODL ₹188.1L, Sharpe 1.32, MaxDD −49.4%, cash drag 1.2%, longest idle 21d.)

**Findings:**
- Widening the universe alone (V1/V2) barely dents the idle streak (214→201d) - in
  bull markets almost everything is above its 200-SMA, so "below midline" candidates
  are scarce regardless of universe. V1 also *hurt* returns (spread into laggards).
- The **force last-resort** (V3/V4) is what actually kills the idle streak - it caps
  idle at the threshold and crushes cash drag to ~1–2%.
- **V4** (force + 21-day threshold) wins outright: solves cash sitting (idle 214→21d,
  drag 5.7%→1.2%) **and** improves returns (₹184→190L), Sharpe (1.27→1.31), and
  drawdown. Deploying sooner and never letting cash rot lands better average entries
  than waiting 42 days for a dip that, in bull runs, never arrives.
- Tradeoff: force sometimes buys *above* midline when no dip exists - a mild
  departure from strict "buy dips," but still long-only within the curated watchlist.

`simulate_timed_hodl` defaults are now `fallback_universe="watchlist"`,
`fallback_force=True`, `idle_threshold=21`. Restore the old behavior with
`("held", False, 42)`.

## Horizon returns by strategy (Timed HODL / SIP / NIFTY 50)

Gated backtest config (bb-60 + midline gate + V4 fallback), flat ₹20k/mo, trailing
windows to 2026-04-17. Best per metric row in **bold**. Also rendered in the
dashboard Backtest tab (best per row in red). Full uses flat contributions, so its
XIRR ≈ the salary-model headline (Timed 26.4% / SIP 27.0% / NIFTY 10.9%).

**1 year**

| Metric | Timed HODL | SIP | NIFTY 50 |
|---|---|---|---|
| XIRR | **16.1%** | 0.7% | −3.8% |
| Sharpe | 2.48 | 2.47 | **2.49** |
| Max DD | **−9.8%** | −10.8% | −10.2% |
| Cash drag | 3.3% | - | - |

**3 years**

| Metric | Timed HODL | SIP | NIFTY 50 |
|---|---|---|---|
| XIRR | 10.7% | **24.4%** | 4.9% |
| Sharpe | 1.88 | **2.05** | 1.91 |
| Max DD | −16.8% | −22.3% | **−11.7%** |
| Cash drag | 5.9% | - | - |

**5 years**

| Metric | Timed HODL | SIP | NIFTY 50 |
|---|---|---|---|
| XIRR | 37.0% | **38.5%** | 7.9% |
| Sharpe | 1.94 | **1.95** | 1.65 |
| Max DD | −26.9% | −26.3% | **−12.9%** |
| Cash drag | 2.0% | - | - |

**Full (~16y)**

| Metric | Timed HODL | SIP | NIFTY 50 |
|---|---|---|---|
| XIRR | 25.2% | **25.9%** | 10.9% |
| Sharpe | **1.23** | 1.22 | 1.03 |
| Max DD | −56.5% | −54.6% | **−37.8%** |
| Cash drag | 1.1% | - | - |

**Reading:** Timing's edge is regime-dependent - Timed HODL dominates the last 1y
(16.1% vs SIP 0.7%) but SIP wins 3y/5y on return; the two tie over Full. Timed
almost always has the shallower drawdown of the two stock strategies. NIFTY 50
trails on return at every horizon ≥3y but has the mildest drawdowns.

## six7 almanac - pure strategy effect (OLD vs NEW, frozen prices)

Isolates the strategy change on the six7 almanac lists by holding **prices
constant** (the six7 price cache) and running two configs back-to-back:

- **OLD** = bb-30 watch window, **no** midline gate
- **NEW** = bb-60 watch window, **close < midline gate ON**

V4 idle-cash fallback is identical in both, so the only variables are the
Bollinger lookback and the midline gate. Each cell is `old→new (Δ)`. This is the
clean A/B; the "recalculated almanac" headline numbers also moved because the
price cache was re-downloaded - that data effect is *excluded* here.

**Full (~16y)** - Timed ₹L · XIRR% · Sharpe · MaxDD%

| List | Timed ₹L | XIRR% | Sharpe | MaxDD% |
|---|---|---|---|---|
| top10 | 260.9→263.5 (+2.7) | 29.8→29.9 (+0.1) | 0.99→1.00 | −47.0→−47.4 |
| top30 | 252.4→261.9 (+9.4) | 29.4→29.9 (+0.4) | 0.93→0.93 | −43.5→−43.4 |
| top50 | 258.2→268.7 (+10.6) | 29.7→30.1 (+0.5) | 1.03→1.03 | −44.6→−45.8 |
| top100 | 317.7→318.4 (+0.7) | 32.0→32.0 (0.0) | 1.17→1.16 | −49.5→−53.4 |
| strong_buy | 302.8→315.0 (+12.2) | 31.5→31.9 (+0.4) | 1.08→1.08 | −53.8→−56.6 |
| buy_plus | 399.0→454.5 (+55.6) | 34.6→36.0 (+1.4) | 1.07→1.06 | −53.4→−58.2 |
| six_plus | 399.0→454.5 (+55.6) | 34.6→36.0 (+1.4) | 1.07→1.06 | −53.4→−58.2 |
| perfect7 | 254.9→254.5 (−0.4) | 29.6→29.5 (0.0) | 1.03→1.02 | −45.4→−45.6 |
| univest_old | 234.6→253.8 (+19.2) | 28.6→29.5 (+0.9) | 0.69→0.72 | −65.6→−68.9 |
| **stocks_current** | **210.4→199.0 (−11.4)** | **27.4→26.8 (−0.6)** | 0.78→0.78 | −58.6→−58.6 |

**5y**

| List | Timed ₹L | XIRR% | Sharpe | MaxDD% |
|---|---|---|---|---|
| top10 | 18.4→18.5 (+0.1) | 16.8→16.9 (+0.1) | 0.99→0.98 | −26.9→−26.6 |
| top30 | 44.0→44.1 (+0.1) | 54.4→54.5 (+0.1) | 1.59→1.56 | −21.7→−25.4 |
| top50 | 35.5→34.9 (−0.6) | 44.8→44.0 (−0.8) | 1.52→1.49 | −21.5→−21.7 |
| top100 | 33.6→33.9 (+0.3) | 42.3→42.7 (+0.4) | 1.47→1.47 | −24.5→−26.4 |
| strong_buy | 32.0→32.4 (+0.4) | 40.2→40.7 (+0.5) | 1.47→1.47 | −19.2→−21.0 |
| buy_plus | 31.7→34.7 (+3.0) | 39.7→43.7 (+4.0) | 1.77→1.83 | −25.8→−27.2 |
| six_plus | 31.7→34.7 (+3.0) | 39.7→43.7 (+4.0) | 1.77→1.83 | −25.8→−27.2 |
| perfect7 | 40.6→41.8 (+1.2) | 50.8→52.1 (+1.4) | 1.52→1.48 | −21.2→−22.3 |
| univest_old | 31.4→27.7 (−3.6) | 39.3→34.0 (−5.3) | 1.31→1.17 | −32.6→−32.3 |
| **stocks_current** | **29.7→26.5 (−3.2)** | **36.9→31.9 (−5.0)** | 1.32→1.12 | −25.7→−29.1 |

**3y**

| List | Timed ₹L | XIRR% | Sharpe | MaxDD% |
|---|---|---|---|---|
| top10 | 7.9→8.0 (+0.1) | 4.6→5.3 (+0.7) | 0.34→0.36 | −27.7→−25.8 |
| top30 | 11.6→11.7 (+0.1) | 32.2→32.6 (+0.5) | 1.49→1.53 | −19.2→−18.4 |
| top50 | 11.5→11.9 (+0.5) | 31.3→34.3 (+3.0) | 1.57→1.67 | −23.4→−20.1 |
| top100 | 9.7→10.1 (+0.4) | 18.7→22.0 (+3.2) | 1.20→1.33 | −18.9→−16.3 |
| strong_buy | 10.0→10.4 (+0.4) | 21.1→24.2 (+3.1) | 1.29→1.40 | −17.1→−16.7 |
| buy_plus | 9.7→9.5 (−0.1) | 18.8→17.7 (−1.1) | 1.20→0.91 | −23.0→−21.9 |
| six_plus | 9.7→9.5 (−0.1) | 18.8→17.7 (−1.1) | 1.20→0.91 | −23.0→−21.9 |
| perfect7 | 10.8→11.1 (+0.3) | 26.7→28.7 (+2.0) | 1.33→1.38 | −19.9→−17.9 |
| univest_old | 9.2→8.8 (−0.4) | 15.0→11.5 (−3.5) | 0.87→0.75 | −22.7→−27.7 |
| **stocks_current** | 8.7→8.7 (0.0) | 11.0→11.4 (+0.4) | 0.66→0.67 | −22.2→−21.7 |

**1y**

| List | Timed ₹L | XIRR% | Sharpe | MaxDD% |
|---|---|---|---|---|
| top10 | 2.5→2.5 (0.0) | −9.1→−10.0 (−0.9) | −0.61→−0.63 | −26.9→−26.9 |
| top30 | 2.8→2.8 (−0.1) | 17.2→12.7 (−4.5) | 0.39→0.32 | −18.3→−20.6 |
| top50 | 2.9→3.1 (+0.2) | 22.5→40.2 (+17.7) | 0.69→1.42 | −16.8→−21.9 |
| top100 | 2.7→3.0 (+0.2) | 9.3→28.4 (+19.2) | 0.11→1.16 | −20.0→−22.7 |
| strong_buy | 2.7→3.0 (+0.3) | 9.8→30.9 (+21.0) | 0.23→1.26 | −20.1→−21.6 |
| buy_plus | 2.7→2.9 (+0.2) | 9.5→25.7 (+16.2) | 0.55→1.10 | −23.1→−21.7 |
| six_plus | 2.7→2.9 (+0.2) | 9.5→25.7 (+16.2) | 0.55→1.10 | −23.1→−21.7 |
| perfect7 | 2.7→2.7 (0.0) | 6.8→4.2 (−2.6) | −0.27→−0.12 | −24.3→−27.5 |
| univest_old | 2.6→2.6 (0.0) | −3.3→−0.2 (+3.1) | −0.79→−0.56 | −23.6→−21.4 |
| **stocks_current** | 2.5→2.6 (+0.1) | −4.6→−0.1 (+4.5) | −0.80→−0.56 | −24.8→−21.2 |

**Reading:**
- **1y is the clear win** (the design intent): broad screens jump +16 to +21 XIRR
  points and Sharpe goes ~0 → ~1.2 (strong_buy, top100, top50). The midline gate
  kept entries out of premature buys through the recent drawdown.
- **Full ~16y is ~neutral, mildly positive for most screens** - `buy_plus`/`six_plus`
  the standout (+₹55.6L); most others +0 to +1 XIRR. Matches the "≈neutral over full
  history" claim.
- **The live watchlist (`stocks_current`) is the consistent laggard** from the
  change: worse on Full (−0.6 XIRR) and 5y (−5.0 XIRR, Sharpe 1.32→1.12), flat 3y,
  better only 1y. `univest_old` behaves the same. The stricter gate trades
  medium-term return for better recent-period behavior on the actual portfolio.
- **Drawdowns run slightly deeper** on long horizons for several lists (the gate
  concentrates buying into deeper dips → more exposure when it commits), but
  shallower on 1y/3y.

## Caveat

All runs apply *today's* watchlist over full history - the same survivorship /
look-ahead the whole backtest carries. Treat as relative comparison, not a
tradeable result.

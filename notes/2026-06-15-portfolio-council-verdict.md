# Portfolio council verdict: which six7 list to adopt + project critique

Date: 2026-06-15
Author: quant-advisor (council chair), synthesising a four-member council
Status: recommendation - not yet applied to stocks.txt

## TL;DR

- **Best list to adopt: Top 50.** Near-unanimous (Quant, Risk, Fundamental); the
  Skeptic dissented on method, not on the list. Top 50 is the only candidate that
  is strong and consistent across 1/3/5y on a risk-adjusted basis, clears the 25%
  sector cap, carries no true microcaps, and lands inside the manageable
  20-50 name window.
- **But "adopt wholesale" must be redefined to respect the invariant.** The
  strategy never sells. Top 50 shares only 23 of your current 75 names, so a
  literal swap means selling 52 holdings (69% of the book) - which torches the
  product's core rule. The coherent path: **point the watchlist (`stocks.txt`) at
  Top 50 so all future dip-buys target it, and HODL the 52 legacy names (never
  sell, just stop adding).** The real book converges to Top 50 through new
  capital, not liquidation.
- **Do not believe the headline returns.** The 40/34/44% is survivorship +
  look-ahead hindsight (the repo's own code says "NOT a tradeable signal"). The
  forward edge over a plain NIFTY SIP is small and uncertain. The real, forward
  valid reason to adopt Top 50 is **quality and diversification**, not the
  backtest level.

## The question

Adopt one six7 fundamental-screen list wholesale as the new book, chosen to
perform consistently across 1/3/5y while staying manageable. Current book =
75-name "Univest + six7 Hybrid"; user had 54 real holdings; believes >100 names
is pointless.

## The candidates (Timed HODL, six7 almanac, snapshot 2026-06-01)

XIRR% / Sharpe / max-drawdown%, per horizon (source: `docs/data.js`):

| List (n) | 1Y | 3Y | 5Y |
|---|---|---|---|
| Top 30 (30) | 12.7 / 0.32 / -20.6 | 32.6 / 1.53 / -18.4 | 54.5 / 1.56 / -25.4 |
| **Top 50 (50)** | **40.2 / 1.42 / -21.9** | **34.3 / 1.67 / -20.1** | **44.0 / 1.49 / -21.7** |
| Strong Buy (84) | 30.9 / 1.26 / -21.6 | 24.2 / 1.40 / -16.7 | 40.7 / 1.47 / -21.0 |
| Top 100 (100) | 28.4 / 1.16 / -22.7 | 22.0 / 1.33 / -16.3 | 42.7 / 1.47 / -26.4 |
| Your book (75) | -0.1 / -0.56 / -21.2 | 11.4 / 0.67 / -21.7 | 31.9 / 1.12 / -29.1 |

Benchmarks (XIRR%): NIFTY 50 -10.2 / 1.4 / 5.9; NIFTY Midcap 100 8.5 / 12.1 / 17.2.

**Structural fact (Quant):** these are nested rank-cuts of one screen -
Top30 subset of Top50 subset of Top100, all inside Strong Buy. The choice is not
between strategies; it is *how deep to cut the same six7 rank*. Survivorship bias
is monotonic in cut-depth, so the deepest cut (Top 30) is the most
hindsight-inflated, which is exactly why its headline 5Y (54.5%, 3.61x) is a
mirage.

## The council

### The Quant - pick: Top 50
Only list positive and risk-adjusted-strong in all three windows (Sharpe
1.42/1.67/1.49). Top 30 is a hindsight trap: 1Y Sharpe 0.32 (dead money), edge
delivered in only two of three windows = concentration noise. Trust the broad
cuts because bias is monotonic in depth. Strong Buy is the honest, most
bias-robust runner-up but loses on size (84 names) and magnitude. **1Y numbers
are noise; weight 3Y/5Y Sharpe, where Top 50 leads.**

### The Risk Manager - pick: Top 50
Only list that clears the 25% sector cap. Verified sector weights:
- **Top 30: Financials 33% AND Materials 30% = 63% in two correlated
  rate/commodity-cycle sectors.** A leveraged bet on the Indian credit/commodity
  cycle in a 30-name costume. Disqualified.
- Perfect 7: 48% Financials. Disqualified.
- **Top 50: Financials 20%, Materials 22%, spread across 11 sectors. No
  sub-1000Cr microcaps (min 1,132Cr).** The manageable ceiling, not the floor.
- Strong Buy / Top 100: well diversified but reintroduce microcaps (ADSL 691Cr,
  ECOSMOBLTY 791Cr) and exceed the user's size ceiling.

### The Fundamental PM - pick: Top 50
- Every candidate is a massive upgrade on the current book (0 Strong Buy, median
  composite 5.0). The decision is Top 30 vs Top 50.
- **No quality cliff at names 31-50.** That slice is demoted from Top 30 only by
  PEG (valuation), not business quality - it actually *beats* Top 30 on
  RevGrowth5Y (100% vs 93%), EPSGrowth1Y (100% vs 93%), D/E (95% vs 67%). All 50
  are Strong Buy (composite >= 8.89). The real cliff is at Top 100 (floor 6.67).
- **Top 30's "purity" hides risk:** 5 perfect-10 lenders score full marks via the
  Financials D/E+FCF exemption - untested on leverage and cash flow, a
  concentrated housing/NBFC credit-cycle bet at the top of the book.

### The Skeptic - dissent: do NOT adopt wholesale
The sharpest and most valuable voice. Three points stand:
1. **The edge is mostly fake.** Lists ranked on today's fundamentals, replayed
   backward = survivorship + look-ahead. The repo's own code
   (`analysis/backtest_six7.py:20`) says "NOT a tradeable signal." The ~12-point
   5Y spread between Top 50 (44%) and your book (32%) is roughly the size of the
   survivorship premium - hindsight you cannot capture. Honest forward
   expectation: NIFTY (~11%) plus a modest, uncertain few points, wide error bars.
2. **"Adopt wholesale" violates the never-sells invariant.** Book intersection
   Top 50 = 23; selling 52 of 75 names (69%) to "adopt" the list contradicts the
   one rule the entire product is built on. A rotating quarterly screen bolted
   onto a buy-and-never-sell engine is a structural mismatch.
3. **Freezing today's winners breaks later.** Momentum/new-listing names
   (WAAREEENER, IXIGO, SOLARINDS, PREMIERENE) are in the list *because* they ran;
   never selling removes the rotation that would manage their mean-reversion.

## Adjudication (council chair)

The list question and the method question have different answers, and both are right.

**On the list: Top 50 wins decisively.** Quant (risk-adjusted consistency), Risk
(only list inside the sector cap with no microcaps), and Fundamental (no quality
cliff; dilutes Top 30's hidden lender concentration) independently converge. Top
30's headline 5Y is the single most bias-inflated number on the board and its
63% two-sector concentration is disqualifying for a book you never trim.

**On the method: the Skeptic is right that a literal swap is incoherent - so we
redefine "adopt."** The never-sells invariant governs the engine's signals and
your existing holdings. Changing `stocks.txt` changes the *universe the bot scans
and dip-buys going forward*; it does not command selling anything. So:

1. **Set the watchlist (`stocks.txt`) to Top 50.** All future dip-buys + the V4
   idle-cash fallback target the Top 50 universe. This is forward-legitimate: it
   is simply the six7 screen applied today, with no hindsight involved.
2. **HODL the 52 legacy names** not in Top 50. Never sell them. They stop
   receiving new buys; the book converges toward Top 50 via new capital only.
3. **Re-screen quarterly and only ever *append*** names that survive repeated
   screens (intersect Top 50 with Strong Buy / Perfect 7 to demand the screen
   agree with itself). Route additions through the dip engine - never lump-sum a
   small-cap on day one.

This keeps the invariant intact, captures the genuine quality/diversification
upgrade, and refuses to pretend the backtest level is forward edge.

## What this actually buys you (the honest "proof")

- **Forward-valid (real):** business quality jumps from 0 Strong Buy / median 5.0
  to 50/50 Strong Buy / median composite ~9.4; Financials concentration drops
  from ~24% to 20% and no single sector breaches 25%; the microcap liquidity tail
  (AMJLAND, NILAINFRA, INDIANCARD) is gone. These are properties of the list
  today, not hindsight.
- **Backward-only (discount heavily):** the 40/34/44% XIRR and the Sharpe grid.
  Top 50 beats your current book across every horizon in the almanac, but that
  comparison is survivorship-biased on both sides. Treat it as "a quality screen
  beats a stale mixed book," which is plausible, not as "expect 44% a year."

## Project critique - what is best, what is lacking, how to improve

**What is best**
- The signals-only / never-sells invariant is a genuine behavioral edge: it
  removes panic-selling, the most common retail mistake.
- The almanac is intellectually honest - it labels its own survivorship bias in
  code and prose. The new per-horizon Screens curves and the dashboard polish
  make the comparison legible.
- The strategy stack (BB dip gate -> MACD confirm -> Timed HODL with V4
  idle-cash fallback) is coherent and the cash-drag work (214d -> 21d idle) is
  real, measured improvement.

**What is lacking (harshest first, from the Skeptic + verified)**
1. **No point-in-time / delisting universe.** Every backtest sees only tickers
   that still exist and still rank today. Long-run Sharpe is computed on a
   universe purged of failures. This is the biggest credibility gap.
2. **Costs are a single 5bps slippage.** No STT, brokerage, GST, stamp duty, or
   impact cost. The V4 fallback fires hundreds of small buys into thin names;
   real returns will be materially below every dashboard number.
3. **The no-sell rule's downside is uncosted.** Unbounded single-name risk
   (a holding can go to zero) and -55% to -67% full drawdowns are never
   stress-tested behaviorally or in tail terms.
4. **Regime dependence is acknowledged then under-weighted.** Timed HODL beats
   SIP over 1y but roughly ties or trails over 3/5y/full. The *list* is the
   dominant return driver, not the BB+MACD timing - the dashboard's prominence
   inverts that.
5. **Backtest models a stricter strategy than the live bot** (`BUY_REQUIRE_BELOW_MID`
   True in backtest, False live). You are not backtesting the bot you run.
6. **No walk-forward / out-of-sample / second price source.** Every horizon ends
   on one pinned date; the recent window is the most overfit.

**How to improve (concrete, prioritized)**
1. Add a realistic India cost model (STT 0.1% delivery + brokerage + impact tier
   by daily turnover) and re-run; report net-of-cost numbers as the headline.
2. Build a point-in-time universe (or at least a delisting haircut) before
   trusting any long-run Sharpe.
3. Add a liquidity floor (e.g. drop sub-X-Cr daily-turnover names from buys) -
   this alone removes the worst microcap impact risk.
4. Reconcile backtest and live gates, or show both side by side and label which
   is the live signal.
5. Add a walk-forward / holdout split so the 1y win is not in-sample tuning.
6. Surface the regime-dependence finding prominently: state plainly that the
   list choice matters more than the timing.

## Recommended action

1. Adopt **Top 50** as `stocks.txt` (watchlist), keeping all legacy holdings as
   HODL (never sell). 27 new names to dip-buy over time; 52 legacy names held but
   no longer added to.
2. Re-run the strat backtest + dashboards on the new `stocks.txt` (the
   iteration workflow in CLAUDE.md), so the dashboard models the adopted book.
3. Treat the backtest as relative, not predictive; budget forward against NIFTY +
   a small, uncertain premium net of real costs.

The new-name set (Top 50 minus current book, 27 names to accumulate): CARYSIL,
LODHA, IXIGO, ANANTRAJ, SOLARINDS, JAMNAAUTO, IKS, EXCELSOFT, JKTYRE, TVSMOTOR,
LLOYDSME, WAAREEENER, GODFRYPHLP, NETWEB, GESHIP, VISHNU, HINDCOPPER, GRAVITA,
SHRIPISTON, TIMETECHNO, PGIL, NATIONALUM, COFORGE, PENIND, INDRAMEDCO, USHAMART,
HINDZINC.

*Personal-use analysis, not SEBI-registered investment advice.*

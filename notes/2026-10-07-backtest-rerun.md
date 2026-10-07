# Backtest rerun after the six7 D/E + watchlist-gate change (2026-10-07)

six7 changed its screen on 2026-10-07:

- **Criterion #5 D/E** tightened from `0 ≤ D/E ≤ 1.2` to `0 ≤ D/E ≤ 0.6` (soft ramp `(0.6, 0.8)`).
  1.2 sat at p90 of Indian non-financials and rejected nobody; 0.6 is p72.5.
- **Top-N gates**: Top 100 membership now needs market cap > ₹2,000cr **and** `0 < peg_eff < 2.0`,
  with no backfill. The list is 88 names, not 100.

The scorer also changed in ways that reach back before this date: the 2026-08-28 PEG rebuild
(own forward PE, 5Y-fallback growth) tripled PEG coverage, which is why the *ungated* screens
grew a lot (Strong Buy 88 → 263, Perfect 7 18 → 89). So "old vs new" below is **the June 16
screen vs the October 7 screen**, not D/E in isolation.

Everything here is the same strategy as always: Timed HODL (BB-200/2σ lower-band touch within 60
bars + Impulse MACD cross + close below the 200-SMA midline), V4 idle-cash fallback, salary-model
contributions for Full/10y, flat ₹20k/mo for 5y/3y/1y.

## What was kept, what was regenerated

| Artifact | Old (kept) | New |
|---|---|---|
| six7 almanac (lists × horizons) | `backtest_output/six7_20260616/` (results + the lists it ran) | `backtest_output/six7/` |
| Strat run (live union `stocks.txt`) | `backtest_output/20260827_104sym_bb60/` | `backtest_output/20261006_150sym_bb60/` |
| Source snapshot | `analysis/six7_stocks/snapshot_20260616.json` | `analysis/six7_stocks/snapshot_20261007.json` |

## 1. Like-for-like: same window, old screen vs new screen

To separate the screen change from four extra months of market, the new lists were also run over
the **old window** (to 2026-06-03, `backtest_six7.py --end 2026-06-03`). Sanity check: `univest_old`,
a list that did not change, reproduces the archived numbers exactly (29.5% / 41.9% / 34.0% /
11.5% / −0.2% XIRR), so every difference below comes from the lists.

Timed HODL XIRR %, with max drawdown in brackets. *n* = names with enough history for the BB-200
warmup.

| List | n old → new | Full | 10y | 5y | 3y | 1y |
|---|---|---|---|---|---|---|
| Top 10 | 10 → 8 | 29.4 → 29.9 (−66 → −50) | 41.0 → 39.7 | 49.1 → 47.0 | 31.8 → 26.5 | 18.8 → −6.1 |
| Top 30 | 29 → 27 | 30.8 → 29.6 | 43.0 → 39.2 | 50.5 → 41.1 | 35.6 → 32.9 | 27.9 → 25.5 |
| Top 50 | 46 → 44 | 29.3 → 29.9 (−51 → −60) | 39.6 → 38.3 | 44.0 → 47.4 | 34.3 → 30.1 | 37.7 → 25.3 |
| **Top 100** | 90 → 75 | **32.1 → 28.8** (−57 → −54) | 37.9 → 36.3 | 42.3 → 38.9 (−27 → −22) | 20.5 → 23.9 | 26.3 → 17.6 |
| Strong Buy | 79 → 148 | 31.3 → 27.2 | 38.0 → 30.8 | 39.6 → 33.2 | 21.6 → 14.1 | 28.7 → 0.1 |
| 6+ / Buy+ | 150 → 194 | 35.7 → 28.6 (−59 → −54) | 38.2 → 31.9 | 43.4 → 34.8 | 17.0 → 16.9 | 24.9 → −0.0 |
| Perfect 7 | 17 → 49 | 33.1 → 32.7 | 43.4 → 41.8 | 58.2 → 36.9 | 31.8 → 34.6 | 0.7 → 26.5 |
| Live watchlist | 98 → 135 | 28.2 → 26.7 | 40.8 → 34.2 | 35.4 → 34.0 | 17.7 → 16.3 | 1.8 → 2.1 |
| NIFTY 50 SIP | | 10.3 | 9.8 | 5.9 | 1.4 | −10.2 |

What it says:

- **Over the same window, the new screen earns less in hindsight** on every long horizon. Top 100
  Full XIRR falls 32.1% → 28.8%; the broad screens (Strong Buy, 6+) fall 4–7 points.
- **It is shallower in drawdown.** Top 100 Full max DD −56.8% → −53.5%, 5y −26.5% → −21.7%;
  6+ −58.8% → −53.7%; Top 10 −66% → −50%. That is what a D/E 0.6 ceiling should do: fewer levered
  names to blow up in a crash.
- **Timed HODL lost its edge over SIP on the new Top 100**: Full 28.8% Timed vs 29.9% SIP (old:
  32.1% vs 31.1%). The new list is lower-beta, so there are fewer deep dips for the BB/MACD gate to buy.
- **The ungated screens are now much wider and weaker.** Strong Buy and 6+ took in ~70 / ~45 more
  names, mostly small caps the PEG rebuild made scorable. Without the market-cap and PEG gates they
  carry the worst 1y numbers in the table (≈0%). That is the case for the gates: the gated Top 100
  held 17.6% over the same 1y.
- **Short windows are noisy.** Top 10 went from +18.8% to −6.1% over 1y on two names fewer; Perfect 7
  went the other way. Treat 1y/3y rows as anecdotes.

## 2. Published almanac: new screen, window to 2026-10-06

Same table, current window (`backtest_output/six7/`, live on the almanac's Screens tab):

| List | n | Full | 10y | 5y | 3y | 1y |
|---|---|---|---|---|---|---|
| Top 10 | 8 | 27.8 | 36.1 | 37.5 | 12.1 | −19.4 |
| Top 30 | 27 | 27.7 | 36.2 | 34.4 | 22.1 | 0.2 |
| Top 50 | 44 | 29.9 | 37.6 | **46.6** | **27.2** | 24.7 |
| **Top 100 (= six7.txt)** | 75 | 29.3 | 37.4 | 39.4 | 24.3 | **26.9** |
| Strong Buy | 150 | 27.7 | 32.1 | 35.3 | 15.5 | 25.9 |
| 6+ / Buy+ | 198 | 28.9 | 32.4 | 34.9 | 16.9 | 22.2 |
| Perfect 7 | 51 | **30.5** | 34.4 | 29.8 | 18.6 | 21.8 |
| Live watchlist | 135 | 26.6 | 34.3 | 34.8 | 16.8 | −2.3 |
| NIFTY 50 SIP | | 9.4 | 8.4 | 3.5 | −2.2 | −13.2 |
| NIFTY Midcap 50 SIP | | 15.8 | 17.5 | 15.0 | 7.2 | 0.6 |

The Top 50 / Top 100 are the steadiest rows across horizons. The 1y window (Oct 2025 → Oct 2026)
was a down year for the index (NIFTY 50 −13.2%), and the gated Top 100 still made +26.9%.

## 3. Strat run: the live watchlist (`stocks.txt` = six7 ∪ holdings)

| | Aug 27 run (104 sym, 100 with data) | Oct 6 run (150 sym, 135 with data) |
|---|---|---|
| Window | 2010-01-04 → 2026-08-27 | 2010-01-04 → 2026-10-06 |
| Timed HODL | ₹246.1L · 28.5% XIRR · DD −58.4% | ₹214.3L · 26.6% XIRR · DD −57.7% |
| SIP same stocks | ₹245.9L · 28.5% · DD −63.2% | ₹254.1L · 28.5% · DD −60.3% |
| Timed Entry+Exit | ₹34.4L · 4.4% | ₹98.2L · 17.7% |
| NIFTY 50 SIP | ₹52.8L · 10.3% | ₹50.3L · 9.4% |
| Cash drag / fallback buys | 1.2% / 727 | 1.1% / 983 |

The union grew 104 → 150 because six7 went Top 50 → Top 100 (88 after the gates) and holdings went
71 → 81. Timed HODL now trails SIP by ~2 points of XIRR on the union, at every horizon (Full 26.6 vs
28.5, 10y 33.9 vs 36.7, 5y 33.4 vs 34.7, 3y 16.9 vs 19.2, 1y −1.2 vs 23.8). The Aug run had them
tied. The extra 46 names spread signal buys thinner, and holdings include illiquid SME names that
drag the timed book. The six7 list alone (Top 100 above) keeps Timed within ~0.7 points of SIP.

Iterations tab, every past watchlist re-run on the same 2026-10-06 window (bb-60, no midline gate):

| Watchlist | 1y | 3y | 5y | 10y | Full |
|---|---|---|---|---|---|
| **Current (150)** | **10.9** | **25.4** | 35.4 | 34.9 | 27.4 |
| Aug 27 (104) | −0.8 | 23.8 | 33.8 | 35.9 | 27.6 |
| Apr 17 (102) | 3.4 | 20.1 | 32.5 | 34.1 | 25.6 |
| Apr 17 (75) | −8.4 | 13.3 | 29.3 | 34.8 | 25.8 |
| Apr 17 (50) | −8.8 | 21.2 | **36.8** | 31.6 | 25.7 |

On today's window the current watchlist leads on 1y and 3y and is level with the August one over
Full.

## Caveats

- **Hindsight.** Every list is today's screen run backwards. Both the old and new screens carry
  the same bias, so the like-for-like table ranks them fairly. The levels are not forecasts.
- **Shrinking n.** 13 of the 88 Top-100 names have no Yahoo data or less than the 310 bars
  (200 + 60 + 50) the signals need, mostly recent listings, so the backtest sees 75.
- **Benchmark swap.** Yahoo stopped serving `NIFTY_MIDCAP_100.NS`; the midcap benchmark is now NIFTY
  Midcap 50 (`^NSEMDCP50`). Over the old window the two agree within 0.3 points of XIRR (Full 16.3 vs
  16.6).
- **Sharpe is not comparable to April's README.** Since 2026-06-21, Sharpe/Sortino/vol/DD are
  computed on a unit NAV, not the contribution-inflated value series. That lowered every Sharpe;
  compare runs from June on only.
- `horizon_compare.py` had been pinned to 2026-04-20, so the Aug 27 run's horizon tables stopped in
  April. It now uses the run's data date (2026-10-06).

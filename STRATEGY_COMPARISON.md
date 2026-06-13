# Strategy comparison — watchlist & Bollinger experiments

Timed HODL strategy, period 2010-01-04 → 2026-04-17 (16.3y), ₹24.7L invested.
"OLD list" = 62-symbol `stocks.txt` (commit `88bb51a`); "NEW list" = current 75-symbol `stocks.txt`.

| Run | Final (Timed) | XIRR | Sharpe | Max DD | Stocks | Signals / Bought |
|---|---|---|---|---|---|---|
| OLD list / bb-30 (archived baseline) | ₹207.1L | 27.6% | 1.27 | −55.5% | 61 | 152 / 46 |
| OLD list / bb-60 (isolate) | ₹241.8L | 29.3% | 1.29 | −62.6% | 62 | — |
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
  signal-buy condition (NEW list / bb-60) gives ₹182.2L vs ₹182.6L — essentially
  identical, marginally worse on return and drawdown. Reason: when BB fires Buy
  (price touched the lower band) the close is almost always already below the
  midline, so the extra filter rarely changes the trade and only delays a few
  Watch-state entries. Flag retained as `BUY_REQUIRE_BELOW_MID` in `backtest.py`
  (default False).

## Horizon returns — old vs new watchlist

Timed HODL, bb-60, **flat ₹20k/month**, trailing windows ending 2026-04-17.
Signals are computed over full history (so the 200-bar Bollinger warmup is always
satisfied); only the investing/measurement window is the trailing horizon — that's
why a 1y horizon is valid even though it's shorter than the 200-day warmup.
Source: full-history price cache (`six7_backtest_output/_price_cache.pkl`).

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
  NEW bb-60+mid is the best 1y cell (16.1% vs 4.9% for plain NEW bb-60) — requiring
  close < midline avoided buying the recently-added names while they were still
  extended. But the edge **fades with horizon** and is neutral over Full (24.9 vs
  25.0). Over the full period it remains a wash, matching the salary-model run
  (₹182.2L vs ₹182.6L) — a recent-window improver, not a long-run one.

## Caveat

All runs apply *today's* watchlist over full history — the same survivorship /
look-ahead the whole backtest carries. Treat as relative comparison, not a
tradeable result.

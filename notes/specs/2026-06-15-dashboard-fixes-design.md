# Dashboard fixes (sub-project A) - design

Date: 2026-06-15
Status: approved-in-approach, pending spec review

## Context

This is sub-project A of a three-part effort:

- **A. Dashboard fixes** (this spec): correctness + UX bugs on `docs/index.html`.
- **B. `quant-advisor` subagent** (separate spec, later): a dispatchable professional
  investor / quant persona, project-aware, informed by mining `~/claude` history and
  online best practice.
- **C. Strategy + stock-list verdict** (separate spec, later): critique the project and
  use the six7 almanac to recommend the best watchlist (consistent over 1/3/5y,
  manageable, cap ~100), via a multi-agent council, with B advising.

A is first per the user's chosen sequence. B and C get their own brainstorm/spec cycles.

## Scope of A

Five fixes. Three are frontend-only (`docs/index.html`); two touch the Python data
layer and need a rebuild (`backtest_six7.py` + `build_web.py`, reusing the 26MB price
cache, so no large download).

### Fix 1 - Regime chart raw float (frontend)

**Bug:** the Regime returns chart shows `33.849999999999994%`.
**Cause:** `barChart` is called with `yfmt:v=>v+"%"` (index.html:876); both axis labels
and the bar tooltip reuse it, neither rounds.
**Fix:** change the regime call's formatter to `v=>v.toFixed(1)+"%"`. No other chart is
affected (buy-distribution uses integer counts).

### Fix 2 - Charts not zoomable (frontend)

**Bug:** chart cards cannot be enlarged. A modal already exists (`#overlay`, `closeModal`,
Esc + click-outside) but only row drilldowns use it.
**Fix:** add a generic chart-expand path:
- Maintain a registry mapping a chart-host id to a render thunk `(host)=>void` that
  redraws that chart into any host. Each chart render site registers its thunk.
- Add an expand affordance (a small "expand" control in the card header, plus making the
  chart-host itself clickable with `role=button` + keyboard support).
- On activate: open the modal, set title/subtitle from the card, render a fresh copy of
  the chart into a large modal host (`#mBody`). Charts already size to
  `host.clientWidth`, so a wide modal host yields a large chart automatically.
- Re-render on modal resize is not required (modal is fixed-size); a single render at
  open is enough.

Applies to all `lineChart` / `barChart` / `donut` cards across Overview, Portfolio,
Backtest, Screens, Iterations. Sparkline cells and the existing stock-price modal are
left as-is.

### Fix 3 - "Rolling alpha vs SIP" clarity (frontend)

**Meaning (verified in backtest.py:953):** for each day, `(trailing-window total return of
Timed HODL) - (trailing-window total return of equal-weight SIP)`, in percentage points.
The two series use a trailing 252-day (12-month) and 756-day (36-month) window. Above 0 =
the strategy beat a plain SIP over that look-back; below 0 = it lagged. The data also
carries `pct_win` (share of days the strategy was ahead) which the dashboard never shows.
**Fix:**
- Rename the series from `"1Y α" / "3Y α"` to `"12-month" / "36-month"` (index.html:868).
- Rewrite the card subtitle to plain language, e.g. "How far Timed HODL's trailing
  12-month and 36-month return runs ahead of an equal-weight SIP, in percentage points.
  Above the zero line means winning."
- Surface `pct_win` as a small caption, e.g. "Ahead of SIP 78% / 91% of days
  (12m / 36m)."

### Fix 4 - Index rows have no SIP number or trend (data layer + frontend)

**Bug:** the NIFTY 50 and NIFTY Midcap 100 rows in the Screens leaderboard show `-` for
the Trend sparkline and `-` for SIP final.
**Cause:** `bench_row()` (backtest_six7.py:152) runs a monthly SIP into the index via
`nifty_sip()`, stores the result only in the `timed` slot, leaves `sip` empty, and emits
no equity curve. `build_web.py` only builds curves for the 10 strategy lists, not the
benchmarks.
**Concept:** an index cannot be dip-timed; the index benchmark IS a monthly SIP into the
index, so its `timed` value and its SIP value are the same number.
**Fix:**
- `bench_row()` returns a downsampled `equity` series (from `sim["portfolio"]`) and its
  drawdown series, alongside the existing metrics.
- `comparison_<h>.json` carries that series per benchmark row (already serialized via the
  results list).
- `build_web.py`: emit a `curves[<benchmark key>]` entry from the benchmark equity so the
  sparkline + inspect chart can render; set `sip.final = timed.final` for benchmark rows
  (they are the same SIP).
- Frontend: the Screens table already renders a sparkline when a curve exists, so the
  Trend column lights up automatically; the SIP final column fills from the mirrored
  value. The inspect panel works because a curve now exists for the benchmark key.

### Fix 5 - Screens inspect curve windowed, table per-horizon (data layer + frontend)

**Bug:** the Screens leaderboard numbers are per-horizon fresh (a 3y row is a real 3y
sim), but the inspect equity/drawdown curve slices the tail of the full-history curve
(index.html:959), so the chart and the table disagree.
**Cause:** `run_metrics()` (backtest_six7.py:168) computes per-horizon metrics but discards
the windowed equity; only `run_full_suite()` (full history) emits curves.
**Fix:**
- `run_metrics()` returns downsampled `equity` (Timed HODL / SIP / NIFTY 50) and
  `drawdowns` (Timed HODL / SIP) for the window, the same shape `run_full_suite` produces.
- `comparison_<h>.json` carries these per row.
- `build_web.py`: emit per-horizon curves, e.g. `curves_by_h[<h>][<key>]`, in addition to
  the existing full-history `curves` (kept for "All").
- Frontend `renderScrInspect`: for the active horizon, read the per-horizon curve and draw
  it directly (no `sliceTS` of the full curve). For "All", use the existing full curve.

**Data size note:** per-horizon curves for 10 lists x 5 horizons x ~3 series, downsampled
to ~200-400 points, will grow `docs/data.js` (currently 447KB). Acceptable; downsample
benchmark and per-horizon series the same way `downsample()` already does.

## Rebuild + verification

After code changes:

1. `python3 analysis/backtest_six7.py` (reuses `_price_cache.pkl`, `_midcap_cache.pkl`).
2. `python3 analysis/build_web.py` (rewrites `docs/data.js`).
3. Open `docs/index.html` locally and check each fix:
   - Regime chart shows rounded percentages.
   - Every chart card opens enlarged in the modal and closes cleanly.
   - Rolling-alpha card reads clearly and shows the win-rate caption.
   - NIFTY 50 and NIFTY Midcap 100 rows show a trend sparkline and a SIP value.
   - Switching 1Y/3Y/5Y/10Y re-bases the Screens inspect curve to match the table.

`strat_data.js` (the strat dashboard data) is unaffected: rolling-alpha and regime fixes
are display-only and read existing fields. Only `data.js` (six7) is regenerated.

## Out of scope for A

- Building the `quant-advisor` agent (sub-project B).
- The strategy critique and stock-list recommendation (sub-project C).
- Any change to the live bot, the strategy itself, or `stocks.txt`.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Project: Dip Mafia** (formerly HODL-bot), a long-only dip-buying signal bot for NSE stocks. Crucial invariant: it is *signals only*. The strategy **never sells**: Sell/red signals are indications of technical weakness for awareness, never executed. Everything user-facing (Telegram, README, repo bio) must reflect "we only buy dips and HODL."

## How this runs

The only real entry point is `bot.py`, invoked by `.github/workflows/dip-mafia.yml` on a cron schedule. `bollinger_signals.py` and `macd_signals.py` have `__main__` blocks but they are not part of the production path, treat them as import-only modules. There are no tests, linter, or build step.

Local invocation (rarely needed):
```bash
pip install -r requirements.txt
python bot.py
```

## Repo layout

```
bot.py  bollinger_signals.py  macd_signals.py   live signal path (run by the workflow); root
analysis/   backtest.py  horizon_compare.py  portfolio_view.py  backtest_six7.py
            build_web.py  run_paths.py         research/backtest tooling
pine/       dip_mafia*.pine                     standalone TradingView ports (+ README)
notes/      STRATEGY_COMPARISON.md  context.md  TODO.md
tests/      test_bb_position.py
backtest_output/   dated run subfolders + six7/   docs/   six7_stocks/
```

**Run `analysis/` scripts from the repo root** (e.g. `python3 analysis/backtest.py`) - they use paths relative to the working directory (`backtest_output/`, `stocks.txt`, `docs/`). `analysis/backtest.py` adds the repo root to `sys.path` so it can import the root-level `macd_signals`.

## Strategy

Long-only signals for NSE stocks listed in `stocks.txt` (symbols without `.NS` suffix; `bot.py` appends it). The pipeline is:

1. **Bollinger Bands as a universe filter** (`bollinger_signals.py`). 200-period, 2σ. A stock is `Buy` if today's low/close touches or breaks the lower band, `Watch` if it did so within the last 60 bars (capped by available history, ~50 bars with 1y data, since the band needs a 200-bar warmup), else `Hold`. This is the *gate*, MACD output for stocks outside Buy+Watch is discarded from the Telegram message.

2. **MACD crossovers as the long signal** (`macd_signals.py`). Two indicators run in parallel on the same data:
   - Standard MACD (12/26/9 EMA)
   - Impulse MACD (LazyBear, SMMA of high/low, ZLEMA of HLC/3, length_ma=34, signal=9)

   Both feed `_trend_to_action`, which walks the crossover series and emits the *latest* state: `Buy`/`Sell` on the crossover bar, then `Hold` (after Buy) or `Wait for Buy` (after Sell) until the next cross. Only `Buy`/`Sell` rows render as stock lines in Telegram; `Hold`/`Wait for Buy` are counted into the summary.

3. **Fallback averaging** (backtest only, `simulate_timed_hodl`). The "V4" default adopted after the cash-drag study (`notes/STRATEGY_COMPARISON.md`): if cash sits idle for >21 trading days (~1 month), deploy it equally across **any watchlist stock** below the BB midline (200-SMA); if nothing is below midline (raging bull), `fallback_force` deploys across all priced stocks so cash never rots. Each stock is capped at 15% of portfolio value. This cut the longest idle streak 214d→21d and cash drag 5.7%→1.2% while improving returns/Sharpe. Pass `("held", False, 42)` to `simulate_timed_hodl` to restore the old conservative fallback (held-only, below-midline, 42-day threshold).

4. **Partial SIP+Timed** (`simulate_partial_sip`) - **disabled for now** (suspected incorrect implementation). The function is still defined in `backtest.py` but is no longer computed or shown in any output (`backtest.py` / `backtest_six7.py` / the dashboards). To re-enable, add it back to `metrics_list` / `portfolios` / `nav_series` in `main` and `run_full_suite`.

5. **Telegram delivery** (`bot.py:send_bulk_telegram_message`). MarkdownV2, sent to multiple chat IDs. Two sections: Standard MACD and Impulse MACD, each restricted to the Bollinger-filtered universe. Header includes NIFTY 50 and NIFTY Midcap 100 day move + % from ATH (`get_index_moves`).

## Architecture notes

**Single download, shared DataFrame.** `bot.py` calls `yf.download` once for all tickers (period=1y, interval=1d) and passes that multi-index DataFrame to `process_both_signals` and `process_bollinger_signals`. Per-stock frames are sliced with `data.xs(stock, axis=1, level=1)`. Do not reintroduce per-stock downloads in the hot path.

**Bollinger is the filter, not a co-equal signal.** If you add or change signals, preserve the invariant that MACD lines in Telegram are gated by the Bollinger filter `{Buy, Watch}` (via `passes_bollinger_gate`). Console output prints full Bollinger results separately.

**Live bot vs backtest gate (intentional divergence).** `bot.py` `REQUIRE_CLOSE_BELOW_MIDLINE = False` - the live Telegram bot shows the **full** Buy/Watch universe (no midline filter) so no alerts are suppressed. The **backtest** runs tighter: `backtest.py` `BUY_REQUIRE_BELOW_MID = True` adds the close-below-200-SMA requirement to Timed HODL buys (better recent-horizon returns; see `notes/STRATEGY_COMPARISON.md`). So the backtest models a stricter strategy than the bot signals, on purpose. `passes_bollinger_gate` in `bot.py` still supports the gate if the flag is flipped True.

**MarkdownV2 escaping.** Any dynamic text inserted into the Telegram message must go through `escape_md`, the special-char set is broad (`.`, `-`, `!`, `(`, `)` etc. all require escaping) and unescaped output will cause Telegram to reject the message.

**Data sufficiency guards.** Bollinger needs `length + 30` bars (230 by default); MACD needs ≥50. Tickers with insufficient history are skipped with a `✗` log line. Timestamps are converted to Asia/Kolkata.

**Secrets.** `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_IDS` (comma-separated) are read from environment variables. Set them in GitHub Secrets and pass via the workflow.

## Backtest output layout

All backtest artifacts live under a single parent, `backtest_output/`, defined in one place by **`analysis/run_paths.py`**:

```
backtest_output/
  <YYYYMMDD>_<N>sym_bb<L>/   one self-contained run (charts, dashboard_data.json,
                             horizons.json, trades.csv, meta.json, stocks.txt snapshot)
  …                          older runs, same naming
  six7/                      six7 almanac outputs (results tracked; *.pkl caches git-ignored)
```

There is **no separate archive folder**. The "current" run is simply the newest subfolder - `run_paths.current_run()` returns the one with the highest `meta.json` date (ties broken by folder name); `run_paths.archived_runs()` returns the rest. `portfolio_view.py`, `horizon_compare.py`, and `backtest_six7.py` all resolve paths through `run_paths` - never hard-code `backtest_output/...`.

## Re-running the strat backtest (iteration workflow)

Whenever `stocks.txt` or a strategy parameter changes, run a fresh strat backtest. Prior runs are kept automatically (each run is its own dated subfolder), so the Iterations tab always compares against them - no manual archiving step:

1. **Re-run** `python3 analysis/backtest.py` (from the repo root). It writes a fresh `backtest_output/<YYYYMMDD>_<N>sym_bb<L>/` (date from `assumptions.end_date`, N from `stocks.txt`, L from `CONFIG.bb_lookback`), auto-emitting `meta.json` and a `stocks.txt` snapshot so the run is self-describing. Older run folders are left untouched. (Prune stale runs by hand if the Iterations list gets noisy.)
2. **Recompute horizons**: `python3 analysis/horizon_compare.py` writes `<current run>/horizons.json` - Timed HODL 1y/3y/5y/10y/Full returns for the current + each older watchlist, across bb-60 / bb-30 / bb-60+midline variants (uses the full-history price cache `backtest_output/six7/_price_cache.pkl` when present, else downloads). `strategy_horizons` carries the full per-horizon × per-strategy metric grid (final_value, mult, xirr, sharpe, sortino, maxdd, maxdd_days, vol, cash) that feeds the dashboard's Backtest cards and comparison, **plus `strategy_horizons.portfolios`** - a complete per-horizon portfolio book (summary, holdings rows, alloc, pnl, nav) for the current watchlist, built from each horizon's windowed `simulate_timed_hodl` buy_log and valued at the data-date close. Feeds the Iterations section's Horizon Returns tables (best per row highlighted).
3. **Rebuild the data layer**: `python3 analysis/portfolio_view.py` emits **`docs/strat_data.js`** (`window.STRAT_DATA` = portfolio + backtest + iterations + horizons). It no longer generates HTML; the unified, hand-authored page is **`docs/index.html`** (consumes `strat_data.js` + `data.js`). The portfolio block is **`portfolio.byHorizon[<HZ>]`** - one fresh, self-contained Timed HODL book per horizon (a `5Y` book started investing 5 years ago, NAV growing from ~₹0, valued at the data-date close), reshaped directly from `strategy_horizons.portfolios`. `All` is the full-history sim (== the lifetime book). So flipping the global horizon control re-bases every Portfolio/Overview card, chart and the holdings table - no lifetime-curve slicing, no live-price endpoint. (`portfolio_view.py` no longer reads `trades.csv` or fetches live prices.) Each book's `nav` carries both the absolute rupee `value`/`invested` series **and a `navindex`** - a unitized fund-style NAV (base 100) where each monthly deposit buys units, so contributions don't move it (only performance does). The Overview/Portfolio charts have a **Value / NAV** toggle to switch between them. Then update the README "Latest Results" block.

The unified dashboard (`docs/index.html`) has five horizon-aware sections (Overview · Portfolio · Backtest · Screens · Iterations) behind one global `1Y/3Y/5Y/10Y/All` control. It is hand-authored with a custom SVG chart kit (no chart library); design system in `DESIGN.md`, product context in `PRODUCT.md`. `docs/strat.html` is a redirect stub to `index.html`. The Screens section reads `data.js` (built by `build_web.py`, see the six7 almanac section).

**bb-60 is the default lookback** (live `bollinger_signals.py` and `backtest.py` CONFIG `bb_lookback=60`); horizon comparisons list it first and label it the default.

`BUY_REQUIRE_BELOW_MID` in `backtest.py` (**default True**, matching the live bot's `REQUIRE_CLOSE_BELOW_MIDLINE`): a Timed HODL signal buy also requires close < BB midline. Adds returns over 1/3/5y horizons, ~neutral over the full 16y - see `notes/STRATEGY_COMPARISON.md`. Set False to model the plain BB(touch)+MACD gate.

## Rebuilding the six7 almanac

The six7 almanac (`docs/`, published on GitHub Pages) compares the screener lists in `six7_stocks/lists/` plus the live watchlist, running **Timed HODL vs SIP** across 1y/3y/5y/10y/Full horizons. `analysis/backtest_six7.py` does *not* define its own strategy - it deep-copies `bt.CONFIG` (so `bb_lookback=60`) and calls `bt.simulate_timed_hodl`, which honors `BUY_REQUIRE_BELOW_MID` and the V4 idle-cash fallback by default. **So the almanac's "Timed" numbers are the same V4 + midline + bb-60 strategy as the strat dashboard** - whenever that strategy or `stocks.txt` changes, the almanac is stale until rebuilt:

1. **Recompute** `python3 analysis/backtest_six7.py` (from the repo root) → writes `backtest_output/six7/` (per-list 8-chart suites + `comparison_<h>.{csv,json,png}`). Reuses `backtest_output/six7/_price_cache.pkl` when the ticker-union + `END` match; otherwise it re-downloads and rewrites the cache. `END` is pinned in the script for reproducibility.
2. **Rebuild the web data** `python3 analysis/build_web.py` → assembles `docs/data.js` (`window.SIX7_DATA`) from the comparison JSON, which the GitHub Pages almanac reads.

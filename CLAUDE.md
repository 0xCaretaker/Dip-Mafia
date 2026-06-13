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

## Strategy

Long-only signals for NSE stocks listed in `stocks.txt` (symbols without `.NS` suffix; `bot.py` appends it). The pipeline is:

1. **Bollinger Bands as a universe filter** (`bollinger_signals.py`). 200-period, 2σ. A stock is `Buy` if today's low/close touches or breaks the lower band, `Watch` if it did so within the last 60 bars (capped by available history, ~50 bars with 1y data, since the band needs a 200-bar warmup), else `Hold`. This is the *gate*, MACD output for stocks outside Buy+Watch is discarded from the Telegram message.

2. **MACD crossovers as the long signal** (`macd_signals.py`). Two indicators run in parallel on the same data:
   - Standard MACD (12/26/9 EMA)
   - Impulse MACD (LazyBear, SMMA of high/low, ZLEMA of HLC/3, length_ma=34, signal=9)

   Both feed `_trend_to_action`, which walks the crossover series and emits the *latest* state: `Buy`/`Sell` on the crossover bar, then `Hold` (after Buy) or `Wait for Buy` (after Sell) until the next cross. Only `Buy`/`Sell` rows render as stock lines in Telegram; `Hold`/`Wait for Buy` are counted into the summary.

3. **Fallback averaging** (backtest only, `simulate_timed_hodl`). If cash sits idle for >42 trading days (~2 months), deploy it equally into existing holdings where price is below the BB midline (200-SMA). Each stock is capped at 15% of portfolio value to prevent concentration. This reduces cash drag without buying overvalued positions.

4. **Partial SIP+Timed** (backtest only, `simulate_partial_sip`). Splits each month's budget 50/50: half goes as plain SIP across all stocks regardless of signals, half waits for BB+MACD buy signals (with the same fallback logic as the timed strategy). Included as a comparison, currently underperforms pure timed with fallback (₹193.7L vs ₹207.1L) but has better risk-adjusted metrics (Sharpe 1.29, Sortino 3.05).

5. **Telegram delivery** (`bot.py:send_bulk_telegram_message`). MarkdownV2, sent to multiple chat IDs. Two sections: Standard MACD and Impulse MACD, each restricted to the Bollinger-filtered universe. Header includes NIFTY 50 and NIFTY Midcap 100 day move + % from ATH (`get_index_moves`).

## Architecture notes

**Single download, shared DataFrame.** `bot.py` calls `yf.download` once for all tickers (period=1y, interval=1d) and passes that multi-index DataFrame to `process_both_signals` and `process_bollinger_signals`. Per-stock frames are sliced with `data.xs(stock, axis=1, level=1)`. Do not reintroduce per-stock downloads in the hot path.

**Bollinger is the filter, not a co-equal signal.** If you add or change signals, preserve the invariant that MACD lines in Telegram are gated by the Bollinger filter. The gate is `{Buy, Watch}` and — when `REQUIRE_CLOSE_BELOW_MIDLINE = True` (current default in `bot.py`) — also requires the latest close to sit below the BB midline (band position ⏬/🔽), via `passes_bollinger_gate`. Buy names always qualify; this only drops Watch names that recovered above their 200-SMA. Set the flag False to revert to the plain `{Buy, Watch}` gate. Console output prints full Bollinger results separately.

**MarkdownV2 escaping.** Any dynamic text inserted into the Telegram message must go through `escape_md`, the special-char set is broad (`.`, `-`, `!`, `(`, `)` etc. all require escaping) and unescaped output will cause Telegram to reject the message.

**Data sufficiency guards.** Bollinger needs `length + 30` bars (230 by default); MACD needs ≥50. Tickers with insufficient history are skipped with a `✗` log line. Timestamps are converted to Asia/Kolkata.

**Secrets.** `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_IDS` (comma-separated) are read from environment variables. Set them in GitHub Secrets and pass via the workflow.

## Re-running the strat backtest (iteration workflow)

Whenever `stocks.txt` or a strategy parameter changes, run a fresh strat backtest **and keep the prior one for comparison**. The Iterations tab on the strat dashboard auto-discovers archived runs, so the only manual step is archiving before the new run:

1. **Archive the current run** into a dated folder before overwriting: `backtest_output_archive_YYYYMMDD/` (the data-as-of date from `dashboard_data.json` → `assumptions.end_date`). Copy the whole `backtest_output/` contents plus the generated `dashboard.html`, a snapshot of the old `stocks.txt`, and a `meta.json` (`{date, label, watchlist_size, bb_lookback}`). `portfolio_view.py` reads `meta.json` to label the iteration; `load_iterations()` globs `backtest_output_archive_*`, so new archives appear in the UI automatically — no code change.
2. **Re-run** `python3 backtest.py` (writes fresh `backtest_output/`).
3. **Recompute horizons**: `python3 horizon_compare.py` writes `backtest_output/horizons.json` — Timed HODL 1y/3y/5y/Full returns for the current + each archived watchlist, across bb-60 / bb-30 / bb-60+midline variants (uses the full-history price cache `six7_backtest_output/_price_cache.pkl` when present, else downloads). Feeds the Iterations tab's Horizon Returns tables (best per row in red).
4. **Rebuild the views**: `python3 portfolio_view.py` regenerates `dashboard.html` and publishes a copy to `docs/strat.html` (live on GitHub Pages, linked from the six7 almanac). It reads `horizons.json` if present. Then update the README "Latest Results" block.

**bb-60 is the default lookback** (live `bollinger_signals.py` and `backtest.py` CONFIG `bb_lookback=60`); horizon comparisons list it first and label it the default.

`BUY_REQUIRE_BELOW_MID` in `backtest.py` (default False) is an experiment flag: when True, a Timed HODL signal buy also requires close < BB midline. Neutral over the full period but the best recent-1y variant on the current list — see `STRATEGY_COMPARISON.md`.

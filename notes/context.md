# Goal
Long-only signal bot for NSE stocks: BB + Impulse MACD timing strategy with Telegram + Discord delivery. Backtest validates the strategy at portfolio level against equal-weight SIP and NIFTY 50.

# Current Status
- **Bot**: Production-ready, runs via GitHub Actions cron (`dip-mafia.yml`). Posts to Telegram + an opt-in Discord webhook (`DISCORD_WEBHOOK_URL` repo secret).
- **Backtest**: Portfolio-level simulation. `stocks.txt` shares a single monthly budget across signaling stocks. Compares 3 strategies + NIFTY 50 benchmark. Generates 8 numbered PNG charts + console summary + trade log CSVs.
- **Latest results** (data as of 2026-04-17, headline strat backtest against `six7.txt` alone — 46 of 50 priced, bb_lookback=60, midline buy-gate ON, V4 idle-cash fallback, ₹24.7L invested over 16.3 years):
  - Your Strategy (Timed HODL): ₹238.6L, XIRR 29.2%, Sharpe 1.38, MaxDD -41.3%
  - SIP on Your Stocks: ₹221.2L, XIRR 28.3%, Sharpe 1.35, MaxDD -45.0%
  - SIP on NIFTY 50: ₹52.3L, XIRR 10.9%, Sharpe 1.13, MaxDD -37.3%
  - Timed Entry+Exit: ₹76.3L, XIRR 15.8% — destroys returns, don't use
  - V4 fallback (deploy idle cash after 21d into any watchlist stock below midline, force if none): cash drag 1.3%, longest idle 21d
  - Both strategies crush NIFTY 50 by ~4.6x; Timed HODL edges SIP at Full + 10y, narrowly loses 5y.
  - Older runs kept as their own dated subfolders: `20260417_75sym_bb60`, `20260417_62sym_bb30`, `20260417_102sym_bb60`.
  - **Gates aligned (2026-06-17)**: backtest `BUY_REQUIRE_BELOW_MID=True` and live bot `REQUIRE_CLOSE_BELOW_MIDLINE=True`. The bot now posts only Watch names that are still below the 200-SMA midline, matching what the backtest would buy.

# Architecture
- `bot.py` - single entry point. Reads `six7.txt` ∪ `holdings.txt` via `watchlist.py` (so signals fire on both the Top 50 and your real book; each line tagged `⭐` / `💼`). Downloads all tickers once via `yf.download`, passes the shared DataFrame to signal modules. Sends MarkdownV2 Telegram messages + a parallel Discord post (`@here` ping).
- `bollinger_signals.py` - BB 200-period, 2σ. Gate filter: Buy/Watch/Hold.
- `macd_signals.py` - Standard MACD (12/26/9) + Impulse MACD (LazyBear, SMMA/ZLEMA, length=34, signal=9). Crossover → Buy/Sell/Hold/Wait.
- `watchlist.py` - two-list loader; regenerates the derived `stocks.txt` union for the analysis tooling.
- `analysis/backtest.py` - portfolio-level backtest. Reads `stocks.txt`, downloads via yfinance, runs 3 strategies + NIFTY 50. Outputs 8 numbered PNG charts + console summary + trade log CSVs.
- `analysis/horizon_compare.py` + `portfolio_view.py` - per-horizon grid + reshape into `docs/strat_data.js` (powers the unified dashboard).
- `analysis/backtest_six7.py` + `build_web.py` - rebuilds the six7 almanac (`docs/data.js`) from `analysis/six7_stocks/lists/`.

# Backtest Charts (backtest_output/<dated run>/)
1. `1_equity_curves.png` - All strategies + NIFTY 50 + invested line on one chart
2. `2_drawdowns.png` - Side-by-side drawdowns with max annotated
3. `3_cash_utilization.png` - % invested vs cash over time
4. `4_regime_returns.png` - NAV-based returns per regime (strips out cash flow effects) for all 3 strategies
5. `5_rolling_alpha.png` - 1Y and 3Y rolling outperformance vs SIP
6. `6_buy_distribution.png` - Which stocks got bought and how often
7. `7_buy_timeline.png` - When buys happened over time
8. `8_summary_table.png` - Full metrics table as image, best values highlighted

# Key Design Decisions
- BB is the **gate**, MACD is the **signal** - this invariant must be preserved.
- Portfolio-level simulation: single budget split across signaling stocks. The point of 50+ stocks is temporal diversification (something is always dipping → less cash drag).
- The strategy **never sells**: Sell/red signals are awareness-only, never executed.
- yfinance v1.x: columns are always MultiIndex `(Price, Ticker)`.
- Risk-free rate = 6% (India) for Sharpe/Sortino.
- Slippage = 5 bps.
- Backtest salary: ₹22K/month starting 2010, 25% invested, 10% annual hike (reaches ~₹1L/month by 2026).

# Key Files
- `bot.py` - production entry point
- `six7.txt` - Top 50 watchlist (overwritten by the external six7 mirror)
- `holdings.txt` - real Zerodha book (manual Kite snapshot)
- `stocks.txt` - DERIVED union (six7 ∪ holdings); analysis input only
- `analysis/backtest.py` - portfolio-level backtest (run: `python3 analysis/backtest.py` from repo root)
- `backtest_output/<dated run>/` - 8 numbered PNG charts + trades.csv + meta.json + stocks.txt snapshot (newest run = current; see `analysis/run_paths.py`)
- `analysis/six7_stocks/` - baked snapshot + per-list rebuilds for the almanac
- `docs/index.html` + `strat_data.js` + `data.js` - unified dashboard (GitHub Pages)
- `.github/workflows/dip-mafia.yml` - cron schedule + manual force-send input
- `.github/workflows/regen-stocks.yml` - auto-regen `stocks.txt` on source-list change
- `requirements.txt` - yfinance, requests (backtest also needs matplotlib, scipy)

# Known Issues
- ~5-7 stocks from `holdings.txt` are illiquid SMEs / delisted on Yahoo (download fails, skipped with a `✗` log line).
- `requirements.txt` doesn't include matplotlib/scipy (backtest-only deps).
- Timed HODL has last-price carry-forward for stocks missing data on a given day.

# Goal
Long-only signal bot for NSE stocks: BB + Impulse MACD timing strategy with Telegram delivery. Backtest validates the strategy at portfolio level against equal-weight SIP and NIFTY 50.

# Current Status
- **Bot**: Production-ready, runs via GitHub Actions cron (`dip-mafia.yml`)
- **Backtest**: Focused portfolio-level simulation. stocks.txt stocks share a single monthly budget. Compares 3 strategies + NIFTY 50 benchmark. Generates 8 clean PNG charts + console summary.
- **Latest results** (data as of 2026-04-17, 73 stocks from 75-symbol stocks.txt, bb_lookback=60, midline buy-gate ON, V4 idle-cash fallback, ₹24.7L invested over 16.3 years):
  - Your Strategy (Timed HODL): ₹185.9L, XIRR 26.4%, Sharpe 1.31, MaxDD -50.8%
  - SIP on Your Stocks: ₹197.2L, XIRR 27.0%, Sharpe 1.31, MaxDD -51.4%
  - SIP on NIFTY 50: ₹52.3L, XIRR 10.9%, Sharpe 1.13, MaxDD -37.3%
  - Timed Entry+Exit: ₹34.4L — destroys returns, don't use
  - V4 fallback (deploy idle cash after 21d into any watchlist stock below midline, force if none):
    cash drag 5.7%→1.2%, longest idle 214d→21d; Timed HODL now best on Sharpe/Sortino/MaxDD
  - SIP nearly matches on absolute returns (neck and neck)
  - Both crush NIFTY 50 by ~3.6x
  - Prior 62-symbol / 30-bar run kept as its own subfolder backtest_output/20260417_62sym_bb30/
  - Gate divergence (intentional): backtest BUY_REQUIRE_BELOW_MID=True (tighter, better 1/3/5y);
    live bot REQUIRE_CLOSE_BELOW_MIDLINE=False (sends ALL Buy/Watch alerts, no midline filter).

# Architecture
- `bot.py` — single entry point. Downloads all tickers once via `yf.download`, passes shared DataFrame to signal modules. Sends MarkdownV2 Telegram messages.
- `bollinger_signals.py` — BB 200-period, 2σ. Gate filter: Buy/Watch/Hold.
- `macd_signals.py` — Standard MACD (12/26/9) + Impulse MACD (LazyBear, SMMA/ZLEMA, length=34, signal=9). Crossover → Buy/Sell/Hold/Wait.
- `backtest.py` — Portfolio-level backtest. Reads stocks.txt, downloads via yfinance, runs 3 strategies + NIFTY 50. Outputs 8 numbered PNG charts + console summary + trade log CSVs.

# Backtest Charts (backtest_output/<dated run>/)
1. `1_equity_curves.png` — All strategies + NIFTY 50 + invested line on one chart
2. `2_drawdowns.png` — Side-by-side drawdowns with max annotated
3. `3_cash_utilization.png` — % invested vs cash over time
4. `4_regime_returns.png` — NAV-based returns per regime (strips out cash flow effects) for all 3 strategies
5. `5_rolling_alpha.png` — 1Y and 3Y rolling outperformance vs SIP
6. `6_buy_distribution.png` — Which stocks got bought and how often
7. `7_buy_timeline.png` — When buys happened over time
8. `8_summary_table.png` — Full metrics table as image, best values highlighted

# Key Design Decisions
- BB is the **gate**, MACD is the **signal** — this invariant must be preserved
- Portfolio-level simulation: single budget split across signaling stocks. Point of 60+ stocks is temporal diversification (something always dipping → less cash drag)
- yfinance v1.x: columns are always MultiIndex `(Price, Ticker)`, no `auto_adjust` param
- Risk-free rate = 6% (India) for Sharpe/Sortino
- Slippage = 5 bps
- Backtest salary: ₹22K/month starting 2010, 25% invested, 10% annual hike (reaches ~₹1L/month by 2026)

# Key Files
- `bot.py` — production entry point
- `backtest.py` — portfolio-level backtest (run: `python3 backtest.py`)
- `stocks.txt` — watchlist (75 symbols, no `.NS` suffix)
- `backtest_output/<dated run>/` — 8 numbered PNG charts + trades.csv + trades_monthly_summary.csv (newest run = current; see `run_paths.py`)
- `.github/workflows/dip-mafia.yml` — cron schedule
- `requirements.txt` — yfinance, requests (backtest also needs matplotlib, scipy)

# Known Issues
- ~14 stocks from old BROAD_NSE_UNIVERSE are delisted/renamed on Yahoo (MINDTREE→LTIM, etc.)
- `requirements.txt` doesn't include matplotlib/scipy (backtest-only deps)
- Timed HODL has last-price carry-forward for stocks missing data on a given day

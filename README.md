# Dip Mafia: Crash-Buy Signals for Indian Equities (NSE)

**Dip Mafia** (formerly HODL-bot) is an automated **algo-trading signal system** that identifies deeply undervalued stocks during market crashes using **200-period Bollinger Bands** and **dual MACD crossovers**, then delivers actionable buy signals with market sentiment to Telegram, fully automated via GitHub Actions.

> **Philosophy**: Buy the crash, hold forever. This bot watches 70+ fundamentally screened NSE stocks and alerts when they hit statistically extreme lows with confirmed momentum reversal. No day-trading, no exits, just long entries at high-conviction dips.
>
> **We never sell.** Sell / red signals are **indications only**: they flag technical weakness for awareness; Dip Mafia does not execute exits. The strategy is buy dips and HODL.
>
> The watchlist in `stocks.txt` is curated via a separate fundamental analysis tool (not included in this repo), this bot handles the technical timing layer on top of that fundamental filter.

### [Join the Telegram channel to receive live signals](https://t.me/dipmafia)

---

## How It Works

```
┌─────────────────────────────────────┐
│         stocks.txt (watchlist)      │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│     yfinance, 1yr daily OHLCV     │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Bollinger Bands (200-period, 2σ)  │
│  ┌─────┐  ┌───────┐  ┌──────┐     │
│  │ Buy │  │ Watch │  │ Hold │     │
│  └──┬──┘  └───┬───┘  └──┬───┘     │
│     │         │         │ filtered │
│     ▼         ▼         ✗ out     │
│  ┌─────────────────┐              │
│  │   MACD Filter   │              │
│  │  Standard 12/26 │              │
│  │  Impulse MACD   │              │
│  └────────┬────────┘              │
└───────────┼────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│  Sentiment (Hold/Wait for Buy %)   │
│  Bullish · Neutral · Cautious ·    │
│  Bearish                           │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│     Telegram (if signals changed)  │
└─────────────────────────────────────┘
```

### Signal Logic

| Stage | Indicator | Signal | Meaning |
|---|---|---|---|
| **Gate** | Bollinger Bands (200, 2σ) | Buy | Price at or below lower band today |
| | | Watch | Touched lower band in last 60 days |
| | | Hold | No recent lower band interaction, **filtered out** |
| | | _midline gate_ | **Backtest only**: Buy/Watch must also be below the 200-SMA midline (`BUY_REQUIRE_BELOW_MID`). The live bot sends all Buy/Watch (`REQUIRE_CLOSE_BELOW_MIDLINE=False`) |
| **Signal** | Standard MACD (12/26/9) | Buy/Sell | Crossover on current bar |
| | Impulse MACD (LazyBear) | Buy/Sell | SMMA + ZLEMA crossover on current bar |
| | Both | Hold / Wait for Buy | Between crossovers |
| **Context** | NIFTY 50 + Midcap 100 | % move, % from ATH | Market-wide context |
| **Sentiment** | Hold vs Wait ratio | Bullish/Neutral/Cautious/Bearish | Aggregate market mood |

### Deduplication

Signals are hashed each run. If unchanged from the previous run, Telegram notifications are skipped, no spam during sideways markets.

## Sample Output

```
📊 Signal Alert | 19 April, 03:15PM
🔻 NIFTY 50: -3.42% (from ATH: -18.50%)
🔻 NIFTY Midcap 100: -4.10% (from ATH: -25.30%)
🔴 Sentiment: Bearish

🔵 STANDARD MACD:
⏱️ 1d
🟢 SUZLON      ₹38.50
🟢 GRSE        ₹1850.00

📈 Summary:
🟣 Wait for Buy: 25/34 (73.5%)
🟡 Hold: 7/34 (20.6%)

🟠 IMPULSE MACD (LazyBear):
⏱️ 1d Impulse MACD
🟢 SUZLON      ₹38.50
🟢 GRSE        ₹1850.00
🟢 AIIL        ₹320.00

📈 Summary:
🟣 Wait for Buy: 28/34 (82.4%)
🟡 Hold: 4/34 (11.8%)
```

## Quick Start

### 1. Fork & configure secrets

Go to **Settings > Secrets and variables > Actions** and add:

| Secret | Value |
|---|---|
| `TELEGRAM_TOKEN` | Your bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_IDS` | Comma-separated chat IDs |

### 2. Edit your watchlist

`stocks.txt`, one NSE symbol per line, without `.NS`:
```
RELIANCE
TCS
INFY
```

### 3. Done

The bot runs automatically:
- **Weekdays**: every hour, 9:15 AM – 3:15 PM IST (market hours)
- **Weekends**: once at 10:15 AM IST

Or trigger manually: **Actions tab → Run workflow**

### Local run

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="your_token"
export TELEGRAM_CHAT_IDS="id1,id2"
python bot.py
```

## Backtest

A portfolio-level backtest validates the timing strategy against plain SIP investing. All stocks in `stocks.txt` share a single monthly budget, the point of 60+ stocks is that something is always dipping, keeping cash deployed.

### Run it

```bash
pip install matplotlib scipy  # one-time, in addition to requirements.txt
python3 analysis/backtest.py  # run from the repo root
```

Generates 8 charts in a dated run subfolder under `backtest_output/` + console summary.

### Latest Results (73 stocks, 2010–2026)

> Run as of 2026-06-02 (from the recalculated six7 almanac's live-watchlist run, `backtest_output/six7/stocks_current/`) against the 75-symbol `stocks.txt` (73 had enough history for the 200-bar Bollinger warmup), 60-bar Bollinger watch window, **midline buy gate** (matches the live bot), and the **V4 idle-cash fallback** (deploy after 21 idle days across any watchlist stock below its 200-SMA, force-deploy if none - see `notes/STRATEGY_COMPARISON.md`).

```
════════════════════════════════════════════════════════════════════════════════════════════════════
  INVESTMENT ASSUMPTIONS
────────────────────────────────────────────────────────────────────────────────────────────────────
  Period:             2010-01-04 → 2026-06-02 (16.4 years)
  Starting salary:    ₹22,000/month → ₹101,089/month (10% annual hike)
  Monthly SIP:        ₹5,500 → ₹25,272 (25% of salary)
  Total invested:     ₹25.2L (inflation-adjusted: ₹9.7L in 2010 rupees)
  Inflation (6%/yr):  ₹1 in 2010 = ₹2.6 today

════════════════════════════════════════════════════════════════════════════════════════════════════
  RESULTS - 73 stocks, ₹25.2L invested
════════════════════════════════════════════════════════════════════════════════════════════════════
                            Your Strategy (Timed HODL)     SIP on Your Stocks       Timed Entry+Exit        SIP on NIFTY 50
  ───────────────────────────────────────────────────────────────────────────────────────────────
  Final Value                              ₹199.0L                ₹214.0L                 ₹34.2L                 ₹50.9L
  Inflation-Adj Value                       ₹76.5L                 ₹82.3L                 ₹13.1L                 ₹19.6L
  Wealth Multiple                             7.9x                   8.5x                   1.4x                   2.0x
  Real Multiple (infl-adj)                    3.0x                   3.3x                   0.5x                   0.8x
  XIRR                                       26.8%                  27.6%                   4.7%                  10.3%
  Real XIRR (minus 6% infl)                  20.8%                  21.6%                  -1.3%                   4.3%
  Sharpe                                      1.32                   1.31                   0.93                   1.12
  Sortino                                     3.17                   3.06                   2.02                   3.36
  Max Drawdown                              -50.8%                 -51.4%                 -68.2%                 -37.3%
  Max DD Duration                         710 days               709 days               851 days               183 days
  Volatility                                 38.8%                  39.4%                  46.8%                  37.6%

  Buy signals fired on 183 days across 69/73 stocks
  Cash drag (Your Strategy): 1.2%   ·   longest idle: 21 trading days (~1 month)   ·   542 fallback buys
```

### Key Findings

| Metric | Your Strategy | SIP (same stocks) | NIFTY 50 SIP |
|---|---|---|---|
| Final Value | ₹199L | ₹214L | ₹51L |
| Inflation-Adjusted | ₹76L | ₹82L | ₹20L |
| XIRR | 26.8% | 27.6% | 10.3% |
| Real XIRR (−6% inflation) | **20.8%** | 21.6% | 4.3% |
| Sharpe | **1.32** | 1.31 | 1.12 |
| Sortino | **3.17** | 3.06 | 3.36 |
| Max Drawdown | **-51%** | -51% | -37% |
| Volatility | 38.8% | 39.4% | 37.6% |

- **Both strategies crush NIFTY 50 by ~4x**, stock picking matters more than timing
- **Backtest is gated, the live bot is not** (by design) - `BUY_REQUIRE_BELOW_MID` adds the close-below-200-SMA rule to the backtest (better 1/3/5y returns, ~neutral over 16y); the Telegram bot stays ungated so all Buy/Watch alerts come through
- **Cash drag down to 1.2%** (from 5.7%) with the V4 fallback, longest idle stretch cut from 214 to 21 trading days
- **Real returns beat inflation easily**, 20.8% real XIRR for Timed HODL vs 4.3% for NIFTY 50
- **Entry+Exit is terrible**, selling on MACD Sell destroys compounding

### Returns by horizon (live watchlist)

The summary table above is the full ~16-year run. Recent trailing-window XIRR for the same `stocks.txt`:

| Horizon | Timed HODL | SIP (same stocks) | NIFTY 50 |
|---|---|---|---|
| 1 year | **17.0%** | 1.1% | -4.6% |
| 3 years | 9.7% | 21.3% | 4.2% |
| 5 years | 30.0% | 36.4% | 7.5% |
| 10 years | 35.8% | 35.1% | 10.9% |
| Full (~16y) | 26.3% | 27.0% | 10.9% |

> Every horizon is a fresh windowed sim on the salary model (₹22k/mo from 2010, +10%/yr, 25% invested), calendar-anchored then restricted to the window, so Full reproduces the headline above. Timing beats plain SIP at 1y and 10y and protects in the down year (deploying into the dip while NIFTY fell ~5%); it trails on raw return at 3y/5y, where a relentless SIP rode the rally without waiting for weakness.

### Charts

| Chart | What it shows |
|---|---|
| `1_equity_curves.png` | All strategies + NIFTY 50 on one chart |
| `2_drawdowns.png` | How deep each strategy fell from peak |
| `3_cash_utilization.png` | % of money actually invested vs cash |
| `4_regime_returns.png` | Returns during bull, bear, sideways, recovery |
| `5_rolling_alpha.png` | When your strategy beats/loses to SIP |
| `6_buy_distribution.png` | Which stocks got bought most often |
| `7_buy_timeline.png` | When buys happened over time |
| `8_summary_table.png` | Full metrics table with best values highlighted |

![Equity Curves](backtest_output/six7/stocks_current/1_equity_curves.png)
![Regime Returns](backtest_output/six7/stocks_current/4_regime_returns.png)
![Summary Table](backtest_output/six7/stocks_current/8_summary_table.png)

## Architecture

```
├── bot.py                 # live entry: orchestrator, Telegram sender, sentiment
├── macd_signals.py        # Standard + Impulse MACD (standalone capable)
├── bollinger_signals.py   # 200-period Bollinger Bands (standalone capable)
├── stocks.txt             # watchlist
├── analysis/              # research/backtest tooling (run from the repo root)
│   ├── backtest.py        # portfolio backtest - Timed HODL (V4 fallback + midline + bb-60)
│   ├── horizon_compare.py # 1y/3y/5y/10y/Full horizon grids for the dashboard
│   ├── portfolio_view.py  # emits docs/strat_data.js (portfolio NAV + backtest + iterations)
│   ├── backtest_six7.py   # six7 almanac: lists × horizons (same Timed HODL strategy)
│   ├── build_web.py       # assembles docs/data.js for the Screens section
│   └── run_paths.py       # backtest_output/ layout helper
├── pine/                  # TradingView ports (indicator + strategy)
├── notes/                 # STRATEGY_COMPARISON.md, context.md, specs/
├── tests/                 # test_bb_position.py
├── backtest_output/       # dated run subfolders + six7/ almanac
├── docs/                  # GitHub Pages: index.html (unified dashboard) + data.js + strat_data.js
├── requirements.txt       # yfinance, requests
└── .github/workflows/
    └── dip-mafia.yml      # GitHub Actions (cron + cache); runs `python bot.py`
```

Each signal module can run standalone for quick analysis:
```bash
python bollinger_signals.py   # Bollinger only
python macd_signals.py        # MACD only
```

## Configuration

| Parameter | File | Default |
|---|---|---|
| BB period | `bollinger_signals.py` | 200 |
| BB std dev | `bollinger_signals.py` | 2 |
| BB watch window | `bollinger_signals.py` | 60 bars |
| MACD fast/slow/signal | `macd_signals.py` | 12/26/9 |
| Impulse MA length | `macd_signals.py` | 34 |
| Impulse signal length | `macd_signals.py` | 9 |

## Disclaimer

This is not financial advice. The bot generates signals for educational and research purposes. Always do your own due diligence before making investment decisions.

# Dip Mafia: Crash-Buy Signals for Indian Equities (NSE)

**Dip Mafia** (formerly HODL-bot) is an automated **algo-trading signal system** that identifies deeply undervalued stocks during market crashes using **200-period Bollinger Bands** and **dual MACD crossovers**, then delivers actionable buy signals with market sentiment to Telegram, fully automated via GitHub Actions.

> **Philosophy**: Buy the crash, hold forever. This bot watches 70+ fundamentally screened NSE stocks and alerts when they hit statistically extreme lows with confirmed momentum reversal. No day-trading, no exits, just long entries at high-conviction dips.
>
> **We never sell.** Sell / red signals are **indications only**: they flag technical weakness for awareness; Dip Mafia does not execute exits. The strategy is buy dips and HODL.
>
> The watchlist is the union of two lists: `six7.txt` (the six7 Top 50, curated by a separate fundamental scorer) and `holdings.txt` (the stocks already held). Signals fire on both, and each Telegram line is tagged `⭐` Top 50 or `💼` your holding, so a position you hold keeps getting signals even after the Top 50 rotates. This bot handles the technical timing layer on top of that fundamental filter.

### [Join the Telegram channel to receive live signals](https://t.me/dipmafia)

---

## How It Works

```
┌─────────────────────────────────────┐
│  six7.txt ∪ holdings.txt (watchlist) │
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

The bot signals on the union of two files, one NSE symbol per line, without `.NS`:

- `six7.txt` - the Top 50 watchlist (overwritten by the external six7 mirror)
- `holdings.txt` - stocks you already hold (so they keep getting signals)

```
RELIANCE
TCS
INFY
```

`stocks.txt` is a **derived** file (the `six7.txt` ∪ `holdings.txt` union) used only by the backtest/dashboard tooling - regenerate it with `python3 watchlist.py` after editing either list.

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

### Latest Results (50 stocks, 2010–2026)

> Run as of 2026-06-03 (from the recalculated six7 almanac's live-watchlist run, `backtest_output/six7/stocks_current/`) against the 50-symbol `stocks.txt` - the **six7 Top 50** (highest 50 by 0-10 Fundamental Score), adopted 2026-06-15 (see `notes/2026-06-15-portfolio-council-verdict.md`); 47 had enough history for the 200-bar Bollinger warmup. 60-bar Bollinger watch window, **midline buy gate** (matches the live bot), and the **V4 idle-cash fallback** (deploy after 21 idle days across any watchlist stock below its 200-SMA, force-deploy if none - see `notes/STRATEGY_COMPARISON.md`).

```
════════════════════════════════════════════════════════════════════════════════════════════════════
  INVESTMENT ASSUMPTIONS
────────────────────────────────────────────────────────────────────────────────────────────────────
  Period:             2010-01-04 → 2026-06-03 (16.4 years)
  Starting salary:    ₹22,000/month → ₹101,089/month (10% annual hike)
  Monthly SIP:        ₹5,500 → ₹25,272 (25% of salary)
  Total invested:     ₹25.2L (inflation-adjusted: ₹9.7L in 2010 rupees)
  Inflation (6%/yr):  ₹1 in 2010 = ₹2.6 today

════════════════════════════════════════════════════════════════════════════════════════════════════
  RESULTS - 47 stocks, ₹25.2L invested
════════════════════════════════════════════════════════════════════════════════════════════════════
                            Your Strategy (Timed HODL)     SIP on Your Stocks       Timed Entry+Exit        SIP on NIFTY 50
  ───────────────────────────────────────────────────────────────────────────────────────────────
  Final Value                              ₹268.7L                ₹261.2L                 ₹45.4L                 ₹50.9L
  Inflation-Adj Value                      ₹103.4L                ₹100.5L                 ₹17.5L                 ₹19.6L
  Wealth Multiple                            10.7x                  10.4x                   1.8x                   2.0x
  Real Multiple (infl-adj)                    4.1x                   4.0x                   0.7x                   0.8x
  XIRR                                       30.1%                  29.8%                   8.7%                  10.3%
  Real XIRR (minus 6% infl)                  24.1%                  23.8%                   2.7%                   4.3%
  Sharpe                                      1.39                   1.37                   0.97                   1.12
  Sortino                                     3.31                   3.18                   2.08                   3.36
  Max Drawdown                              -40.1%                 -43.5%                 -56.2%                 -37.3%
  Max DD Duration                         480 days               283 days               519 days               183 days
  Volatility                                 37.8%                  38.5%                  46.2%                  37.6%

  Buy signals fired on 182 days across 45/47 stocks
  Cash drag (Your Strategy): 1.4%   ·   longest idle: 21 trading days (~1 month)   ·   639 fallback buys
```

### Key Findings

| Metric | Your Strategy | SIP (same stocks) | NIFTY 50 SIP |
|---|---|---|---|
| Final Value | ₹269L | ₹261L | ₹51L |
| Inflation-Adjusted | ₹103L | ₹101L | ₹20L |
| XIRR | **30.1%** | 29.8% | 10.3% |
| Real XIRR (−6% inflation) | **24.1%** | 23.8% | 4.3% |
| Sharpe | **1.39** | 1.37 | 1.12 |
| Sortino | **3.31** | 3.18 | 3.36 |
| Max Drawdown | **-40%** | -44% | -37% |
| Volatility | 37.8% | 38.5% | 37.6% |

- **Both strategies crush NIFTY 50 by ~5x**, stock picking matters more than timing - and the six7 Top 50 lifts the book's quality (every name is a Strong Buy) versus the prior mixed 75-name watchlist
- **Timed HODL now edges plain SIP at every horizon** (and across the full run), where the older watchlist trailed SIP at 3y/5y - a tighter, higher-quality universe gives the dip-timing more to work with
- **Lower drawdown too** - max drawdown improved from -51% to -40% versus the 75-name book
- **Backtest is gated, the live bot is not** (by design) - `BUY_REQUIRE_BELOW_MID` adds the close-below-200-SMA rule to the backtest (better 1/3/5y returns, ~neutral over 16y); the Telegram bot stays ungated so all Buy/Watch alerts come through
- **Cash drag stays low at 1.4%**, longest idle stretch 21 trading days, with the V4 fallback deploying across the Top 50 below-midline pool
- **Real returns beat inflation easily**, 24.1% real XIRR for Timed HODL vs 4.3% for NIFTY 50
- **Entry+Exit is terrible**, selling on MACD Sell destroys compounding

> The backtest is current-screen hindsight (the Top 50 is today's fundamental screen run backward - survivorship/look-ahead biased), so treat the levels as relative, not predictive. See the council verdict note for the honest forward expectation.

### Returns by horizon (live watchlist)

The summary table above is the full ~16-year run. Recent trailing-window XIRR for the same `stocks.txt`:

| Horizon | Timed HODL | SIP (same stocks) | NIFTY 50 |
|---|---|---|---|
| 1 year | **40.2%** | 23.4% | -10.2% |
| 3 years | **34.3%** | 33.2% | 1.4% |
| 5 years | **44.0%** | 42.8% | 5.9% |
| 10 years | **40.2%** | 38.9% | 9.8% |
| Full (~16y) | **30.1%** | 29.8% | 10.3% |

> Every horizon is a fresh windowed sim on the salary model (₹22k/mo from 2010, +10%/yr, 25% invested), calendar-anchored then restricted to the window, so Full reproduces the headline above. With the Top 50 watchlist, Timed HODL beats plain SIP at every horizon, most strongly in the down year (1y: NIFTY -10%, Timed +40% deploying into the dip).

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
├── watchlist.py           # two-list loader; regenerates stocks.txt
├── six7.txt               # source list: six7 Top 50 (mirror target)
├── holdings.txt           # source list: stocks you already hold
├── stocks.txt             # DERIVED union (six7 ∪ holdings); analysis input only
├── analysis/              # research/backtest tooling (run from the repo root)
│   ├── backtest.py        # portfolio backtest - Timed HODL (V4 fallback + midline + bb-60)
│   ├── horizon_compare.py # 1y/3y/5y/10y/Full horizon grids for the dashboard
│   ├── portfolio_view.py  # emits docs/strat_data.js (per-horizon portfolio books + backtest + iterations)
│   ├── backtest_six7.py   # six7 almanac: lists × horizons (same Timed HODL strategy)
│   ├── build_web.py       # assembles docs/data.js for the Screens section
│   └── run_paths.py       # backtest_output/ layout helper
├── pine/                  # TradingView ports (indicator + strategy)
├── notes/                 # STRATEGY_COMPARISON.md, context.md, specs/
├── tests/                 # test_bb_position.py, test_watchlist.py
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

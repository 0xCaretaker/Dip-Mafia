# Dip Mafia: Crash-Buy Signals for Indian Equities (NSE)

**Dip Mafia** (formerly HODL-bot) is an automated **algo-trading signal system** that identifies deeply undervalued stocks during market crashes using **200-period Bollinger Bands** and **dual MACD crossovers**, then delivers actionable buy signals with market sentiment to Telegram and Discord, fully automated via GitHub Actions.

> **Philosophy**: Buy the crash, hold forever. This bot watches 150+ NSE stocks (the six7 watchlist ∪ your real holdings) and alerts when they hit statistically extreme lows with confirmed momentum reversal. No day-trading, no exits, just long entries at high-conviction dips.
>
> **We never sell.** Sell / red signals are **indications only**: they flag technical weakness for awareness; Dip Mafia does not execute exits. The strategy is buy dips and HODL.
>
> The watchlist is the union of two lists: `six7.txt` (the six7 watchlist — the Top N by Fundamental Score, curated by a separate fundamental scorer) and `holdings.txt` (the stocks already held). Signals fire on both, and each Telegram line is tagged `⭐` six7 or `💼` your holding, so a position you hold keeps getting signals even after the six7 list rotates. six7 also mirrors `six7_scores.json` here, so **every row carries its 0-10 Fund. Score** — Verdict and Cheap Bargains, `⭐` and `💼` alike — which is what picks between two buys on the same day. This bot handles the technical timing layer on top of that fundamental filter.

### Join to receive live signals:
- 📨 [Telegram channel](https://t.me/dipmafia)
- 💬 [Discord server](https://discord.gg/qmYPPjPdGA)

---

## How It Works

```mermaid
flowchart TD
    A(["📋 <b>Watchlist</b><br/>six7.txt ∪ holdings.txt"])
    B["📥 <b>Data</b><br/>yfinance · 1yr daily OHLCV"]
    C{"🎚️ <b>Gate · Bollinger Bands</b><br/>200-period · 2σ"}
    D["📊 <b>Signal · Dual MACD</b><br/>Standard 12/26/9 · Impulse (LazyBear)"]
    V{{"🎯 <b>VERDICT</b> · Bollinger + Impulse<br/><i>the only line a beginner acts on</i>"}}
    N["💰 <b>Cheap Bargains</b> · idle-cash targets<br/>six7 names 15%+ below the 200-SMA midline<br/><i>where spare cash gets deployed</i>"]
    T["📣 <b>Delivery</b><br/>Telegram + Discord"]
    X(["🗑️ dropped"])

    A --> B --> C
    A -.->|"below midline"| N
    C -->|"Buy / Watch ✅"| D
    C -.->|"Hold ✗"| X
    D --> V --> T
    N --> T

    classDef gate fill:#1e293b,stroke:#64748b,color:#e2e8f0;
    classDef verdict fill:#16a34a,stroke:#15803d,color:#ffffff;
    classDef cash fill:#78350f,stroke:#b45309,color:#fed7aa;
    classDef drop fill:#450a0a,stroke:#7f1d1d,color:#fca5a5;
    class C gate;
    class V verdict;
    class N cash;
    class X drop;
```

### Signal Logic

| Stage | Indicator | Signal | Meaning |
|---|---|---|---|
| **Gate** | Bollinger Bands (200, 2σ) | Buy | Price at or below lower band today |
| | | Watch | Touched lower band in last 60 days |
| | | Hold | No recent lower band interaction, **filtered out** |
| | | _midline gate_ | Buy/Watch must also be below the 200-SMA midline. Live bot: `REQUIRE_CLOSE_BELOW_MIDLINE=True` (matches the backtest's `BUY_REQUIRE_BELOW_MID`). Set False to revert to the looser awareness view. |
| **Signal** | Standard MACD (12/26/9) | Buy/Sell | Crossover on current bar |
| | Impulse MACD (LazyBear) | Buy/Sell | SMMA + ZLEMA crossover on current bar |
| | Both | Hold / Wait for Buy | Between crossovers |
| **Context** | NIFTY 50 + Midcap 100 | % move, % from ATH | Market-wide context |
| **Sentiment** | Hold vs Wait ratio | Bullish/Neutral/Cautious/Bearish | Aggregate market mood |
| **Deploy** | Cheap Bargains (six7 vs 200-SMA) | idle-cash targets | six7 names trading more than 15% below the 200-SMA midline (`MIN_BARGAIN_DISCOUNT_PCT`), cheapest first, with `⚡` on a fresh Impulse MACD cross. This is **where spare cash goes**: cash left idle beyond ~21 days is spread equally across these below-midline names (capped 15% per name). Rendered as the `📉 Cheap Bargains` section. |

### Delivery cadence

Two trigger paths post the same full message to Telegram and Discord:

- **Scheduled cron** (`dip-mafia.yml`) - 4 runs/day on weekdays (~08:33 / 10:33 / 12:33 / 14:33 IST) plus a weekend summary on **both Saturday and Sunday** (~10:33 IST). (GitHub cron is best-effort, so these are targets, not guarantees; spreading the runs keeps coverage even if one is delayed or dropped.)
- **Scan-triggered** - the external six7 scan dispatches `dip-mafia.yml` on *every* scan, so a scan always posts once.

**Every run recomputes and posts fresh.** It re-reads current prices and rebuilds the whole message each time, so the prices, sentiment, and the mid-line / Cheap Bargains read are always current - there is no reuse cache (it was retired so intraday drift never shows stale data). A watchlist source-list change (`six7.txt` from the mirror, or a hand-synced `holdings.txt`) only rebuilds the derived `stocks.txt` via `regen-stocks.yml` - it **no longer posts directly**; the next scan or cron run covers it, which avoids double-posting. The `reuse_if_unchanged` workflow input still exists but is now ignored - a no-op kept only so the six7 dispatch (which still passes it) doesn't error.

## Sample Output

```
🩸 DIP MAFIA
19 Apr · 3:15 PM IST

🔻 NIFTY 50
Today -3.42%  ·  ATH -18.5%
🔻 MIDCAP 100
Today -4.10%  ·  ATH -25.3%

🔴 Sentiment: Bearish

🎯 Verdict (Boll + iMACD)
🟢 ⭐ ⏬ SUZLON  ₹38.50 ·  9.4
🟢 💼 🔽 AETHER  ₹812.30 ·  7.2

🟣 Wait for Buy · 30/34 · 88.2%
💼 KITEX  ·  5.8
⭐ GRSE   · 10.0

🟡 Hold · 4/34 · 11.8%
💼 AHLUCONT ·  6.0
⭐ MAYURUNIQ · 10.0
⭐ RSYSTEMS  · 10.0
⭐ VEDL      ·  8.9

──────────────────────────
📉 Cheap Bargains (Top 100 · 15%+ below 200-SMA)
💰 cash in hand? grab these undervalued now
⏬ SUZLON  -12.4% ·  9.4 ⚡
🔽 GRSE     -3.1% · 10.0
🔽 KRBL     -1.8% ·  6.2

──────────────────────────
▶️ how to act
🟢 buy the 🎯 Verdict picks
💰 spare cash? spread across 📉 Cheap Bargains

ℹ️ legends
🟢 buy · 🔴 sell
⚡ iMACD turning up
⭐ Top 100 · 💼 your holding
· number = six7 Fund. Score 0-10
⏬ deep dip · 🔽 undervalued
🔼 above avg · ⏫ overvalued

Dip Mafia never sells, red just flags weakness · we only buy dips & HODL
```

### New here? How to read it - and what to do

If the indicators, sentiment, and summary lines don't make sense, **skip them.** Two sections tell you what to do, and the `▶️ how to act` block at the bottom of every message sums them up:

**🎯 Verdict - what to buy.** The bot's highest-conviction call: a stock that's both deeply dipped (Bollinger) *and* turning up (Impulse MACD).
- **🟢 buy in the Verdict = the only line a beginner needs to act on.** That's "Dip Mafia thinks this is a good dip to buy." The example above is telling you to buy `SUZLON`.
- **`🚫 no buys today` under Verdict? Do nothing.** No action that run - that's normal, and most runs look like this.

**📉 Cheap Bargains - where idle cash goes.** six7 watchlist names trading **more than 15% below** their 200-day average (the 200-SMA midline), cheapest first. The floor (`MIN_BARGAIN_DISCOUNT_PCT` in `bot.py`) exists because the Top-100 widening pushed this section to 36 rows reaching -2.1%; a name 2% under its average is noise, and it buried the genuine -30% names. If you have cash sitting idle, **this is where the strategy parks it** - spread it across these below-midline names rather than letting it rot. A `⚡` means momentum is already turning up on that name. (Same rule the backtest uses: cash idle beyond ~21 days is deployed equally across below-midline names, capped 15% per name.)

**🔴 red is never a sell.** Dip Mafia never sells. Red just flags technical weakness for awareness. You only ever buy dips and HODL.

The `🟡 Sentiment` line up top is the only extra context in the message - safe to skip. The raw per-stock MACD and Impulse MACD lists (the noisier, ungated reads) are **not** in the notification anymore; they live in full detail in the GitHub Action run log, alongside a `BOLLINGER FILTER PASS` list of exactly which stocks feed the Verdict.

## Quick Start

### 1. Fork & configure secrets

Go to **Settings > Secrets and variables > Actions** and add:

| Secret | Value |
|---|---|
| `TELEGRAM_TOKEN` | Your bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_IDS` | Comma-separated chat IDs |
| `DISCORD_WEBHOOK_URL` | _Optional_. Discord channel webhook (Server → Integrations → Webhooks → New Webhook → Copy URL). Posts mirror the Telegram payload with an `@here` ping. |

### 2. Edit your watchlist

The bot signals on the union of two files, one NSE symbol per line, without `.NS`:

- `six7.txt` - the six7 watchlist, Top N by Fundamental Score (overwritten by the external six7 mirror; widened 50 -> 100 on 2026-08-28)
- `holdings.txt` - stocks you already hold (so they keep getting signals)

```
RELIANCE
TCS
INFY
```

`stocks.txt` is a **derived** file (the `six7.txt` ∪ `holdings.txt` union) used only by the backtest/dashboard tooling - regenerate it with `python3 watchlist.py` after editing either list.

### 3. Done

The bot runs automatically:
- **Weekdays**: 4 runs/day, ~08:33 / 10:33 / 12:33 / 14:33 IST (cron targets - GitHub may delay them)
- **Weekends**: one summary, ~10:33 IST

The external six7 scan also dispatches a run after each scan (re-sending the cached post when the watchlist and trading date are unchanged). Or trigger manually: **Actions tab → Run workflow**

### Local run

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="your_token"
export TELEGRAM_CHAT_IDS="id1,id2"
python bot.py
```

## Backtest

A portfolio-level backtest validates the timing strategy against plain SIP investing. All stocks in `stocks.txt` share a single monthly budget - the point of 50+ stocks is that something is always dipping, keeping cash deployed.

### Run it

```bash
pip install matplotlib scipy  # one-time, in addition to requirements.txt
python3 analysis/backtest.py  # run from the repo root
```

Generates 8 charts in a dated run subfolder under `backtest_output/` + console summary.

### Latest Results (six7 Top 100, 2010–2026)

Live almanac (every six7 list × 1y/3y/5y/10y/Full, plus the strat dashboard): **https://0xcaretaker.github.io/Dip-Mafia/**

> Run as of 2026-10-06 against `six7.txt` alone: the **six7 Top 100** as of the 2026-10-07 scan (6+ criteria with D/E ≤ 0.6, then market cap > ₹2,000cr and PEG < 2.0, not backfilled, so 88 names). 75 of 88 have enough history for the 200-bar Bollinger warmup. 60-bar watch window, **midline buy gate** (`REQUIRE_CLOSE_BELOW_MIDLINE = True` in `bot.py`, `BUY_REQUIRE_BELOW_MID = True` in `backtest.py`), and the **V4 idle-cash fallback** (deploy after 21 idle days across any watchlist stock below its 200-SMA, force-deploy if none; see `notes/STRATEGY_COMPARISON.md`). Source: the almanac's `top100` list, `backtest_output/six7/top100/`. The live bot signals on `six7.txt ∪ holdings.txt`; that 150-symbol union is the strat run `backtest_output/20261006_150sym_bb60/` (Timed 26.6% vs SIP 28.5% XIRR). The headline isolates the six7 screen from the personal SME/illiquid holdings.

```
════════════════════════════════════════════════════════════════════════════════════════════════════
  INVESTMENT ASSUMPTIONS
────────────────────────────────────────────────────────────────────────────────────────────────────
  Period:             2010-01-04 → 2026-10-06 (16.8 years)
  Starting salary:    ₹22,000/month → ₹101,089/month (10% annual hike)
  Monthly SIP:        ₹5,500 → ₹25,272 (25% of salary)
  Total invested:     ₹26.3L
  Inflation (6%/yr):  ₹1 in 2010 = ₹2.65 today

════════════════════════════════════════════════════════════════════════════════════════════════════
  RESULTS - 75 stocks, ₹26.3L invested
════════════════════════════════════════════════════════════════════════════════════════════════════
                            Your Strategy (Timed HODL)     SIP on Your Stocks       Timed Entry+Exit        SIP on NIFTY 50
  ───────────────────────────────────────────────────────────────────────────────────────────────
  Final Value                              ₹272.3L                ₹291.6L                ₹154.1L                 ₹50.3L
  Inflation-Adj Value                      ₹102.8L                ₹110.0L                 ₹58.1L                 ₹19.0L
  Wealth Multiple                            10.4x                  11.1x                   5.9x                   1.9x
  XIRR                                       29.3%                  30.0%                  22.9%                   9.4%
  Real XIRR (minus 6% infl)                  23.3%                  24.0%                  16.9%                   3.4%
  Sharpe                                      1.00                   1.03                   0.29                   0.28
  Sortino                                     1.23                   1.26                   0.49                   0.36
  Max Drawdown                              -53.5%                 -54.5%                 -78.1%                 -38.4%
  Max DD Duration                         770 days               769 days              2169 days               727 days
  Volatility                                 19.5%                  19.9%                  32.8%                  16.4%

  Buy signals fired on 188 days across 68/75 stocks
  Cash drag (Your Strategy): 1.3%   ·   longest idle: 21 trading days (~1 month)   ·   838 fallback buys
```

### Key Findings

| Metric | Your Strategy | SIP (same stocks) | NIFTY 50 SIP |
|---|---|---|---|
| Final Value | ₹272L | ₹292L | ₹50L |
| Inflation-Adjusted | ₹103L | ₹110L | ₹19L |
| XIRR | 29.3% | **30.0%** | 9.4% |
| Real XIRR (−6% inflation) | 23.3% | **24.0%** | 3.4% |
| Sharpe | 1.00 | **1.03** | 0.28 |
| Max Drawdown | **-53.5%** | -54.5% | -38.4% |
| Volatility | 19.5% | 19.9% | 16.4% |

- **Both strategies beat NIFTY 50 by ~3x on XIRR** (29-30% vs 9.4%). Stock picking matters far more than timing.
- **Timed HODL no longer beats SIP over the full run** (29.3% vs 30.0%). It wins the 5y and 10y windows by under a point and loses 1y/3y. The new screen is lower-beta (D/E ≤ 0.6), so there are fewer deep dips for the BB/MACD gate to buy. On the 150-symbol live union, SIP leads at every horizon.
- **The new screen trades return for drawdown.** Run over the same window as the June screen (to 2026-06-03), the new Top 100 gives 28.8% Full XIRR vs 32.1%, with max drawdown -53.5% vs -56.8% (5y: -21.7% vs -26.5%). Details: [`notes/2026-10-07-backtest-rerun.md`](notes/2026-10-07-backtest-rerun.md).
- **The market-cap and PEG gates do work.** The ungated screens (Strong Buy, 6+) made ≈0% over the same 1y window. The gated Top 100 made 17.6%.
- **Cash drag is low at 1.3%**: longest idle stretch 21 trading days, with the V4 fallback deploying when signals dry up.
- **Entry+Exit is still worse than holding**: 22.9% XIRR vs Timed HODL's 29.3%, with a -78% drawdown. Selling on MACD Sell destroys compounding.

> The backtest is current-screen hindsight (today's Top 100 run backward, so survivorship and look-ahead biased). Treat the levels as relative, not predictive. Sharpe/Sortino are computed on a unit NAV since 2026-06-21, so they are not comparable with the pre-June README figures.

### Returns by horizon (six7.txt alone)

The summary table above is the full ~16.8-year run. Trailing-window XIRR for the same 88-symbol list (75 with data):

| Horizon | Timed HODL | SIP (same stocks) | NIFTY 50 |
|---|---|---|---|
| 1 year | 26.9% | **33.4%** | -13.2% |
| 3 years | 24.3% | **26.6%** | -2.2% |
| 5 years | **39.4%** | 38.6% | 3.5% |
| 10 years | **37.4%** | 37.1% | 8.4% |
| Full (~16.8y) | 29.3% | **30.0%** | 9.4% |

> Full and 10y use the salary model (₹22k/mo from 2010, +10%/yr, 25% invested); 5y/3y/1y use a flat ₹20,000/mo. Every window ends 2026-10-06. In the 1y window NIFTY fell 13% and SIP outran Timed: the midline gate sat out the rebound, while SIP kept deploying every month.

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

![Equity Curves](backtest_output/six7/top100/1_equity_curves.png)
![Regime Returns](backtest_output/six7/top100/4_regime_returns.png)
![Summary Table](backtest_output/six7/top100/8_summary_table.png)

## Architecture

```
├── bot.py                 # live entry: orchestrator, Telegram sender, sentiment
├── macd_signals.py        # Standard + Impulse MACD (standalone capable)
├── bollinger_signals.py   # 200-period Bollinger Bands (standalone capable)
├── watchlist.py           # two-list loader; regenerates stocks.txt
├── six7.txt               # source list: six7 watchlist, Top N (mirror target)
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
├── backtest_output/       # dated run subfolders + six7/ almanac (+ six7_<date>/ archives)
├── docs/                  # GitHub Pages: index.html (unified dashboard) + data.js + strat_data.js
├── requirements.txt       # yfinance, requests
└── .github/workflows/
    ├── dip-mafia.yml      # cron + scan-dispatch; runs `python bot.py` (with last-post cache)
    └── regen-stocks.yml   # rebuilds derived stocks.txt when a source list changes (no posting)
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

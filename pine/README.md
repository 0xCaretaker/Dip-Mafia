# Pine Script ports (TradingView)

TradingView ports of the Dip Mafia signal layer. These are **standalone** - no
Python imports them; paste them into the TradingView Pine Editor on a **daily**
NSE chart (needs ~230+ daily bars for the 200-bar Bollinger warmup).

| File | Type | What it does |
|------|------|--------------|
| `dip_mafia.pine` | indicator | BB(200, 2σ) `{Buy, Watch}` gate + Standard MACD (12/26/9) and Impulse MACD (LazyBear variant). Plots a **BUY** marker only when a MACD bullish cross fires inside the Bollinger universe. Sell/weakness crossovers are info-only, never traded. |
| `dip_mafia_strategy.pine` | strategy | Same gate/signals wired into `strategy()`. Long-only, deploys a **configurable tranche** per gated buy (default = % of equity, so a single symbol stays invested instead of parking ~99% in idle cash) and **never exits in-sample** (HODL). On the **last bar only** it does a report-only `strategy.close_all()` mark-to-market so TradingView's native Net Profit / CAGR / % profitable populate instead of reading ~0 (a never-sell strategy otherwise parks everything in "Open P&L"); the equity curve is unchanged. Shows a custom metrics table (Sharpe/Sortino/CAGR/max-DD **+ Buy & Hold and Strategy − B&H** rows). `process_orders_on_close = true` fills entries at the signal bar's close, matching `backtest.py`. |
| `dip_mafia_sip_vs_timed.pine` | indicator | Per-symbol **Timed HODL vs SIP** comparison with realistic **monthly contributions** (flat ₹/mo input). A `strategy()` can't take periodic cash, so this hand-rolls the accounting: adds ₹X to a cash pool each month, then runs Timed HODL (deploy into dips; deploy idle cash after N bars - the single-symbol reduction of the V4 fallback) and SIP (deploy monthly) on the same stream. Plots both equity curves + Invested, with a table (mult / return / **Timed − SIP** in ₹ and pp). Benchmark is **SIP, not day-1 Buy & Hold** - the fair yardstick when cash arrives over time. On-chart analog of `simulate_timed_hodl` vs `simulate_sip`; no cross-stock fallback or 15% cap (those are portfolio-level, in `backtest.py`). |

## Inputs (both scripts)

- **MACD trigger** (`Combine` group): `Standard` / `Impulse` / `Either` / `Both`. The **indicator** defaults to `Either` (it mirrors the Telegram message, which surfaces both the Standard and Impulse sections). The **strategy** defaults to `Impulse`, because the Timed HODL backtest buys on the BB gate + Impulse MACD only (`imp_sig == "Buy"`) - Standard MACD never enters the buy decision.
- **Require close < BB midline** (`Bollinger gate` group): **on by default** in both scripts, matching the live config (`bot.py REQUIRE_CLOSE_BELOW_MIDLINE = True` and `backtest.py BUY_REQUIRE_BELOW_MID = True`): a buy needs close < BB midline on top of the lower-band touch. Turn off for the looser BB(touch)+MACD universe.

## Chart background zones (both scripts)

- **Green** = lower-band touch (`bbBuy`) - the dip itself, where low/close tagged the lower band.
- **Purple** = the `Watch` grace window - the up-to-60-bar (`watchLookback`) stretch *after* a touch where the stock is still a valid buy candidate, pending a MACD cross. With the midline gate on, a buy only fires on the part of the purple zone still **below the orange midline**; once price recovers above it, the candidate is dropped even though it's inside the 60-bar window.

## Not ported

Portfolio-level mechanics - fallback averaging, the 15%-per-stock cap, the SIP
split - need a shared cash pool across the watchlist. Pine runs per-symbol, so
those stay in `backtest.py`. The strategy file is a per-symbol approximation of
Timed HODL, not a replacement for the portfolio sim.

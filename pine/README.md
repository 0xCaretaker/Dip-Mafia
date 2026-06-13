# Pine Script ports (TradingView)

TradingView ports of the Dip Mafia signal layer. These are **standalone** — no
Python imports them; paste them into the TradingView Pine Editor on a **daily**
NSE chart (needs ~230+ daily bars for the 200-bar Bollinger warmup).

| File | Type | What it does |
|------|------|--------------|
| `dip_mafia.pine` | indicator | BB(200, 2σ) `{Buy, Watch}` gate + Standard MACD (12/26/9) and Impulse MACD (LazyBear variant). Plots a **BUY** marker only when a MACD bullish cross fires inside the Bollinger universe. Sell/weakness crossovers are info-only, never traded. |
| `dip_mafia_strategy.pine` | strategy | Same gate/signals wired into `strategy()`. Long-only, deploys a fixed cash tranche per gated buy and **never exits** (HODL). Shows an equity-curve metrics table (Sharpe/Sortino/CAGR/max-DD) since a never-sell strategy has no closed trades for TradingView's built-in stats. |

## Inputs (both scripts)

- **MACD trigger** (`Combine` group): `Standard` / `Impulse` / `Either` (default) / `Both`.
- **Require close < BB midline** (`Bollinger gate` group): off by default (matches the live bot `REQUIRE_CLOSE_BELOW_MIDLINE = False`); on = stricter mode matching `backtest.py` `BUY_REQUIRE_BELOW_MID = True`.

## Not ported

Portfolio-level mechanics — fallback averaging, the 15%-per-stock cap, the SIP
split — need a shared cash pool across the watchlist. Pine runs per-symbol, so
those stay in `backtest.py`. The strategy file is a per-symbol approximation of
Timed HODL, not a replacement for the portfolio sim.

# PRODUCT.md - Dip Mafia dashboard

**What it is.** A single-page, static research dashboard (GitHub Pages, `docs/`) for the Dip Mafia long-only dip-buying strategy on NSE stocks. It reports - it never trades. Audience is the strategy's author (one power user) plus a few followers reading the public page.

**Register.** Product (a tool the user is *in*), with an "almanac of hindsight" editorial character. Earned familiarity over novelty; the instrument disappears into the task. Distinctive, not decorative.

**Surfaces (one unified page, `docs/index.html`).** Five sections behind a top nav, all driven by one global horizon control (`1Y / 3Y / 5Y / 10Y / All`):
1. **Overview** - the "so what": live portfolio value & P&L + strategy verdict at the chosen horizon.
2. **Portfolio** - reconstructed NAV equity curve, re-scoped cards, allocation, holdings table.
3. **Backtest** - Timed HODL vs SIP vs NIFTY: equity/drawdown + per-horizon metric grid + supporting charts.
4. **Screens (six7)** - fundamental-screen leaderboard + inspect-a-list (the former almanac).
5. **Iterations** - watchlist-vs-watchlist comparison over time.

**Data.** Two generated JS globals, never read raw: `window.SIX7_DATA` (`docs/data.js`, from `analysis/build_web.py`) for Screens; `window.STRAT_DATA` (`docs/strat_data.js`, from `analysis/portfolio_view.py`) for the rest. Frontend is hand-authored; Python is a pure data layer.

**Pipeline.** No framework, no build step. Plain static files in `docs/`, served by GitHub Pages. Edit `docs/index.html` directly. Charts are hand-built SVG (no chart library) for cohesion and crispness.

**Invariants.** Signals only - the strategy never sells; "we only buy dips and HODL." No em-dashes anywhere. Money in ₹ (lakh/crore). Tabular figures.

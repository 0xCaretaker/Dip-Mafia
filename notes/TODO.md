# Roadmap

## Dashboard URL migration (decided 2026-06-14, do later)
Goal: serve the Pages dashboard at a clean `https://dip-mafia.github.io/` instead of
`0xcaretaker.github.io/Dip-Mafia/`. A `<name>.github.io` URL requires the GitHub *account*
to be named that, so this needs a new org. Steps (all in GitHub web UI):
- [ ] Create a Free org named `dip-mafia` (github.com/organizations/plan). If the name is
      taken, the final URL becomes `<chosen-name>.github.io`.
- [ ] Transfer this repo into the org (Settings → Danger Zone → Transfer). Old
      `0xCaretaker/Dip-Mafia` links auto-redirect.
- [ ] Rename the repo to `dip-mafia.github.io` for the root URL with no `/Dip-Mafia/` path
      (skip if `dip-mafia.github.io/Dip-Mafia/` is acceptable).
- [ ] Pages → Source: Deploy from a branch → `main` / `/docs`.
- [ ] After move: update the footer "source" link in `docs/index.html` (currently
      `github.com/0xCaretaker/Dip-Mafia`, the only hardcoded ref) and re-point the local
      git remote (`git remote set-url origin …`). Alternative to all of this: a custom
      domain (CNAME in docs/ + DNS) on the existing repo.

## Backtest Module
- [ ] Run the existing BB + MACD strategy over historical data
- [ ] Report: win rate, avg return per signal, max drawdown, time to recovery
- [ ] Compare Standard MACD vs Impulse MACD signal quality
- [ ] Validate the 200-period BB as a filter vs shorter periods

## Watchlist Management via Telegram
- [ ] `/add SYMBOL` and `/remove SYMBOL` commands
- [ ] Update `stocks.txt` via bot replies (polling or webhook)
- [ ] Confirmation messages with current watchlist count

## Price Alerts (% from 52-week low/high)
- [ ] Calculate distance from 52-week low and high for each stock
- [ ] Flag stocks near 52-week lows that also have BB Watch/Buy
- [ ] Add to Telegram output as additional context

## Historical Signal Log
- [ ] Append each run's signals to a CSV/JSON in the repo
- [ ] Auto-commit via workflow after each run
- [ ] Build dataset to track how signals played out over time
- [ ] Eventually: auto-calculate signal hit rate from the log

## Multi-Timeframe Confirmation
- [ ] Add weekly MACD alongside daily
- [ ] Highlight when daily + weekly MACD align (stronger signal)
- [ ] Separate section or tag in Telegram output

## Integrate Fundamental Screener
- [ ] Bring the external fundamental analysis tool into this repo
- [ ] Auto-refresh `stocks.txt` from screener output on a schedule
- [ ] Full pipeline: fundamental screen → technical timing → Telegram

# Roadmap

## Open follow-ups

- [ ] **Optional Verdict tightening**: live bot keeps `REQUIRE_CLOSE_BELOW_MIDLINE=False` so Watch names
      that recovered above the 200-SMA (e.g. MOTILALOFS) still render. Flip to True to match the backtest's
      stricter gate; needs a call on whether to lose those alerts.

## Not on GitHub (local only — back up before wiping)
- `six7/.claude/` (settings.json + skills/) is personal Claude config, gitignored/untracked by repo convention — it will NOT survive a workspace wipe.
- `holdings.txt` is committed, but is a manual Kite snapshot — refresh via Portfolio-Analyzer when needed (`cp …/data/holdings.txt ./holdings.txt && python3 watchlist.py`).

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

## Backlog ideas (not started)

### Watchlist management via Telegram
- [ ] `/add SYMBOL` and `/remove SYMBOL` commands
- [ ] Update `holdings.txt` via bot replies (polling or webhook)
- [ ] Confirmation messages with current watchlist count

### Price alerts (% from 52-week low/high)
- [ ] Calculate distance from 52-week low and high for each stock
- [ ] Flag stocks near 52-week lows that also have BB Watch/Buy
- [ ] Add to Telegram/Discord output as additional context

### Historical signal log
- [ ] Append each run's signals to a CSV/JSON in the repo
- [ ] Auto-commit via workflow after each run
- [ ] Build dataset to track how signals played out over time
- [ ] Eventually: auto-calculate signal hit rate from the log

### Multi-timeframe confirmation
- [ ] Add weekly MACD alongside daily
- [ ] Highlight when daily + weekly MACD align (stronger signal)
- [ ] Separate section or tag in output

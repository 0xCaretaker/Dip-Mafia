# Roadmap

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

## Open questions from the six7 audit (2026-08-28)

Both need point-in-time data that only started accumulating 2026-08-26; usable
around **late October 2026** (~60 observation days). Do NOT re-run these on
back-dated panels — that produced five retractions across six7 audit volumes
III-VI, because rescaling a multiple by a price ratio that spans the measurement
window makes `Spearman(factor, return) = -1.000` by construction.

- [ ] **Does buying below the 200-SMA actually pay off, just later?**
      The premise this bot is built on. Clean price-only tests over 6 windows show
      below-SMA names UNDERperforming in 6/6 in the broad universe (mean -4.75pp),
      but that reverses inside the six7 Top 100 (4 up / 2 down, mean +0.05pp) where
      survivorship pushes the other way. Genuinely unresolved. All windows tested
      were <= 6 months; a value thesis plausibly needs 6-12.
- [ ] **Can cheapest-PEG be used to pick within the watchlist?**
      Untestable today: back-dated PEG sorts winners into the cheap bucket, and
      today's PEG sorts losers into it (cheapest-20 beat only 4%/1%/2% of random
      draws). A clean cross-sectional test does show cheapness and price weakness
      travel together: `Spearman(PEG, position vs 200-SMA) = +0.254` (p=0.011).
- [ ] **Re-run the strat backtest.** The README's headline numbers use the
      then-current Top 50 and predate both the widening to 100 and the 2026-08-28
      six7 scoring rebuild (PEG now built from `pe`, not the vendor forward PE).
      The figures are stale as well as hindsight-biased.
- [ ] **Reconsider the gate-vs-timing framing.** Deferred by the owner pending the
      data above: whether a reversal signal should decide *whether* to buy (a veto)
      or only *when* to place an order already decided.

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

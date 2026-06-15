# Roadmap

## ⏳ Session handoff (2026-06-15) — continue on another desktop

Everything below shipped this session is **merged to GitHub** on both repos. Pick up here.

### The ONE pending action (required for the Telegram button to work)
The six7 site's new **🩸 Run Dip Mafia** button dispatches Dip-Mafia's `dip-mafia.yml`,
but the six7 Vercel function needs a token to do it:
- [ ] Create a **fine-grained PAT** with **Actions: Read and write** on `0xCaretaker/Dip-Mafia`.
- [ ] Add it to **Vercel → six7 project → Settings → Environment Variables** as
      **`DIPMAFIA_DISPATCH_TOKEN`** (optional `DIPMAFIA_REPO` overrides the default slug).
- [ ] **Redeploy six7** (Vercel applies new env vars on the next deploy). That same redeploy
      also makes the floor-0.5 financials scoring + updated sub-score copy live on the dashboard.
- [ ] Test: press the button → `dip-mafia.yml` runs with `force=true` → signals post to Telegram (~1-2 min).
- Until the token is set, the button toasts "Telegram dispatch not configured" (a clean 502). Doc: `six7/docs/DEPLOY-VERCEL.md`.

### Shipped this session (merged)
- **Two-list watchlist** (Dip-Mafia #26): bot signals on `six7.txt` ∪ `holdings.txt` via `watchlist.py`;
  Telegram tags `⭐` Top 50 / `💼` holding. `stocks.txt` is now a derived union.
- **Auto-regen** (Dip-Mafia #27): `regen-stocks.yml` rebuilds `stocks.txt` when a source list changes.
- **Mirror → six7.txt** (six7 #9): the six7 scorer now writes `six7.txt`, not `stocks.txt`.
- **Financials scoring fix** (six7 #10, **live**): FCF/D-E floored at neutral 0.5 for Financials
  (reward good values, no free ROE-only pillar). Top-50 financials 10→3. Applied via a web-scan run.
- **Force-send** (Dip-Mafia #28): `DIP_MAFIA_FORCE` / `dip-mafia.yml` `force` input so manual runs post even if unchanged.
- **Run Dip Mafia button** (six7 #11): `POST /api/notify` + the dashboard button.
- six7 WIP preserved (six7 #12): dispatch follow-redirects + `ruff.toml`.

### Other open follow-ups
- [ ] **Almanac lockstep**: `HODL-bot/six7_stocks/build_lists.py` reads a *baked* snapshot — re-save it
      from the redeployed six7 API + re-run so its lists reflect the new financials scoring (almanac only, not the live bot).
- [ ] Rerun the strat backtest/dashboards — the research universe grew 50→~100 (two-list union).
- [ ] Offered but not built: put the Dip Mafia button on another page; add a confirmation dialog before it fires.

### Not on GitHub (local only — back up before wiping)
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

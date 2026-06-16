# Roadmap

## ⏳ Session handoff (2026-06-17)

### Shipped today (merged)
- **Run Dip Mafia button wired up end-to-end** (six7 prod): six7 `/api/notify` now falls back to
  `GITHUB_TOKEN` if `DIPMAFIA_DISPATCH_TOKEN` is unset (single PAT covers `/api/scan` + notify).
  A dedicated fine-grained PAT (Dip-Mafia Actions R/W) is set as `DIPMAFIA_DISPATCH_TOKEN` in Vercel,
  the broad `GITHUB_TOKEN` stays for scan. Button verified: `{"dispatched": true}`.
- **Discord mirror** (Dip-Mafia): `send_discord_message()` ships the Telegram payload to a Discord
  channel via webhook (opt-in via `DISCORD_WEBHOOK_URL` repo secret). MarkdownV2 → Discord conversion
  strips `\\(`/`\\.` escapes and promotes `*X*` → `**X**`. Prepends `@here` with explicit
  `allowed_mentions` so the ping actually fires. Splits on blank lines to stay under Discord's 2000-char cap.
- **README / button copy**: README now lists both Telegram + Discord invites; the six7 button tooltip
  and toast text mention both channels.

### Carried forward from 2026-06-15
- **Two-list watchlist** (Dip-Mafia #26), **auto-regen** (#27), **mirror → six7.txt** (six7 #9),
  **financials floor-0.5** (six7 #10), **force-send** (Dip-Mafia #28), **🩸 button** (six7 #11),
  six7 WIP (six7 #12).

### Open follow-ups
- [ ] **Auto-delete Discord posts after 24h**: webhooks can `DELETE /webhooks/{id}/{token}/messages/{msg_id}`,
      but only if we persist each message ID. Needs (a) capture-and-store on send, (b) a scheduled
      cleanup workflow that sweeps entries older than 24h. ~30 lines + a state file. Deferred.
- [ ] **Optional Verdict tightening**: live bot keeps `REQUIRE_CLOSE_BELOW_MIDLINE=False` so Watch names
      that recovered above the 200-SMA (e.g. MOTILALOFS) still render. Flip to True to match the backtest's
      stricter gate; needs a call on whether to lose those alerts.
- [ ] Optional UX: button on another page; confirmation dialog before dispatch.
- [ ] **Rotate the Discord webhook** — the URL was pasted in chat during setup. Delete + recreate the
      webhook in Discord → Integrations, then `gh secret set DISCORD_WEBHOOK_URL --repo 0xCaretaker/Dip-Mafia --body "<new>"`.

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

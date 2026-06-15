# Two-list watchlist: `holdings.txt` + `six7.txt`

Date: 2026-06-15
Status: approved-pending-spec-review
Branch: `two-list-watchlist`  ·  Spec lives in `notes/` (docs/superpowers is gitignored)

## Problem

The live bot reads a single `stocks.txt`. An external six7 scorer (separate repo)
auto-mirrors the NSE Top 50 into `stocks.txt` on every scan, **overwriting it**.
That means any stock the user actually holds but which is not in the current Top 50
silently stops getting signals. Measured on 2026-06-15: of 54 Kite holdings, only
2 (`BSE`, `OBEROIRLTY`) are in the current Top 50 — so 52 real positions would lose
coverage on the next mirror.

The user never sells (core product invariant), so they need signals on their actual
book *and* on the Top 50 watchlist, with the Telegram message distinguishing the two.

## Goal

Split the single watchlist into two source files and signal on their union:

- `holdings.txt` — the user's real Zerodha book (hand-synced from the
  Portfolio-Analyzer Kite export). Stable; not touched by the mirror.
- `six7.txt` — the six7 Top 50 (the external mirror is repointed here).

Both feed signals. The Telegram message tags each row by class so the user can tell
a Top 50 name from a holding-they-own-but-isn't-in-the-Top-50.

`stocks.txt` is retained as a **derived union** so the backtest/dashboard tooling
(`analysis/*.py`) keeps working unchanged.

## Decisions (locked)

- **Overlap rule:** a symbol present in both files counts as six7. "Non-six7" means
  a holding not in the current Top 50.
- **stocks.txt fate:** keep it as a generated `holdings ∪ six7` union; analysis
  tooling is untouched.
- **Telegram legend:** explicit tag on every row — `⭐` six7 / `💼` holding —
  placed before the dip-position emoji. Plus a legend line.
- **holdings seed:** fresh pull via the Portfolio-Analyzer tool (interactive Kite
  login run by the user), then copied into this repo.

## Design

### 1. `watchlist.py` (new, repo root) — single source of truth

```python
load_watchlist() -> (symbols, six7_set, holdings_set)
```
- Reads `six7.txt` and `holdings.txt` (one symbol per line; skips blanks and
  `#` comments).
- Normalizes: uppercase, strip a trailing NSE series suffix matching `-[A-Z]{2}$`
  (e.g. `INDOTECH-BE` → `INDOTECH`) so the symbol resolves on yfinance. The 2-letter
  constraint avoids touching legitimate hyphenated symbols like `BAJAJ-AUTO`.
- Returns the sorted union plus the two membership sets. All values are clean names
  (no `.NS`).

```python
regenerate_stocks_txt()   # also runnable as: python3 watchlist.py
```
- Writes the sorted union to `stocks.txt` for the analysis/backtest tooling.

Rationale: one place owns reading, normalization, dedup, classification, and the
derived-file regeneration — instead of duplicating the read across `bot.py`.

### 2. `bot.py`

- Replace the inline `stocks.txt` read in `main()` with `load_watchlist()`; append
  `.NS` to the union; guard on empty.
- Pass `six7_set` into `send_bulk_telegram_message`.
- In `append_macd_section`'s render loop, compute a class marker per row
  (`⭐` if the clean name is in `six7_set`, else `💼`) and place it before the
  existing dip-position prefix:
  `f"{emoji[action]} {marker} {pos_prefix}\`{padded_stock} ₹{price_str}\`"`.
- Add a legend line in the footer block: `_⭐ Top 50 · 💼 your holding_`.
- Sentiment, counts, dedup hash, and column widths widen naturally to the larger
  universe; no other logic changes.

### 3. File seeding (committed to this repo so GitHub Actions can read them)

- `six7.txt` ← current `stocks.txt` (the 50 Top names).
- `holdings.txt` ← `~/claude/Portfolio-Analyzer/data/holdings.txt` (fresh Kite
  export), stored raw — the loader normalizes at read time.
- `stocks.txt` ← regenerated union (~100 symbols), replacing the current 50.

### 4. Docs

- `CLAUDE.md`: document the two-list model, `watchlist.py`, and the
  "regenerate `stocks.txt` before a backtest" step.
- `README.md`: watchlist description + repo layout.
- `.claude/agents/quant-advisor.md`: fix the "`stocks.txt` is the live book" claim
  (now `six7.txt` + `holdings.txt`; `stocks.txt` is derived).

### 5. Tests / verification

- `tests/test_watchlist.py`: dedup, suffix normalization, six7-wins classification,
  union sorting, missing-file tolerance.
- Manual: `python3 bot.py` with no `TELEGRAM_TOKEN` builds and prints the tagged
  message without sending — confirm `⭐`/`💼` tags and legend render.

## Out of scope (follow-ups, not coded here)

- **six7 mirror repoint (cross-repo):** the six7 scorer must write `six7.txt`
  instead of `stocks.txt`, and ideally run `python3 watchlist.py` afterward.
- **holdings refresh:** run the Portfolio-Analyzer fetch (interactive Kite login),
  then `cp ~/claude/Portfolio-Analyzer/data/holdings.txt ./holdings.txt &&
  python3 watchlist.py`.
- **Backtest/almanac rerun:** the research universe grows 50 → ~100 (now includes
  illiquid SME holdings); rerun `backtest.py` / `horizon_compare.py` /
  `portfolio_view.py` / `backtest_six7.py` to refresh dashboards.

## Risks

- Backtest universe doubling shifts research numbers and may include thin-data SME
  names. Accepted per the derived-union decision; dashboards rerun as a follow-up.
- Some holdings lack sufficient yfinance history → skipped with `✗`, no signal, no
  crash. Expected.
- The `-[A-Z]{2}$` suffix heuristic could mis-strip a future symbol; low risk for
  the current lists.
- `holdings.txt` is a manual snapshot and drifts from the real book until re-synced.

#!/usr/bin/env python3
"""
Data layer for the unified Dip Mafia dashboard.

Emits a single JS data file consumed by the hand-authored ``docs/index.html``
app (designed separately):

    docs/strat_data.js   ->   window.STRAT_DATA = { portfolio, backtest,
                                                     iterations, horizons_grid }

It no longer generates any HTML, and it no longer reconstructs a single lifetime
book from ``trades.csv``. The Portfolio + Overview sections are now **fresh,
self-contained per-horizon simulations**: the ``5Y`` view is the Timed HODL book
you would hold if you had started investing 5 years ago (NAV from ~₹0), valued at
the data-date close. Those per-horizon books are produced upstream by
``horizon_compare.py`` (``strategy_horizons.portfolios``); this script just
reshapes them into ``window.STRAT_DATA.portfolio.byHorizon[<HZ>]`` (summary,
rows, alloc, pnl, nav), so every section answers to the one global horizon control.

Reads (from the newest run subfolder under backtest_output/, via run_paths):
  - <current run>/dashboard_data.json  backtest results (from backtest.py)
  - <current run>/horizons.json        per-horizon strategy + portfolio + grid

Run: python3 analysis/portfolio_view.py   (from the repo root, after
     backtest.py and horizon_compare.py)
Output: docs/strat_data.js
"""

import json
import os
from datetime import datetime

import run_paths

CURRENT_RUN = run_paths.current_run() or run_paths.BASE
BACKTEST_JSON = os.path.join(CURRENT_RUN, "dashboard_data.json")
HORIZONS_JSON = os.path.join(CURRENT_RUN, "horizons.json")
TIMED_KEY = "Your Strategy (Timed HODL)"
DOCS_DIR = "docs"

# Global horizon set shared with the frontend. (label, years; None = full history)
HORIZONS = [("1Y", 1), ("3Y", 3), ("5Y", 5), ("10Y", 10), ("All", None)]
# strategy_horizons keys -> dashboard horizon labels
HZ_LABEL = {"1y": "1Y", "3y": "3Y", "5y": "5Y", "10y": "10Y", "Full": "All"}


# ─── Iteration history (old vs new watchlist) ────────────────────────────────

def _iter_entry(label, watchlist, data, is_current=False):
    """One row for the Iterations section: Timed HODL metrics + equity curve."""
    metrics = {x["name"]: x for x in data.get("metrics", [])}
    t = metrics.get(TIMED_KEY, {})
    eq = data.get("equity", {}).get(TIMED_KEY, {})
    a = data.get("assumptions", {})
    s = data.get("summary", {})
    return {
        "label": label,
        "is_current": is_current,
        "watchlist": watchlist,
        "n_stocks": s.get("n_stocks"),
        "final_value": t.get("final_value"),
        "xirr": t.get("xirr"),
        "sharpe": t.get("sharpe"),
        "sortino": t.get("sortino"),
        "max_drawdown": t.get("max_drawdown"),
        "cash_pct": s.get("cash_pct"),
        "period": f"{a.get('start_date', '')} → {a.get('end_date', '')}".strip(" →"),
        "equity": {"dates": eq.get("dates", []), "values": eq.get("values", [])},
    }


def load_iterations(current_data):
    """Current run first (newest subfolder), then every other run."""
    iters = []
    cur = run_paths.current_run()
    if current_data:
        meta = json.load(open(os.path.join(cur, "meta.json"))) if cur and os.path.isfile(os.path.join(cur, "meta.json")) else {}
        wl = meta.get("watchlist_size")
        if wl is None:
            try:
                wl = sum(1 for ln in open("stocks.txt") if ln.strip())
            except OSError:
                wl = None
        label = f"Current ({wl}-symbol list)" if wl else "Current"
        iters.append(_iter_entry(label, wl, current_data, is_current=True))

    for d in run_paths.archived_runs():
        jp = os.path.join(d, "dashboard_data.json")
        try:
            data = json.load(open(jp))
        except (json.JSONDecodeError, OSError):
            continue
        meta = {}
        mp = os.path.join(d, "meta.json")
        if os.path.isfile(mp):
            try:
                meta = json.load(open(mp))
            except (json.JSONDecodeError, OSError):
                meta = {}
        label = meta.get("label") or os.path.basename(d)
        iters.append(_iter_entry(label, meta.get("watchlist_size"), data))

    return iters


# ─── Portfolio (fresh per-horizon books) ─────────────────────────────────────

def build_portfolio(horizons):
    """Reshape strategy_horizons.portfolios into byHorizon[<HZ>] blocks.

    Each block is a complete, self-contained book (summary, rows, alloc, pnl,
    nav) for a fresh simulation that started ``HZ`` ago, valued at the data-date
    close. ``All`` is the full-history sim (== the lifetime book)."""
    sh = (horizons or {}).get("strategy_horizons") or {}
    src = sh.get("portfolios") or {}
    by_h = {HZ_LABEL.get(k, k): v for k, v in src.items()}
    return {"byHorizon": by_h, "asof": (horizons or {}).get("end_date")}


# ─── Backtest reshape ────────────────────────────────────────────────────────

def reshape_backtest(backtest_data, horizons):
    """Pass the backtest payload through, attaching the expanded per-horizon ×
    per-strategy metric grid from horizons.json (strategy_horizons)."""
    if not backtest_data:
        return None
    sh = (horizons or {}).get("strategy_horizons") or {}
    cells = {}
    for k, v in (sh.get("cells") or {}).items():
        strat, hl = k.rsplit("|", 1)
        cells[f"{strat}|{HZ_LABEL.get(hl, hl)}"] = v
    curves = {HZ_LABEL.get(hl, hl): c for hl, c in (sh.get("curves") or {}).items()}
    backtest_data["horizon_metrics"] = {
        "horizons": [HZ_LABEL.get(h, h) for h in (sh.get("horizons") or [])],
        "strategies": sh.get("strategies") or ["Timed HODL", "SIP", "NIFTY 50"],
        "metrics": sh.get("metrics") or [],
        "cells": cells,
        "curves": curves,
        "gated": sh.get("gated"),
        "contribution": sh.get("contribution"),
    }
    return backtest_data


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    horizons = None
    try:
        with open(HORIZONS_JSON) as f:
            horizons = json.load(f)
        print(f"  Loaded horizons.json ({len(horizons.get('cells', {}))} grid cells)")
    except (FileNotFoundError, json.JSONDecodeError):
        print("  No horizons.json (run horizon_compare.py first)")

    portfolio_data = build_portfolio(horizons)
    bh = portfolio_data["byHorizon"]
    if bh:
        allp = bh.get("All") or next(iter(bh.values()))
        print(f"  Portfolio: {len(bh)} horizons; All = "
              f"{allp['summary']['count']} holdings, "
              f"value {allp['summary']['total_value']:,}")
    else:
        print("  Portfolio: no per-horizon books (strategy_horizons.portfolios missing)")

    backtest_data = None
    try:
        with open(BACKTEST_JSON) as f:
            backtest_data = json.load(f)
        print(f"  Loaded backtest data from {BACKTEST_JSON}")
    except FileNotFoundError:
        print(f"  No backtest data ({BACKTEST_JSON})")

    backtest_data = reshape_backtest(backtest_data, horizons)
    iterations = load_iterations(json.load(open(BACKTEST_JSON)) if os.path.isfile(BACKTEST_JSON) else None)
    n_arch = max(0, len(iterations) - 1)
    if n_arch:
        print(f"  Iterations: current + {n_arch} archived run(s)")

    # Iterations grid: drop strategy_horizons (its curves + per-horizon books now
    # live in backtest.horizon_metrics / portfolio.byHorizon) so the payload
    # doesn't carry them twice.
    grid = None
    if horizons:
        grid = {k: v for k, v in horizons.items() if k != "strategy_horizons"}

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_run": os.path.basename(CURRENT_RUN),
        "end_date": (horizons or {}).get("end_date"),
        "horizon_set": [h for h, _ in HORIZONS],
        "portfolio": portfolio_data,
        "backtest": backtest_data,
        "iterations": iterations,
        "horizons_grid": grid,
    }

    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, "strat_data.js")
    with open(out_path, "w") as f:
        f.write("window.STRAT_DATA = ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";\n")
    print(f"  Wrote {out_path}")


if __name__ == "__main__":
    main()

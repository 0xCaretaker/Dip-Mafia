#!/usr/bin/env python3
"""
Horizon comparison for the dashboard Iterations tab.

For the current watchlist (stocks.txt) and every archived watchlist
(backtest_output_archive_*/stocks.txt), computes Timed HODL returns over
1y / 3y / 5y / Full trailing windows, for three signal variants:

  bb60      — Bollinger watch lookback 60 (the default / live config)
  bb30      — lookback 30
  bb60mid   — lookback 60 + extra "close below BB midline" buy gate

Signals are computed over full history (so the 200-bar Bollinger warmup is always
satisfied); only the investing/measurement window is the trailing horizon. A flat
₹20k/month contribution is used so horizons are comparable to each other and to the
six7 almanac.

Prices come from six7_backtest_output/_price_cache.pkl when present (full history,
no download); otherwise they are downloaded once via backtest.download_batch.

Output: backtest_output/horizons.json  (read by portfolio_view.py)
Run:    .venv/bin/python horizon_compare.py   (after backtest.py)
"""

import os
import glob
import json
import pickle

import pandas as pd

import backtest as bt

END = pd.Timestamp("2026-04-20")               # data-as-of (matches the strat run)
PRICE_CACHE = "six7_backtest_output/_price_cache.pkl"
OUT = "backtest_output/horizons.json"

HORIZONS = [("1y", 1), ("3y", 3), ("5y", 5), ("Full", None)]
# bb-60 first = the default. (key, label, lookback, require_below_mid)
VARIANTS = [
    ("bb60",    "bb-60",      60, False),
    ("bb30",    "bb-30",      30, False),
    ("bb60mid", "bb-60 +mid", 60, True),
]


def read_list(path):
    try:
        return [ln.strip() for ln in open(path) if ln.strip()]
    except OSError:
        return []


def load_prices(symbols):
    """Full-history OHLC per bare symbol, truncated to END. Cache first, else download."""
    data = {}
    if os.path.isfile(PRICE_CACHE):
        raw = pickle.load(open(PRICE_CACHE, "rb")).get("stock_dfs", {})
        for ksym, df in raw.items():
            bare = ksym[:-3] if ksym.endswith(".NS") else ksym
            d = df[df.index <= END]
            if not d.empty:
                data[bare] = d
    missing = [s for s in symbols if s not in data]
    if missing:
        cfg = {"start": "2010-01-01", "end": str(END.date())}
        print(f"  {len(missing)} symbols not cached, downloading...")
        for sym, df in bt.download_batch(missing, cfg).items():
            d = df[df.index <= END]
            if not d.empty:
                data[sym] = d
    return data


def signals_for(data, lookback):
    cfg = dict(bt.CONFIG)
    cfg["bb_lookback"] = lookback
    cfg["initial_salary"] = 80_000          # 80k * 0.25 = flat 20k/mo
    cfg["salary_growth"] = 0.0
    cfg["invest_pct"] = 0.25
    bb, bb_mid, imp, _imp_st, _sk = bt.generate_all_signals(data, cfg)
    return cfg, bb, bb_mid, imp


def run_cell(data, symbols, years, sig, end_dt):
    cfg, bb, bb_mid, imp, below_mid = sig
    bt.BUY_REQUIRE_BELOW_MID = below_mid
    hstart = (min(data[s].index.min() for s in symbols if s in data)
              if years is None else end_dt - pd.DateOffset(years=years))
    win = {s: data[s][data[s].index >= hstart] for s in symbols if s in bb}
    win = {s: df for s, df in win.items() if not df.empty}
    syms = list(win.keys())
    dates = bt.get_all_dates(win, syms)
    if not dates:
        bt.BUY_REQUIRE_BELOW_MID = False
        return None
    monthly = bt.build_monthly_investments(dates, cfg)
    sim, cf, _bl, _idle = bt.simulate_timed_hodl(
        win, syms, monthly, bb, bb_mid, imp, slippage_bps=cfg["slippage_bps"])
    bt.BUY_REQUIRE_BELOW_MID = False
    m = bt.compute_metrics(sim["portfolio"], "T", cf)
    inv = sum(v["amount"] for v in monthly.values())
    return {"xirr": round(m["xirr"], 1),
            "mult": round(m["final_value"] / inv, 2) if inv else None,
            "maxdd": round(m["max_drawdown"], 1)}


def build():
    # watchlists: current first, then each archive (matches Iterations tab ordering)
    watchlists = [{"key": "Current", "label": "Current", "is_current": True,
                   "symbols": read_list("stocks.txt")}]
    for d in sorted(glob.glob("backtest_output_archive_*"), reverse=True):
        syms = read_list(os.path.join(d, "stocks.txt"))
        if not syms:
            continue
        meta = {}
        mp = os.path.join(d, "meta.json")
        if os.path.isfile(mp):
            try:
                meta = json.load(open(mp))
            except (json.JSONDecodeError, OSError):
                meta = {}
        label = meta.get("label") or d.replace("backtest_output_archive_", "")
        # strip the "(… bb-30)" parenthetical so the variant columns aren't redundant
        label = label.split(" (")[0].split(", bb")[0]
        watchlists.append({"key": d, "label": label, "is_current": False, "symbols": syms})

    union = sorted({s for wl in watchlists for s in wl["symbols"]})
    print(f"Watchlists: {[w['label'] for w in watchlists]}")
    print(f"Loading prices for {len(union)} symbols...")
    data = load_prices(union)
    end_dt = max(df.index.max() for df in data.values())
    print(f"  {len(data)} symbols, data to {end_dt.date()}")

    sigs = {}
    for key, _lbl, lb, mid in VARIANTS:
        cfg, bb, bb_mid, imp = signals_for(data, lb)
        sigs[key] = (cfg, bb, bb_mid, imp, mid)

    cells = {}
    for wl in watchlists:
        for vkey, _vl, _lb, _mid in VARIANTS:
            for hl, yr in HORIZONS:
                r = run_cell(data, wl["symbols"], yr, sigs[vkey], end_dt)
                if r:
                    cells[f"{wl['key']}|{vkey}|{hl}"] = r
        print(f"  done: {wl['label']}")

    out = {
        "end_date": str(end_dt.date()),
        "source": "price cache" if os.path.isfile(PRICE_CACHE) else "download",
        "contribution": "flat ₹20k/month",
        "default_variant": "bb60",
        "horizons": [h for h, _ in HORIZONS],
        "variants": [{"key": k, "label": l} for k, l, _lb, _m in VARIANTS],
        "watchlists": [{"key": w["key"], "label": w["label"], "is_current": w["is_current"]}
                       for w in watchlists],
        "cells": cells,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"))
    print(f"  wrote {OUT} ({len(cells)} cells)")


if __name__ == "__main__":
    build()

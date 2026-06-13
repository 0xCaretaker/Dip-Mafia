#!/usr/bin/env python3
"""
Horizon comparison for the dashboard Iterations tab.

For the current watchlist and every archived watchlist (each run's
<run>/stocks.txt under backtest_output/), computes Timed HODL returns over
1y / 3y / 5y / Full trailing windows, for three signal variants:

  bb60      — Bollinger watch lookback 60 (the default / live config)
  bb30      — lookback 30
  bb60mid   — lookback 60 + extra "close below BB midline" buy gate

Signals are computed over full history (so the 200-bar Bollinger warmup is always
satisfied); only the investing/measurement window is the trailing horizon. A flat
₹20k/month contribution is used so horizons are comparable to each other and to the
six7 almanac.

Prices come from backtest_output/six7/_price_cache.pkl when present (full history,
no download); otherwise they are downloaded once via backtest.download_batch.

Output: <current run>/horizons.json  (read by portfolio_view.py)
Run:    .venv/bin/python horizon_compare.py   (after backtest.py)
"""

import os
import json
import pickle

import numpy as np
import pandas as pd
import yfinance as yf

import backtest as bt
import run_paths

END = pd.Timestamp("2026-04-20")               # data-as-of (matches the strat run)
PRICE_CACHE = os.path.join(run_paths.SIX7, "_price_cache.pkl")
OUT = os.path.join(run_paths.current_run() or run_paths.BASE, "horizons.json")

HORIZONS = [("1y", 1), ("3y", 3), ("5y", 5), ("Full", None)]
# 3-strategy horizon table (Backtest tab). Metrics kept: all of them.
STRAT_METRICS = [
    {"key": "xirr",   "label": "XIRR",      "fmt": "pct"},
    {"key": "sharpe", "label": "Sharpe",    "fmt": "num"},
    {"key": "maxdd",  "label": "Max DD",    "fmt": "pct"},
    {"key": "cash",   "label": "Cash drag", "fmt": "pct"},
]
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


def _load_nifty():
    """^NSEI close series, full history to END (single-ticker download)."""
    try:
        d = yf.download("^NSEI", start="2010-01-01", end=str(END.date()), progress=False)
        d = bt.flatten_cols(d).dropna()
        s = d["Close"]
        return s[s.index <= END]
    except Exception as e:
        print(f"  NIFTY download failed ({e}); skipping NIFTY in strategy horizons")
        return None


def _nifty_sip_window(nd, monthly):
    units = cash = 0.0
    done, recs, cf = set(), [], []
    for dt, price in nd.items():
        price = float(price)
        key = (dt.year, dt.month)
        if key in monthly and key not in done:
            amt = monthly[key]["amount"]
            cash += amt; done.add(key); cf.append((dt, -amt))
            units += cash / (price * (1 + 5 / 10000)); cash = 0.0
        recs.append({"date": dt, "portfolio": units * price + cash})
    return pd.DataFrame(recs).set_index("date")["portfolio"], cf


def strategy_horizons(data, symbols, sig, end_dt):
    """Timed HODL / SIP / NIFTY 50 across horizons, all metrics, flat ₹20k, gated
    to match the backtest default (bt.BUY_REQUIRE_BELOW_MID)."""
    cfg, bb, bb_mid, imp, _mid = sig
    fcfg = dict(bt.CONFIG); fcfg["bb_lookback"] = 60
    fcfg["initial_salary"] = 80_000; fcfg["salary_growth"] = 0.0; fcfg["invest_pct"] = 0.25
    # Match the gated backtest default (the run_cell loop above leaves the global off).
    prev_gate = bt.BUY_REQUIRE_BELOW_MID
    bt.BUY_REQUIRE_BELOW_MID = True
    nifty = _load_nifty()
    cells = {}
    for hl, yr in HORIZONS:
        hstart = (min(data[s].index.min() for s in symbols if s in data)
                  if yr is None else end_dt - pd.DateOffset(years=yr))
        win = {s: data[s][data[s].index >= hstart] for s in symbols if s in bb}
        win = {s: df for s, df in win.items() if not df.empty}
        syms = list(win.keys())
        dates = bt.get_all_dates(win, syms)
        if not dates:
            continue
        monthly = bt.build_monthly_investments(dates, fcfg)
        # Timed HODL (gate per backtest default + V4 fallback defaults)
        tsim, tcf, _bl, _idle = bt.simulate_timed_hodl(win, syms, monthly, bb, bb_mid, imp,
                                                       slippage_bps=fcfg["slippage_bps"])
        tm = bt.compute_metrics(tsim["portfolio"], "T", tcf)
        tot = tsim["portfolio"].replace(0, np.nan)
        cash = float((tsim["cash"] / tot * 100).fillna(100).mean())
        cells[f"Timed HODL|{hl}"] = {"xirr": round(tm["xirr"], 1), "sharpe": round(tm["sharpe"], 2),
                                     "maxdd": round(tm["max_drawdown"], 1), "cash": round(cash, 1)}
        # SIP
        ssim, scf = bt.simulate_sip(win, syms, monthly, fcfg["slippage_bps"])
        sm = bt.compute_metrics(ssim["portfolio"], "S", scf)
        cells[f"SIP|{hl}"] = {"xirr": round(sm["xirr"], 1), "sharpe": round(sm["sharpe"], 2),
                              "maxdd": round(sm["max_drawdown"], 1), "cash": None}
        # NIFTY 50
        if nifty is not None:
            nsim, ncf = _nifty_sip_window(nifty[nifty.index >= hstart], monthly)
            nm = bt.compute_metrics(nsim, "N", ncf)
            cells[f"NIFTY 50|{hl}"] = {"xirr": round(nm["xirr"], 1), "sharpe": round(nm["sharpe"], 2),
                                       "maxdd": round(nm["max_drawdown"], 1), "cash": None}
    gated = bool(bt.BUY_REQUIRE_BELOW_MID)
    bt.BUY_REQUIRE_BELOW_MID = prev_gate
    return {
        "gated": gated,
        "contribution": "flat ₹20k/month",
        "horizons": [h for h, _ in HORIZONS],
        "strategies": ["Timed HODL", "SIP", "NIFTY 50"],
        "metrics": STRAT_METRICS,
        "cells": cells,
    }


def build():
    # watchlists: current first, then each archive (matches Iterations tab ordering)
    cur = run_paths.current_run()
    cur_syms = (read_list(os.path.join(cur, "stocks.txt")) if cur else []) or read_list("stocks.txt")
    watchlists = [{"key": "Current", "label": "Current", "is_current": True,
                   "symbols": cur_syms}]
    for d in run_paths.archived_runs():
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
        label = meta.get("label") or os.path.basename(d)
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

    # 3-strategy horizon table for the CURRENT watchlist, using the live backtest
    # config (bb-60 signals + bt.BUY_REQUIRE_BELOW_MID gate + V4 fallback defaults).
    strat_h = strategy_horizons(data, watchlists[0]["symbols"], sigs["bb60"], end_dt)

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
        "strategy_horizons": strat_h,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"))
    print(f"  wrote {OUT} ({len(cells)} cells)")


if __name__ == "__main__":
    build()

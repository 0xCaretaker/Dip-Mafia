#!/usr/bin/env python3
"""
Horizon data for the unified dashboard (Backtest + Iterations sections).

For the current watchlist and every archived watchlist (each run's
<run>/stocks.txt under backtest_output/), computes Timed HODL returns over
1y / 3y / 5y / 10y / Full trailing windows on the bb-60 signal config.

For the CURRENT watchlist it additionally produces the full Timed HODL / SIP /
NIFTY 50 metric grid and per-horizon equity / drawdown / cash curves (Backtest
section). Each horizon is a fresh windowed sim.

Contributions use the salary model (bt.CONFIG: ₹22k/mo in 2010, +10%/yr, 25%
invested), calendar-anchored to 2010 then restricted to the window - the SAME
model as backtest.py, the six7 almanac and the Portfolio/Iterations numbers, so
every horizon's "Full"/"All" agrees with them.

Signals are computed over full history (so the 200-bar Bollinger warmup is always
satisfied); only the investing/measurement window is the trailing horizon.

Prices come from backtest_output/six7/_price_cache.pkl when present (full history,
no download); otherwise they are downloaded once via backtest.download_batch.

Output: <current run>/horizons.json  (read by portfolio_view.py)
Run:    python3 analysis/horizon_compare.py   (from the repo root, after backtest.py)
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

HORIZONS = [("1y", 1), ("3y", 3), ("5y", 5), ("10y", 10), ("Full", None)]
# 3-strategy horizon table (Backtest section). The unified dashboard reads the
# expanded cell metrics directly; this list documents the per-horizon metric set.
STRAT_METRICS = [
    {"key": "final_value", "label": "Final value", "fmt": "inr"},
    {"key": "mult",        "label": "Multiple",    "fmt": "mult"},
    {"key": "xirr",        "label": "XIRR",        "fmt": "pct"},
    {"key": "sharpe",      "label": "Sharpe",      "fmt": "num"},
    {"key": "sortino",     "label": "Sortino",     "fmt": "num"},
    {"key": "maxdd",       "label": "Max DD",      "fmt": "pct"},
    {"key": "vol",         "label": "Volatility",  "fmt": "pct"},
    {"key": "cash",        "label": "Cash drag",   "fmt": "pct"},
]
# bb-60 = the live default; the dashboard Iterations comparison uses it only.
# (key, label, lookback, require_below_mid)
VARIANTS = [
    ("bb60", "bb-60", 60, False),
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
    # Salary model (bt.CONFIG defaults: ₹22k/mo in 2010, +10%/yr, 25% invested) -
    # the same contribution model as backtest.py, the six7 almanac and the
    # Portfolio/Iterations numbers, so every horizon's "All" agrees with them.
    cfg = dict(bt.CONFIG)
    cfg["bb_lookback"] = lookback
    bb, bb_mid, imp, _imp_st, _sk = bt.generate_all_signals(data, cfg)
    return cfg, bb, bb_mid, imp


def _window_monthly(data, symbols, bb, cfg, end_dt, years):
    """Calendar-anchored monthly investments for a trailing window.

    The salary ramp is anchored to the first date of *full* history (so 2025
    months use 2025-level salary), then restricted to the window. Returns
    (win_stock_dfs, syms, monthly, hstart) or (None, ..., None) if empty.
    """
    fsyms = [s for s in symbols if s in bb]
    full_dates = bt.get_all_dates({s: data[s] for s in fsyms}, fsyms)
    if not full_dates:
        return None, [], None, None
    full_monthly = bt.build_monthly_investments(full_dates, cfg)
    hstart = (min(data[s].index.min() for s in fsyms)
              if years is None else end_dt - pd.DateOffset(years=years))
    win = {s: data[s][data[s].index >= hstart] for s in fsyms}
    win = {s: df for s, df in win.items() if not df.empty}
    syms = list(win.keys())
    if not bt.get_all_dates(win, syms):
        return None, syms, None, hstart
    monthly = {k: v for k, v in full_monthly.items() if v["date"] >= hstart}
    if not monthly:
        return None, syms, None, hstart
    return win, syms, monthly, hstart


def run_cell(data, symbols, years, sig, end_dt):
    cfg, bb, bb_mid, imp, below_mid = sig
    bt.BUY_REQUIRE_BELOW_MID = below_mid
    win, syms, monthly, _hstart = _window_monthly(data, symbols, bb, cfg, end_dt, years)
    if win is None:
        bt.BUY_REQUIRE_BELOW_MID = False
        return None
    sim, cf, _bl, _idle = bt.simulate_timed_hodl(
        win, syms, monthly, bb, bb_mid, imp, slippage_bps=cfg["slippage_bps"])
    bt.BUY_REQUIRE_BELOW_MID = False
    m = bt.nav_metrics(sim, cf, "T")
    inv = sum(v["amount"] for v in monthly.values())
    return {"xirr": round(m["xirr"], 1),
            "mult": round(m["final_value"] / inv, 2) if inv else None,
            "maxdd": round(m["max_drawdown"], 1)}


def _drawdown(series):
    cm = series.cummax()
    return (series - cm) / cm * 100


def _downsample(series, n=170):
    """Compact a daily series to ~n points (keeps first and last) as {dates, values}."""
    s = series.dropna()
    if len(s) == 0:
        return {"dates": [], "values": []}
    if len(s) <= n:
        idx = list(range(len(s)))
    else:
        step = len(s) / n
        idx = sorted(set(int(i * step) for i in range(n)) | {len(s) - 1})
    return {"dates": [s.index[i].strftime("%Y-%m-%d") for i in idx],
            "values": [round(float(s.iloc[i]), 2) for i in idx]}


def _cum_invested(index, monthly):
    """Cumulative contributed capital aligned to a sim's date index."""
    contribs = sorted((v["date"], v["amount"]) for v in monthly.values())
    out, running, ci = [], 0.0, 0
    for dt in index:
        while ci < len(contribs) and contribs[ci][0] <= dt:
            running += contribs[ci][1]; ci += 1
        out.append(running)
    return pd.Series(out, index=index)


def _unit_nav(value_series, monthly, base=100.0):
    """Unitized NAV index (fund-style, base 100). Each monthly deposit *buys
    units* at the prevailing NAV, so contributions never move the line - only
    investment performance does. NAV = portfolio value / units outstanding."""
    cum = _cum_invested(value_series.index, monthly)
    inj = cum.diff()
    if len(inj):
        inj.iloc[0] = cum.iloc[0]
    units, out = 0.0, []
    for i in range(len(value_series)):
        v = float(value_series.iloc[i])
        dep = float(inj.iloc[i])
        if dep > 1e-9:
            if units <= 0:                       # first deposit: seed at base
                nav = base
            else:                                # value before today's deposit
                nav = max(v - dep, 0.0) / units
            units += dep / nav if nav > 0 else 0.0
        else:
            nav = v / units if units > 0 else base
        out.append(nav)
    return pd.Series(out, index=value_series.index)


def _horizon_portfolio(buy_log, win, monthly, value_series, metrics, slippage_bps):
    """Per-horizon portfolio payload from a windowed Timed HODL buy_log.

    Holdings are valued at each stock's last close in the window (the data-date
    close), so every horizon is a fresh 'started N years ago' book valued at one
    consistent as-of. Returns {summary, rows, alloc, pnl, nav}.
    """
    close = {}
    for s, df in win.items():
        c = df["Close"].dropna()
        if not c.empty:
            close[s] = float(c.iloc[-1])

    agg = {}
    for b in buy_log:
        s = b["stock"]
        a = agg.setdefault(s, {"shares": 0.0, "invested": 0.0, "n": 0,
                               "first": None, "last": None, "trades": []})
        sh = b["amount"] / (b["price"] * (1 + slippage_bps / 10000))
        a["shares"] += sh; a["invested"] += b["amount"]; a["n"] += 1
        d = b["date"]
        a["first"] = d if a["first"] is None or d < a["first"] else a["first"]
        a["last"] = d if a["last"] is None or d > a["last"] else a["last"]
        a["trades"].append({"date": d.strftime("%Y-%m-%d"), "price": round(b["price"], 2),
                            "shares": round(sh, 2), "amount": round(b["amount"])})

    rows = []
    for s, a in agg.items():
        cp = close.get(s)
        if cp is None or a["shares"] <= 0:
            continue
        value = a["shares"] * cp
        # compact close-price spark over the window (sparkline + modal drilldown)
        spark = None
        df = win.get(s)
        if df is not None:
            cs = df["Close"].dropna()
            if len(cs) >= 2:
                sp = _downsample(cs, 40)
                spark = {"v": [round(x, 2) for x in sp["values"]],
                         "d0": sp["dates"][0], "d1": sp["dates"][-1]}
        rows.append({
            "stock": s, "avg_price": round(a["invested"] / a["shares"], 2),
            "cmp": round(cp, 2), "shares": round(a["shares"], 1),
            "invested": round(a["invested"]), "value": round(value),
            "pnl": round(value - a["invested"]),
            "ret": round((value - a["invested"]) / a["invested"] * 100, 1) if a["invested"] else None,
            "weight": 0.0, "num_buys": a["n"],
            "first_buy": a["first"].strftime("%Y-%m-%d"), "last_buy": a["last"].strftime("%Y-%m-%d"),
            "trades": a["trades"], "spark": spark, "_v": value,
        })
    rows.sort(key=lambda r: r["_v"], reverse=True)
    held_val = sum(r["_v"] for r in rows)
    for r in rows:
        r["weight"] = round(r["_v"] / held_val * 100, 1) if held_val else 0.0
        del r["_v"]

    invested = sum(v["amount"] for v in monthly.values())
    value = float(value_series.iloc[-1])          # incl. residual cash (NAV close)
    winners = sum(1 for r in rows if r["pnl"] > 0)
    best = max(rows, key=lambda r: r["ret"]) if rows else None
    worst = min(rows, key=lambda r: r["ret"]) if rows else None
    summary = {
        "total_invested": round(invested), "total_value": round(value),
        "total_pnl": round(value - invested),
        "total_ret": round((value - invested) / invested * 100, 1) if invested else None,
        "xirr": round(metrics["xirr"], 1), "max_drawdown": round(metrics["max_drawdown"], 1),
        "winners": winners, "losers": len(rows) - winners,
        "best_stock": best["stock"] if best else None,
        "best_ret": round(best["ret"]) if best else None,
        "worst_stock": worst["stock"] if worst else None,
        "worst_ret": round(worst["ret"]) if worst else None,
        "count": len(rows),
    }

    top_n = 10
    alloc_labels = [r["stock"] for r in rows[:top_n]]
    alloc_values = [float(r["value"]) for r in rows[:top_n]]
    if len(rows) > top_n:
        alloc_labels.append("Others")
        alloc_values.append(float(sum(r["value"] for r in rows[top_n:])))
    pnl_sorted = sorted(rows, key=lambda r: r["pnl"])

    v_ds = _downsample(value_series)
    i_ds = _downsample(_cum_invested(value_series.index, monthly))
    n_ds = _downsample(_unit_nav(value_series, monthly))
    nav = {"dates": v_ds["dates"], "value": v_ds["values"], "invested": i_ds["values"],
           "navindex": n_ds["values"]}

    return {"summary": summary, "rows": rows,
            "alloc": {"labels": alloc_labels, "values": alloc_values},
            "pnl": {"labels": [r["stock"] for r in pnl_sorted],
                    "values": [float(r["pnl"]) for r in pnl_sorted]},
            "nav": nav}


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
    """Timed HODL / SIP / NIFTY 50 across horizons: full metric grid + per-horizon
    equity / drawdown / cash curves, on the salary model, gated to match the
    backtest default (bt.BUY_REQUIRE_BELOW_MID). Each horizon is a fresh windowed
    sim with calendar-anchored contributions, so 'Full' reproduces the salary-model
    headline (the Portfolio / Iterations / almanac numbers)."""
    cfg, bb, bb_mid, imp, _mid = sig
    scfg = dict(bt.CONFIG); scfg["bb_lookback"] = 60
    prev_gate = bt.BUY_REQUIRE_BELOW_MID
    bt.BUY_REQUIRE_BELOW_MID = True
    nifty = _load_nifty()
    cells, curves, portfolios = {}, {}, {}
    for hl, yr in HORIZONS:
        win, syms, monthly, hstart = _window_monthly(data, symbols, bb, scfg, end_dt, yr)
        if win is None:
            continue
        inv = sum(v["amount"] for v in monthly.values())

        def _cell(m, cash_pct):
            return {
                "final_value": round(m["final_value"]),
                "mult": round(m["final_value"] / inv, 2) if inv else None,
                "xirr": round(m["xirr"], 1), "sharpe": round(m["sharpe"], 2),
                "sortino": round(m["sortino"], 2), "maxdd": round(m["max_drawdown"], 1),
                "maxdd_days": int(m["max_dd_days"]), "vol": round(m["volatility"], 1),
                "cash": cash_pct,
            }

        # Timed HODL (gate per backtest default + V4 fallback defaults)
        tsim, tcf, tbl, _idle = bt.simulate_timed_hodl(win, syms, monthly, bb, bb_mid, imp,
                                                       slippage_bps=scfg["slippage_bps"])
        tm = bt.nav_metrics(tsim, tcf, "T")
        tot = tsim["portfolio"].replace(0, np.nan)
        cash_series = (tsim["cash"] / tot * 100).fillna(100)
        cells[f"Timed HODL|{hl}"] = _cell(tm, round(float(cash_series.mean()), 1))
        # Per-horizon portfolio (fresh windowed book valued at the data-date close)
        portfolios[hl] = _horizon_portfolio(tbl, win, monthly, tsim["portfolio"], tm,
                                            scfg["slippage_bps"])
        # SIP
        ssim, scf = bt.simulate_sip(win, syms, monthly, scfg["slippage_bps"])
        sm = bt.nav_metrics(ssim, scf, "S")
        cells[f"SIP|{hl}"] = _cell(sm, None)
        # NIFTY 50
        nser = None
        if nifty is not None:
            nser, ncf = _nifty_sip_window(nifty[nifty.index >= hstart], monthly)
            nm = bt.nav_metrics(nser, ncf, "N")
            cells[f"NIFTY 50|{hl}"] = _cell(nm, None)
        # per-horizon curves (downsampled for the dashboard charts)
        eq = {"Timed HODL": _downsample(tsim["portfolio"]), "SIP": _downsample(ssim["portfolio"])}
        dd = {"Timed HODL": _downsample(_drawdown(tsim["portfolio"])),
              "SIP": _downsample(_drawdown(ssim["portfolio"]))}
        if nser is not None:
            eq["NIFTY 50"] = _downsample(nser)
        curves[hl] = {"equity": eq, "drawdown": dd, "cash": _downsample(cash_series)}
    gated = bool(bt.BUY_REQUIRE_BELOW_MID)
    bt.BUY_REQUIRE_BELOW_MID = prev_gate
    return {
        "gated": gated,
        "contribution": "salary model (₹22k/mo from 2010, +10%/yr, 25% invested)",
        "horizons": [h for h, _ in HORIZONS],
        "strategies": ["Timed HODL", "SIP", "NIFTY 50"],
        "metrics": STRAT_METRICS,
        "cells": cells,
        "curves": curves,
        "portfolios": portfolios,
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
        "contribution": "salary model (₹22k/mo from 2010, +10%/yr, 25% invested)",
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

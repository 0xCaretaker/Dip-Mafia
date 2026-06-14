#!/usr/bin/env python3
"""
Data layer for the unified Dip Mafia dashboard.

Emits a single JS data file consumed by the hand-authored ``docs/index.html``
app (designed separately):

    docs/strat_data.js   ->   window.STRAT_DATA = { portfolio, backtest,
                                                     iterations, horizons_grid }

It no longer generates any HTML. The portfolio block now includes a
*reconstructed daily NAV curve* (shares-held-over-time x historical close) so
the Portfolio section can show a real equity curve and true 1Y/3Y/5Y/10Y/All
returns - not just an all-time snapshot.

Reads (from the newest run subfolder under backtest_output/, via run_paths):
  - <current run>/trades.csv          holdings + buy history (Timed HODL rows)
  - <current run>/dashboard_data.json  backtest results (from backtest.py)
  - <current run>/horizons.json        per-horizon strategy + watchlist metrics
  - backtest_output/six7/_price_cache.pkl   historical daily close (NAV rebuild)

Run: python3 analysis/portfolio_view.py   (from the repo root)
Output: docs/strat_data.js
"""

import json
import os
import pickle
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

import run_paths
import backtest as bt   # compute_xirr / download_batch

warnings.filterwarnings("ignore")

CURRENT_RUN = run_paths.current_run() or run_paths.BASE
TRADES_CSV = os.path.join(CURRENT_RUN, "trades.csv")
BACKTEST_JSON = os.path.join(CURRENT_RUN, "dashboard_data.json")
HORIZONS_JSON = os.path.join(CURRENT_RUN, "horizons.json")
PRICE_CACHE = os.path.join(run_paths.SIX7, "_price_cache.pkl")
STRATEGY = "Timed HODL"
TIMED_KEY = "Your Strategy (Timed HODL)"
DOCS_DIR = "docs"

# Global horizon set shared with the frontend. (label, years; None = full history)
HORIZONS = [("1Y", 1), ("3Y", 3), ("5Y", 5), ("10Y", 10), ("All", None)]


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


# ─── Portfolio holdings ──────────────────────────────────────────────────────

def load_holdings():
    df = pd.read_csv(TRADES_CSV, parse_dates=["date"])
    df = df[df["strategy"] == STRATEGY].copy()
    df["shares"] = df["amount"] / df["price"]

    holdings = df.groupby("stock").agg(
        total_invested=("amount", "sum"),
        total_shares=("shares", "sum"),
        num_buys=("amount", "count"),
        first_buy=("date", "min"),
        last_buy=("date", "max"),
    ).reset_index()
    holdings["avg_price"] = holdings["total_invested"] / holdings["total_shares"]

    trades_by_stock = {}
    for stock, group in df.groupby("stock"):
        trades_by_stock[stock] = group[["date", "price", "amount"]].to_dict("records")

    return holdings, trades_by_stock, df


def fetch_current_prices(stocks):
    tickers = [f"{s}.NS" for s in stocks]
    data = yf.download(tickers, period="5d", interval="1d", progress=False)
    prices = {}
    for stock in stocks:
        ticker = f"{stock}.NS"
        try:
            if isinstance(data.columns, pd.MultiIndex):
                col = data["Close"][ticker].dropna()
            else:
                col = data["Close"].dropna()
            prices[stock] = float(col.iloc[-1])
        except (KeyError, IndexError):
            prices[stock] = np.nan
    return prices


def build_portfolio(holdings, prices):
    holdings["current_price"] = holdings["stock"].map(prices)
    holdings["current_value"] = holdings["total_shares"] * holdings["current_price"]
    holdings["pnl"] = holdings["current_value"] - holdings["total_invested"]
    holdings["return_pct"] = (holdings["pnl"] / holdings["total_invested"]) * 100
    holdings["weight_pct"] = (holdings["current_value"] / holdings["current_value"].sum()) * 100
    return holdings.sort_values("current_value", ascending=False).reset_index(drop=True)


def build_portfolio_json(p, trades_by_stock):
    total_invested = p["total_invested"].sum()
    total_value = p["current_value"].sum()
    total_pnl = total_value - total_invested
    total_ret = (total_pnl / total_invested) * 100
    winners = int((p["pnl"] > 0).sum())
    losers = int((p["pnl"] <= 0).sum())
    best = p.loc[p["return_pct"].idxmax()]
    worst = p.loc[p["return_pct"].idxmin()]

    rows = []
    for _, r in p.iterrows():
        stock = r["stock"]
        trades = trades_by_stock.get(stock, [])
        trade_list = []
        for t in trades:
            d = t["date"].strftime("%Y-%m-%d") if hasattr(t["date"], "strftime") else str(t["date"])[:10]
            trade_list.append({"date": d, "price": round(float(t["price"]), 2),
                               "shares": round(t["amount"] / t["price"], 2),
                               "amount": round(float(t["amount"]))})
        rows.append({
            "stock": stock,
            "avg_price": round(r["avg_price"], 2),
            "cmp": round(r["current_price"], 2),
            "shares": round(r["total_shares"], 1),
            "invested": round(r["total_invested"]),
            "value": round(r["current_value"]),
            "pnl": round(r["pnl"]),
            "ret": round(r["return_pct"], 1),
            "weight": round(r["weight_pct"], 1),
            "num_buys": int(r["num_buys"]),
            "first_buy": r["first_buy"].strftime("%Y-%m-%d"),
            "last_buy": r["last_buy"].strftime("%Y-%m-%d"),
            "trades": trade_list,
        })

    top_n = 10
    alloc_labels = list(p.head(top_n)["stock"])
    alloc_values = [float(v) for v in p.head(top_n)["current_value"].round(0)]
    if len(p) > top_n:
        alloc_labels.append("Others")
        alloc_values.append(float(round(p.iloc[top_n:]["current_value"].sum())))

    pnl_sorted = p.sort_values("pnl", ascending=True)

    return {
        "rows": rows,
        "summary": {
            "total_invested": round(total_invested),
            "total_value": round(total_value),
            "total_pnl": round(total_pnl),
            "total_ret": round(total_ret, 1),
            "winners": winners,
            "losers": losers,
            "best_stock": best["stock"],
            "best_ret": round(best["return_pct"]),
            "worst_stock": worst["stock"],
            "worst_ret": round(worst["return_pct"]),
            "count": len(p),
        },
        "alloc": {"labels": alloc_labels, "values": alloc_values},
        "pnl": {"labels": list(pnl_sorted["stock"]),
                "values": [float(v) for v in pnl_sorted["pnl"].round(0)]},
    }


# ─── Portfolio NAV reconstruction ────────────────────────────────────────────

def load_price_history(stocks):
    """Daily Close per bare symbol: six7 cache first, then download the rest."""
    hist = {}
    if os.path.isfile(PRICE_CACHE):
        raw = pickle.load(open(PRICE_CACHE, "rb")).get("stock_dfs", {})
        for ksym, df in raw.items():
            bare = ksym[:-3] if ksym.endswith(".NS") else ksym
            if bare in stocks and "Close" in df:
                s = df["Close"].dropna()
                if not s.empty:
                    hist[bare] = s
    missing = [s for s in stocks if s not in hist]
    if missing:
        print(f"  NAV: {len(missing)} symbols not cached, downloading...")
        cfg = {"start": "2010-01-01", "end": str(pd.Timestamp.now().date())}
        try:
            for sym, df in bt.download_batch(missing, cfg).items():
                if "Close" in df:
                    s = df["Close"].dropna()
                    if not s.empty:
                        hist[sym] = s
        except Exception as e:
            print(f"  NAV: download failed for {len(missing)} symbols ({e})")
    return hist


def build_portfolio_nav(df, prices):
    """Daily portfolio market value + cumulative invested, reconstructed from the
    Timed HODL buy ledger and historical close. A live 'today' endpoint is
    appended so the curve ends at the same current value the summary cards show.

    Returns (nav_dict, df_with_dates) where nav_dict = {dates, value, invested}.
    """
    stocks = sorted(df["stock"].unique())
    hist = load_price_history(stocks)
    first_buy = df["date"].min()

    # Master trading-day index: union of all holdings' price dates from first buy.
    idx = sorted({d for s in hist.values() for d in s.index if d >= first_buy})
    if not idx:
        return None
    index = pd.DatetimeIndex(idx)

    total_value = pd.Series(0.0, index=index)
    for stock, g in df.groupby("stock"):
        if stock not in hist:
            continue
        close = hist[stock].reindex(index).ffill()
        shares_by_date = g.groupby("date")["shares"].sum().sort_index().cumsum()
        held = shares_by_date.reindex(index, method="ffill").fillna(0.0)
        total_value = total_value.add((held * close).fillna(0.0), fill_value=0.0)

    invested = (df.groupby("date")["amount"].sum().sort_index().cumsum()
                .reindex(index, method="ffill").fillna(0.0))

    dates = [d.strftime("%Y-%m-%d") for d in index]
    value = [round(float(v)) for v in total_value.values]
    inv = [round(float(v)) for v in invested.values]

    # Append a live endpoint (today) valued at current prices, so NAV-last ==
    # the summary's current value. Only count holdings with a live price.
    today = pd.Timestamp.now().normalize()
    if today > index[-1]:
        cur_val = 0.0
        for stock, g in df.groupby("stock"):
            px = prices.get(stock)
            if px is not None and not (isinstance(px, float) and np.isnan(px)):
                cur_val += g["shares"].sum() * px
        dates.append(today.strftime("%Y-%m-%d"))
        value.append(round(float(cur_val)))
        inv.append(inv[-1])

    return {"dates": dates, "value": value, "invested": inv}


def portfolio_horizons(nav, df):
    """Per-horizon portfolio performance from the reconstructed NAV.

    For each window we measure the money-weighted return (XIRR) on the capital at
    work: the opening market value plus every buy inside the window, against the
    closing value. ``ret`` is the simple profit over that deployed capital.
    """
    if not nav:
        return {}
    d = pd.to_datetime(nav["dates"])
    val = pd.Series(nav["value"], index=d)
    inv = pd.Series(nav["invested"], index=d)
    end_dt = d[-1]
    v_now = float(val.iloc[-1])
    buys = df[["date", "amount"]].copy()

    out = {}
    for label, yrs in HORIZONS:
        start = d[0] if yrs is None else end_dt - pd.DateOffset(years=yrs)
        if start <= d[0]:
            start, v_then, inv_then = d[0], 0.0, 0.0
        else:
            prior = val.index[val.index <= start]
            if len(prior) == 0:
                v_then = inv_then = 0.0
            else:
                at = prior[-1]
                v_then = float(val.loc[at]); inv_then = float(inv.loc[at])
        win_buys = buys[(buys["date"] > start) & (buys["date"] <= end_dt)]
        contrib = float(win_buys["amount"].sum())
        if yrs is None:                       # All: capital = full invested basis
            capital = float(inv.iloc[-1])
        else:
            capital = v_then + contrib
        pnl = v_now - capital
        ret = round(pnl / capital * 100, 1) if capital > 0 else None

        cfs = []
        if v_then > 0:
            cfs.append((start, -v_then))
        for _, b in win_buys.iterrows():
            cfs.append((b["date"], -float(b["amount"])))
        xirr = None
        if cfs:
            x = bt.compute_xirr(cfs, v_now, end_dt)
            xirr = None if (x is None or (isinstance(x, float) and np.isnan(x))) else round(float(x), 1)

        out[label] = {"ret": ret, "value": round(v_now), "invested": round(capital),
                      "pnl": round(pnl), "xirr": xirr,
                      "start": start.strftime("%Y-%m-%d"), "end": end_dt.strftime("%Y-%m-%d")}
    return out


# ─── Backtest reshape ────────────────────────────────────────────────────────

def reshape_backtest(backtest_data, horizons):
    """Pass the backtest payload through, attaching the expanded per-horizon ×
    per-strategy metric grid from horizons.json (strategy_horizons)."""
    if not backtest_data:
        return None
    sh = (horizons or {}).get("strategy_horizons") or {}
    label_map = {"1y": "1Y", "3y": "3Y", "5y": "5Y", "10y": "10Y", "Full": "All"}
    cells = {}
    for k, v in (sh.get("cells") or {}).items():
        strat, hl = k.rsplit("|", 1)
        cells[f"{strat}|{label_map.get(hl, hl)}"] = v
    backtest_data["horizon_metrics"] = {
        "horizons": [label_map.get(h, h) for h in (sh.get("horizons") or [])],
        "strategies": sh.get("strategies") or ["Timed HODL", "SIP", "NIFTY 50"],
        "metrics": sh.get("metrics") or [],
        "cells": cells,
        "gated": sh.get("gated"),
        "contribution": sh.get("contribution"),
    }
    return backtest_data


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("Loading trades...")
    holdings, trades_by_stock, df = load_holdings()
    print(f"Found {len(holdings)} stocks in {STRATEGY} strategy")

    print("Fetching current prices...")
    prices = fetch_current_prices(holdings["stock"].tolist())

    portfolio = build_portfolio(holdings, prices)
    valid = portfolio.dropna(subset=["current_price"])
    skipped = portfolio[portfolio["current_price"].isna()]
    if len(skipped):
        print(f"  Skipped {len(skipped)} stocks (no price data): {', '.join(skipped['stock'])}")

    portfolio_data = build_portfolio_json(valid, trades_by_stock)

    print("Reconstructing portfolio NAV...")
    nav = build_portfolio_nav(df, prices)
    portfolio_data["nav"] = nav
    portfolio_data["horizon"] = portfolio_horizons(nav, df)
    if nav:
        print(f"  NAV: {len(nav['dates'])} daily points, "
              f"{nav['dates'][0]} → {nav['dates'][-1]}")

    backtest_data = None
    try:
        with open(BACKTEST_JSON) as f:
            backtest_data = json.load(f)
        print(f"  Loaded backtest data from {BACKTEST_JSON}")
    except FileNotFoundError:
        print(f"  No backtest data ({BACKTEST_JSON})")

    horizons = None
    try:
        with open(HORIZONS_JSON) as f:
            horizons = json.load(f)
        print(f"  Loaded horizons.json ({len(horizons.get('cells', {}))} grid cells)")
    except (FileNotFoundError, json.JSONDecodeError):
        print("  No horizons.json (run horizon_compare.py first)")

    backtest_data = reshape_backtest(backtest_data, horizons)
    iterations = load_iterations(json.load(open(BACKTEST_JSON)) if os.path.isfile(BACKTEST_JSON) else None)
    n_arch = max(0, len(iterations) - 1)
    if n_arch:
        print(f"  Iterations: current + {n_arch} archived run(s)")

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_run": os.path.basename(CURRENT_RUN),
        "end_date": (horizons or {}).get("end_date"),
        "horizon_set": [h for h, _ in HORIZONS],
        "portfolio": portfolio_data,
        "backtest": backtest_data,
        "iterations": iterations,
        "horizons_grid": horizons,
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

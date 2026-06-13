#!/usr/bin/env python3
"""Backtest the six7 stock lists (+ current stocks.txt) across multiple horizons.

Reuses the simulation + chart core of backtest.py (same CONFIG, same BB200/2sigma
gate + Impulse MACD Timed HODL, SIP, NIFTY 50 benchmark). It:

  1. Downloads the union of all list tickers + NIFTY once, over full history.
  2. Computes BB + Impulse signals once on full history (so indicators are fully
     warmed up even for short horizons -- a 1y window still uses the prior 200+
     bars to form BB-200, the simulation just starts counting at the window).
  3. Runs every list over 5 horizons -- full (~16y), trailing 10y / 5y / 3y / 1y,
     all ending at the latest date -- and writes a comparison table+chart per
     horizon (the full-horizon table also shows the old saved 61-stock run).
  4. Generates the full 8-chart suite (like a normal run) for every list on
     the full horizon, into backtest_output/six7/<list>/.

backtest.py's own run subfolders under backtest_output/ are left untouched;
chart output is redirected by setting bt.OUTPUT_DIR per list.

CAVEAT (labelled in output): the lists are a *current* (2026-06-01) fundamental
screen, so this is survivorship/look-ahead-biased hindsight -- good for ranking
lists against each other and across horizons, NOT a tradeable signal.

Run: python3 analysis/backtest_six7.py   (from the repo root)
"""

import os
import csv
import json
import copy
import pickle

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import backtest as bt
import run_paths

LISTS_DIR = "six7_stocks/lists"
STOCKS_TXT = "stocks.txt"
OUT_DIR = run_paths.SIX7
OLD_DASHBOARD = os.path.join(run_paths.current_run() or run_paths.BASE, "dashboard_data.json")

# six7 lists first, then the live portfolio. stocks_current is read from stocks.txt.
SIX7_LISTS = ["top10", "top30", "top50", "top100",
              "strong_buy", "buy_plus", "six_plus", "perfect7"]

END = "2026-06-03"   # latest; all trailing windows end here
HORIZONS = [          # (label, start_date) -- end is END for all
    ("full", "2010-01-01"),
    ("10y", "2016-06-03"),
    ("5y", "2021-06-03"),
    ("3y", "2023-06-03"),
    ("1y", "2025-06-03"),
]
# Short windows use a flat monthly SIP instead of the 2010 salary-growth model
# (a recent investor putting in a fixed amount). full/10y keep the salary model.
FLAT_MONTHLY = {"5y": 20000, "3y": 20000, "1y": 20000}


def build_schedule(dates, cfg, flat):
    """Monthly investment schedule: flat ₹/mo if `flat` set, else the salary model."""
    if not flat:
        return bt.build_monthly_investments(dates, cfg)
    inv = {}
    for dt in sorted(dates):
        key = (dt.year, dt.month)
        if key not in inv:
            inv[key] = {"date": dt, "amount": float(flat)}
    return inv

C_TIMED, C_SIP, C_NIFTY, C_GRAY = "#4CAF50", "#2196F3", "#9C27B0", "#9E9E9E"


# ── inputs ────────────────────────────────────────────────────────────────────

def load_lists():
    lists = {}
    for name in SIX7_LISTS:
        path = os.path.join(LISTS_DIR, f"{name}.txt")
        if os.path.isfile(path):
            with open(path) as f:
                syms = [ln.strip() for ln in f if ln.strip()]
            if syms:
                lists[name] = syms
    # Univest Old = the Univest base before six7's perfect-stock auto-additions
    # (current stocks.txt minus the six7-added tickers). Run across every horizon.
    uo = os.path.join(LISTS_DIR, "univest_old.txt")
    if os.path.isfile(uo):
        with open(uo) as f:
            syms = [ln.strip() for ln in f if ln.strip()]
        if syms:
            lists["univest_old"] = syms
    # Univest + six7 Hybrid = the live watchlist (current stocks.txt)
    if os.path.isfile(STOCKS_TXT):
        with open(STOCKS_TXT) as f:
            syms = [ln.strip() for ln in f if ln.strip()]
        if syms:
            lists["stocks_current"] = syms
    return lists


# ── windowed simulation (signals precomputed on full history) ──────────────────

def slice_window(stock_dfs, start):
    ts = pd.Timestamp(start)
    out = {}
    for s, df in stock_dfs.items():
        w = df[df.index >= ts]
        if not w.empty:
            out[s] = w
    return out


def nifty_sip(nifty_data, monthly_inv, slippage_bps=5):
    units = cash = 0.0
    done, records, cashflows = set(), [], []
    for dt, row in nifty_data.iterrows():
        price = row["Close"]
        key = (dt.year, dt.month)
        if key in monthly_inv and key not in done:
            amt = monthly_inv[key]["amount"]
            cash += amt; done.add(key); cashflows.append((dt, -amt))
            units += cash / (price * (1 + slippage_bps / 10000))
            cash = 0.0
        records.append({"date": dt, "portfolio": units * price + cash})
    return pd.DataFrame(records).set_index("date"), cashflows


def nav_metrics(sim_df, cashflows, name):
    """Metrics where risk is measured on the cash-flow-adjusted NAV (unit value).

    Sharpe/Sortino/MaxDD/volatility/CAGR on the raw accumulating portfolio value
    are meaningless — monthly contributions show up as always-positive daily
    "returns", so a money-losing SIP can post a high Sharpe. The NAV (unit value)
    strips contributions, giving the true time-weighted risk profile. Final value
    and XIRR stay money-weighted (computed on the value series + cashflows).
    """
    nav = bt._compute_nav(sim_df, cashflows)
    m = bt.compute_metrics(nav, name)                       # risk metrics from NAV
    vm = bt.compute_metrics(sim_df["portfolio"], name, cashflows)
    m["final_value"] = vm["final_value"]                    # money-weighted final
    m["xirr"] = vm["xirr"]                                  # money-weighted return
    return m


def bench_row(key, index_data, cfg, hstart, flat=None):
    """Benchmark row: SIP the same monthly money into an index over the window."""
    if index_data is None:
        return None
    bd = index_data[index_data.index >= pd.Timestamp(hstart)]
    if bd.empty:
        return None
    minv = build_schedule(sorted(bd.index), cfg, flat)
    sim, cf = nifty_sip(bd, minv, cfg["slippage_bps"])
    m = nav_metrics(sim, cf, key)
    return {"list": key, "n_with_data": None,
            "total_invested": sum(v["amount"] for v in minv.values()),
            "start": str(sim.index[0].date()), "end": str(sim.index[-1].date()),
            "timed": m, "sip": {}, "nifty": None, "benchmark": True}


def run_metrics(name, syms_ns, stock_dfs_full, signals, cfg, hstart, nifty_data, flat=None):
    """Timed HODL + SIP + NIFTY over [hstart, END]; metrics only. Fast path."""
    bb, bb_mid, imp, imp_st = signals
    dfs = slice_window(stock_dfs_full, hstart)
    syms = [s for s in syms_ns if s in dfs and s in bb]
    if not syms:
        return None
    dates = bt.get_all_dates(dfs, syms)
    if len(dates) < 30:
        return None
    monthly_inv = build_schedule(dates, cfg, flat)
    timed, timed_cf, buy_log, _ = bt.simulate_timed_hodl(
        dfs, syms, monthly_inv, bb, bb_mid, imp, cfg["slippage_bps"])
    sip, sip_cf = bt.simulate_sip(dfs, syms, monthly_inv, cfg["slippage_bps"])
    nd = nifty_data[nifty_data.index >= pd.Timestamp(hstart)]
    nifty, nifty_cf = nifty_sip(nd, monthly_inv, cfg["slippage_bps"])
    return {
        "list": name, "n_with_data": len(syms),
        "total_invested": sum(v["amount"] for v in monthly_inv.values()),
        "start": str(timed.index[0].date()), "end": str(timed.index[-1].date()),
        "timed": nav_metrics(timed, timed_cf, bt.LABEL_TIMED),
        "sip": nav_metrics(sip, sip_cf, bt.LABEL_SIP),
        "nifty": nav_metrics(nifty, nifty_cf, bt.LABEL_NIFTY),
    }


# ── full 8-chart suite (replicates backtest.main(), redirected per list) ───────

def run_full_suite(name, syms_ns, stock_dfs_full, signals, cfg, nifty_price):
    bb, bb_mid, imp, imp_st = signals
    syms = [s for s in syms_ns if s in stock_dfs_full and s in bb]
    if not syms:
        print(f"  [{name}] no signal-ready stocks; skipping suite")
        return None
    out_dir = os.path.join(OUT_DIR, name)
    os.makedirs(out_dir, exist_ok=True)
    bt.OUTPUT_DIR = out_dir   # redirect every chart writer + dashboard json

    dfs = stock_dfs_full
    dates = bt.get_all_dates(dfs, syms)
    monthly_inv = bt.build_monthly_investments(dates, cfg)
    total_invested = sum(v["amount"] for v in monthly_inv.values())

    sip_sim, sip_cf = bt.simulate_sip(dfs, syms, monthly_inv, cfg["slippage_bps"])
    timed_sim, timed_cf, buy_log, idle = bt.simulate_timed_hodl(
        dfs, syms, monthly_inv, bb, bb_mid, imp, cfg["slippage_bps"])
    partial_sim, partial_cf, _ = bt.simulate_partial_sip(
        dfs, syms, monthly_inv, bb, bb_mid, imp, cfg["slippage_bps"])
    exit_sim, exit_cf, trade_log = bt.simulate_timed_exit(
        dfs, syms, monthly_inv, bb, imp, imp_st, cfg["slippage_bps"])
    nifty_sim, nifty_cf = bt.simulate_nifty_sip(cfg, monthly_inv)

    m_timed = bt.compute_metrics(timed_sim["portfolio"], bt.LABEL_TIMED, timed_cf)
    m_sip = bt.compute_metrics(sip_sim["portfolio"], bt.LABEL_SIP, sip_cf)
    m_partial = bt.compute_metrics(partial_sim["portfolio"], bt.LABEL_PARTIAL, partial_cf)
    m_exit = bt.compute_metrics(exit_sim["portfolio"], bt.LABEL_EXIT, exit_cf)
    m_nifty = bt.compute_metrics(nifty_sim["portfolio"], bt.LABEL_NIFTY, nifty_cf) if nifty_sim is not None else None

    portfolios = {bt.LABEL_TIMED: timed_sim["portfolio"], bt.LABEL_SIP: sip_sim["portfolio"],
                  bt.LABEL_PARTIAL: partial_sim["portfolio"], bt.LABEL_EXIT: exit_sim["portfolio"]}
    nifty_series = nifty_sim["portfolio"] if nifty_sim is not None else None
    metrics_list = [m_timed, m_partial, m_sip, m_exit] + ([m_nifty] if m_nifty else [])

    buy_dates = {b["date"] for b in buy_log}
    stocks_bought = {b["stock"] for b in buy_log}
    cash_total = timed_sim["portfolio"].replace(0, np.nan)
    cash_pct = (timed_sim["cash"] / cash_total * 100).fillna(100).mean()
    max_idle = max(idle) if idle else 0
    avg_idle = np.mean(idle) if idle else 0
    assumptions = bt.compute_investment_assumptions(cfg, dates)

    bt.chart_1_equity(portfolios, nifty_series, total_invested, "1_equity_curves.png")
    bt.chart_2_drawdowns(portfolios, nifty_series, "2_drawdowns.png")
    bt.chart_3_cash(timed_sim, exit_sim, "3_cash_utilization.png")
    nav_series = {bt.LABEL_TIMED: bt._compute_nav(timed_sim, timed_cf),
                  bt.LABEL_PARTIAL: bt._compute_nav(partial_sim, partial_cf),
                  bt.LABEL_SIP: bt._compute_nav(sip_sim, sip_cf)}
    bt.chart_4_regimes(nav_series, nifty_price, "4_regime_returns.png")
    bt.chart_5_rolling_alpha(portfolios, "5_rolling_alpha.png")
    bt.chart_6_buy_distribution(buy_log, len(syms), "6_buy_distribution.png")
    bt.chart_7_buy_timeline(buy_log, "7_buy_timeline.png")
    bt.chart_8_summary_table(metrics_list, total_invested, len(syms), len(buy_dates),
                             len(stocks_bought), assumptions, "8_summary_table.png", max_idle, avg_idle)
    bt.write_trade_log(buy_log, trade_log, monthly_inv, timed_sim, os.path.join(out_dir, "trades.csv"))
    bt.save_dashboard_data(portfolios, nifty_series, timed_sim, exit_sim, nav_series, nifty_price,
                           metrics_list, buy_log, total_invested, assumptions, idle,
                           len(syms), len(buy_dates), len(stocks_bought), cash_pct, "dashboard_data.json")
    n_charts = len([f for f in os.listdir(out_dir) if f.endswith(".png")])
    print(f"  [{name}] {len(syms)} stocks | Timed ₹{m_timed['final_value']/100000:.1f}L "
          f"XIRR {m_timed['xirr']:.1f}% | {n_charts} charts -> {out_dir}/")
    return {"list": name, "n_with_data": len(syms), "total_invested": total_invested,
            "start": str(timed_sim.index[0].date()), "end": str(timed_sim.index[-1].date()),
            "timed": nav_metrics(timed_sim, timed_cf, bt.LABEL_TIMED),
            "sip": nav_metrics(sip_sim, sip_cf, bt.LABEL_SIP),
            "nifty": nav_metrics(nifty_sim, nifty_cf, bt.LABEL_NIFTY) if nifty_sim is not None else None}


# ── comparison output (per horizon) ────────────────────────────────────────────

FIELDS = [("list", "List"), ("n_with_data", "Stocks"), ("total_invested", "Invested"),
          ("timed_final", "Timed ₹"), ("timed_xirr", "Timed XIRR%"), ("timed_sharpe", "Sharpe"),
          ("timed_sortino", "Sortino"), ("timed_maxdd", "MaxDD%"),
          ("sip_final", "SIP ₹"), ("sip_xirr", "SIP XIRR%")]


def flat_row(r):
    t, s = r["timed"], r["sip"]
    return {"list": r["list"], "n_with_data": r["n_with_data"], "total_invested": r["total_invested"],
            "timed_final": t.get("final_value"), "timed_xirr": t.get("xirr"),
            "timed_sharpe": t.get("sharpe"), "timed_sortino": t.get("sortino"),
            "timed_maxdd": t.get("max_drawdown"),
            "sip_final": s.get("final_value"), "sip_xirr": s.get("xirr")}


def old_baseline():
    if not os.path.isfile(OLD_DASHBOARD):
        return None
    d = json.load(open(OLD_DASHBOARD))
    by = {m["name"]: m for m in d["metrics"]}
    return {"list": "stocks.txt (OLD 61)", "n_with_data": d["summary"]["n_stocks"],
            "total_invested": d["total_invested"], "timed": by.get(bt.LABEL_TIMED, {}),
            "sip": by.get(bt.LABEL_SIP, {}), "nifty": by.get(bt.LABEL_NIFTY)}


def fmt(k, v):
    if v is None: return "-"
    if k in ("total_invested",) or k.endswith("_final"): return f"₹{v/100000:.1f}L"
    if k.endswith(("xirr", "maxdd")): return f"{v:.1f}"
    if k in ("timed_sharpe", "timed_sortino"): return f"{v:.2f}"
    return f"{v}"


def write_comparison(horizon, period, results):
    rows = [flat_row(r) for r in results]
    csv_path = os.path.join(OUT_DIR, f"comparison_{horizon}.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([h for _, h in FIELDS])
        for row in rows:
            w.writerow([row[k] for k, _ in FIELDS])
    # raw (unformatted) numbers for the web build
    with open(os.path.join(OUT_DIR, f"comparison_{horizon}.json"), "w") as f:
        json.dump({"horizon": horizon, "period": period, "results": results}, f, default=float)

    six7 = [r for r in rows if "OLD" not in r["list"] and r["timed_final"]]
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 1.0], hspace=0.3)
    ax0 = fig.add_subplot(gs[0]); ax0.axis("off")
    table = ax0.table(cellText=[[fmt(k, row[k]) for k, _ in FIELDS] for row in rows],
                      colLabels=[h for _, h in FIELDS], cellLoc="center", loc="center")
    table.auto_set_font_size(False); table.set_fontsize(9); table.scale(1, 1.55)
    for j in range(len(FIELDS)):
        table[(0, j)].set_facecolor("#263238"); table[(0, j)].set_text_props(color="white", fontweight="bold")
    is_ref = lambda nm: "OLD" in nm or nm.startswith("nifty")
    best = max(range(len(rows)), key=lambda i: (rows[i]["timed_final"] or 0) if not is_ref(rows[i]["list"]) else -1)
    for i, row in enumerate(rows, start=1):
        if "OLD" in row["list"]:
            for j in range(len(FIELDS)): table[(i, j)].set_facecolor("#FFF3E0")
    for j in range(len(FIELDS)):
        table[(best + 1, j)].set_facecolor("#E8F5E9")
    ax0.set_title(f"six7 lists vs stocks.txt — {horizon.upper()} ({period})  ·  Timed HODL & SIP  "
                  f"(current-screen hindsight)", fontsize=13, fontweight="bold", pad=14)

    ax1 = fig.add_subplot(gs[1])
    labels = [r["list"] for r in rows]
    tv = [(r["timed_final"] or 0) / 100000 for r in rows]
    sv = [(r["sip_final"] or 0) / 100000 for r in rows]
    x = np.arange(len(labels)); w = 0.38
    ax1.bar(x - w/2, tv, w, color=C_TIMED, label="Timed HODL")
    ax1.bar(x + w/2, sv, w, color=C_SIP, label="SIP")
    ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("Final value (₹L)"); ax1.grid(True, axis="y", alpha=0.3); ax1.legend(fontsize=10)
    ax1.set_title(f"Final portfolio value by list — {horizon.upper()}", fontsize=12, fontweight="bold")
    for i, v in enumerate(tv):
        ax1.annotate(f"{v:.1f}" if v < 10 else f"{v:.0f}", (x[i] - w/2, v),
                     ha="center", va="bottom", fontsize=7.5)
    fig.savefig(os.path.join(OUT_DIR, f"comparison_{horizon}.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  comparison_{horizon}.{{csv,png}} written ({len(rows)} rows)")


# ── orchestration ──────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    lists = load_lists()
    print(f"Lists ({len(lists)}): {', '.join(lists)}")

    full_cfg = copy.deepcopy(bt.CONFIG); full_cfg["start"], full_cfg["end"] = "2010-01-01", END
    union = sorted({s for syms in lists.values() for s in syms})
    tickers = [s + ".NS" for s in union]

    # Price cache: downloads are flaky + slow, so persist the union + NIFTY keyed
    # on the ticker set and end date. Reuse on rebuilds (also makes runs reproducible).
    cache_path = os.path.join(OUT_DIR, "_price_cache.pkl")
    cache_key = (tuple(tickers), END)
    stock_dfs = nifty_data = None
    if os.path.isfile(cache_path):
        try:
            cached = pickle.load(open(cache_path, "rb"))
            if cached.get("key") == cache_key:
                stock_dfs, nifty_data = cached["stock_dfs"], cached["nifty_data"]
                print(f"\nUsing cached prices for {len(stock_dfs)} tickers (delete {cache_path} to refresh).")
        except Exception:
            pass
    if stock_dfs is None:
        print(f"\nDownloading union of {len(tickers)} tickers over full history (single pass)...")
        stock_dfs = bt.download_batch(tickers, full_cfg)
        print(f"  price history: {len(stock_dfs)}/{len(tickers)} tickers")
        print("Downloading NIFTY 50 (full history, reused everywhere)...")
        nraw = yf.download("^NSEI", start="2010-01-01", end=END, progress=False)
        nifty_data = bt.flatten_cols(nraw).dropna() if not nraw.empty else None
        pickle.dump({"key": cache_key, "stock_dfs": stock_dfs, "nifty_data": nifty_data},
                    open(cache_path, "wb"))
    nifty_price = nifty_data["Close"] if nifty_data is not None else None

    # NIFTY Midcap 100 benchmark (downloaded separately so it doesn't churn the
    # union price cache). Cached in its own small file.
    mid_cache = os.path.join(OUT_DIR, "_midcap_cache.pkl")
    midcap_data = None
    if os.path.isfile(mid_cache):
        try:
            mc = pickle.load(open(mid_cache, "rb"))
            if mc.get("end") == END:
                midcap_data = mc["data"]
        except Exception:
            pass
    if midcap_data is None:
        print("Downloading NIFTY Midcap 100...")
        mraw = yf.download("NIFTY_MIDCAP_100.NS", start="2010-01-01", end=END, progress=False)
        midcap_data = bt.flatten_cols(mraw).dropna() if not mraw.empty else None
        pickle.dump({"end": END, "data": midcap_data}, open(mid_cache, "wb"))
    BENCH = [("nifty50", nifty_data), ("nifty_midcap", midcap_data)]

    print("Computing BB + Impulse signals on full history (once)...")
    bb, bb_mid, imp, imp_st, skipped = bt.generate_all_signals(stock_dfs, full_cfg)
    signals = (bb, bb_mid, imp, imp_st)
    print(f"  signals ready for {len(bb)} stocks ({len(skipped)} skipped: short history)")

    # 1) full 8-chart suite per list (full horizon)
    print("\n── Full 8-chart suite per list (full horizon) ──")
    full_results = []
    for name, syms in lists.items():
        r = run_full_suite(name, [s + ".NS" for s in syms], stock_dfs, signals, full_cfg, nifty_price)
        if r:
            full_results.append(r)

    # 2) comparison per horizon
    print("\n── Comparison per horizon ──")
    for label, start in HORIZONS:
        cfg = copy.deepcopy(bt.CONFIG); cfg["start"], cfg["end"] = start, END
        period = f"{start} → {END}"
        flat = FLAT_MONTHLY.get(label)
        if label == "full":
            results = full_results[:]            # reuse the suite metrics
        else:
            results = []
            for name, syms in lists.items():
                r = run_metrics(name, [s + ".NS" for s in syms], stock_dfs, signals, cfg, start, nifty_data, flat)
                if r:
                    results.append(r)
        # index benchmarks (same monthly money SIP'd into the index)
        for bkey, bdata in BENCH:
            br = bench_row(bkey, bdata, cfg, start, flat)
            if br:
                results.append(br)
        write_comparison(label, period, results)

    print("\nDone.")


if __name__ == "__main__":
    main()

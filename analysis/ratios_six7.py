#!/usr/bin/env python3
"""Extended risk/return ratios for the six7 almanac lists (Timed HODL vs SIP).

backtest_six7.py reports XIRR, Sharpe, Sortino and max drawdown. This adds the
rest of the usual ratio set, for any set of lists and any end date, so an
archived screen can be compared with a new one on the same window:

  NAV-based (daily, on the contribution-stripped unit NAV, like nav_metrics):
    CAGR (time-weighted), volatility, Sharpe, Sortino, Calmar,
    profit factor = sum of positive daily returns / |sum of negative| (== Omega at 0),
    Ulcer index (RMS drawdown, %) and Martin ratio = (CAGR - rf) / Ulcer,
    hit rate = % of days up, max drawdown and its duration.
  Position-based (each stock's whole position, valued at the window's last close;
  the strategy never sells, so every position is open):
    position profit factor = sum of gains on stocks held at a profit
                             / |sum of losses on stocks held at a loss|,
    win rate = % of positions in profit, payoff = avg win % / |avg loss %|.

Same engine and schedule as backtest_six7 (signals on full history, salary
model for full/10y, flat Rs 20k/mo for 5y/3y/1y). Prices come from
backtest_output/six7/_price_cache.pkl; symbols it lacks are downloaded.

Run (from the repo root):
  python3 analysis/ratios_six7.py --lists analysis/six7_stocks/lists \
      --stocks stocks.txt --end 2026-10-07 --out <dir>
Writes <dir>/ratios.json.
"""

import argparse
import copy
import json
import os
import pickle

import numpy as np
import pandas as pd

import backtest as bt
import backtest_six7 as b7
import run_paths

RF_DAILY = 1.06 ** (1 / 252) - 1  # same 6% risk-free as backtest.compute_metrics


def nav_ratios(sim, cashflows):
    nav = bt._compute_nav(sim, cashflows)
    dr = nav.pct_change().dropna().replace([np.inf, -np.inf], 0)
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0.0
    ex = dr - RF_DAILY
    sharpe = np.sqrt(252) * ex.mean() / ex.std() if ex.std() > 0 else 0.0
    down = ex[ex < 0]
    sortino = np.sqrt(252) * ex.mean() / down.std() if len(down) and down.std() > 0 else 0.0
    dd = nav / nav.cummax() - 1
    max_dd = dd.min()
    run = longest = 0
    for x in dd:
        run = run + 1 if x < 0 else 0
        longest = max(longest, run)
    ulcer = float(np.sqrt((dd.pow(2)).mean())) * 100
    gains, losses = dr[dr > 0].sum(), -dr[dr < 0].sum()
    return {
        "cagr": cagr * 100,
        "vol": dr.std() * np.sqrt(252) * 100,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": cagr / abs(max_dd) if max_dd else 0.0,
        "profit_factor": gains / losses if losses > 0 else None,
        "ulcer": ulcer,
        "martin": (cagr - 0.06) * 100 / ulcer if ulcer > 0 else None,
        "hit_rate": (dr > 0).mean() * 100,
        "max_dd": max_dd * 100,
        "max_dd_days": longest,
    }


def position_ratios(cost, value):
    """cost/value: {stock: rupees}. Ratios over whole positions."""
    pnl = {s: value[s] - cost[s] for s in cost if cost[s] > 0}
    wins = [p for p in pnl.values() if p > 0]
    loss = [p for p in pnl.values() if p < 0]
    win_pct = [pnl[s] / cost[s] * 100 for s in pnl if pnl[s] > 0]
    loss_pct = [pnl[s] / cost[s] * 100 for s in pnl if pnl[s] < 0]
    return {
        "positions": len(pnl),
        "pos_profit_factor": sum(wins) / -sum(loss) if loss else None,
        "win_rate": len(wins) / len(pnl) * 100 if pnl else None,
        "payoff": (np.mean(win_pct) / -np.mean(loss_pct)) if win_pct and loss_pct else None,
    }


def timed_positions(buy_log, last_close, slip):
    cost, value = {}, {}
    for b in buy_log:
        s = b["stock"]
        sh = b["amount"] / (b["price"] * (1 + slip / 10000))
        cost[s] = cost.get(s, 0) + b["amount"]
        value[s] = value.get(s, 0) + sh * last_close[s]
    return cost, value


def sip_positions(dfs, syms, monthly_inv, slip):
    """Replays bt.simulate_sip's buys to get each stock's cost and shares."""
    cost = {s: 0.0 for s in syms}
    shares = {s: 0.0 for s in syms}
    done, cash = set(), 0.0
    for dt in bt.get_all_dates(dfs, syms):
        key = (dt.year, dt.month)
        if key in monthly_inv and key not in done:
            cash += monthly_inv[key]["amount"]; done.add(key)
            avail = [s for s in syms if dt in dfs[s].index]
            if avail:
                per = cash / len(avail)
                for s in avail:
                    shares[s] += per / (dfs[s].loc[dt, "Close"] * (1 + slip / 10000))
                    cost[s] += per
                cash = 0.0
    value = {s: shares[s] * dfs[s]["Close"].iloc[-1] for s in syms}
    return cost, value


def load_prices(tickers, end, cfg):
    cache = pickle.load(open(os.path.join(run_paths.SIX7, "_price_cache.pkl"), "rb"))
    cut = pd.Timestamp(end)
    have = cache["stock_dfs"]
    dfs = {t: have[t][have[t].index < cut] for t in tickers if t in have}
    missing = [t for t in tickers if t not in have]
    if missing:
        print(f"  downloading {len(missing)} symbols not in the price cache...")
        for t, df in bt.download_batch(missing, cfg).items():
            dfs[t] = df[df.index < cut]
    nd = cache["nifty_data"]
    return {t: d for t, d in dfs.items() if not d.empty}, nd[nd.index < cut]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lists", required=True, help="folder of <list>.txt files")
    ap.add_argument("--stocks", help="live-watchlist file, run as stocks_current")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    lists = {}
    for name in b7.SIX7_LISTS + ["univest_old"]:
        p = os.path.join(args.lists, f"{name}.txt")
        if os.path.isfile(p):
            lists[name] = [ln.strip() for ln in open(p) if ln.strip()]
    if args.stocks:
        lists["stocks_current"] = [ln.strip() for ln in open(args.stocks) if ln.strip()]

    full_cfg = copy.deepcopy(bt.CONFIG); full_cfg["start"], full_cfg["end"] = "2010-01-01", args.end
    tickers = sorted({s + ".NS" for syms in lists.values() for s in syms})
    stock_dfs, nifty = load_prices(tickers, args.end, full_cfg)
    bb, bb_mid, imp, _st, _sk = bt.generate_all_signals(stock_dfs, full_cfg)
    slip = full_cfg["slippage_bps"]

    out = {"end": args.end, "lists_dir": args.lists, "horizons": {}}
    for label, start in b7.horizons(args.end):
        cfg = copy.deepcopy(bt.CONFIG); cfg["start"], cfg["end"] = start, args.end
        flat = b7.FLAT_MONTHLY.get(label)
        rows = {}
        for name, syms in lists.items():
            dfs = b7.slice_window(stock_dfs, start)
            s_ns = [s + ".NS" for s in syms if s + ".NS" in dfs and s + ".NS" in bb]
            if not s_ns:
                continue
            dates = bt.get_all_dates(dfs, s_ns)
            if len(dates) < 30:
                continue
            monthly = b7.build_schedule(dates, cfg, flat)
            timed, timed_cf, buy_log, _ = bt.simulate_timed_hodl(dfs, s_ns, monthly, bb, bb_mid, imp, slip)
            sip, sip_cf = bt.simulate_sip(dfs, s_ns, monthly, slip)
            last = {s: dfs[s]["Close"].iloc[-1] for s in s_ns}
            rows[name] = {
                "n": len(s_ns),
                "timed": {**nav_ratios(timed, timed_cf),
                          "xirr": bt.compute_xirr(timed_cf, timed["portfolio"].iloc[-1], timed.index[-1]),
                          **position_ratios(*timed_positions(buy_log, last, slip))},
                "sip": {**nav_ratios(sip, sip_cf),
                        "xirr": bt.compute_xirr(sip_cf, sip["portfolio"].iloc[-1], sip.index[-1]),
                        **position_ratios(*sip_positions(dfs, s_ns, monthly, slip))},
            }
        nd = nifty[nifty.index >= pd.Timestamp(start)]
        nsim, ncf = b7.nifty_sip(nd, b7.build_schedule(bt.get_all_dates({"N": nd}, ["N"]), cfg, flat), slip)
        rows["nifty50"] = {"n": None, "timed": {**nav_ratios(nsim, ncf),
                           "xirr": bt.compute_xirr(ncf, nsim["portfolio"].iloc[-1], nsim.index[-1])}}
        out["horizons"][label] = {"start": start, "rows": rows}
        print(f"  {label}: {len(rows)} rows")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "ratios.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"wrote {os.path.join(args.out, 'ratios.json')}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Assemble the static dashboard data (docs/data.js) from the six7 backtest output.

Reads:
  six7_stocks/lists/_manifest.json          - list counts + definitions + snapshot date
  six7_backtest_output/comparison_<h>.json  - per-horizon metrics (raw numbers)
  six7_backtest_output/<list>/dashboard_data.json - full-horizon curves + metrics

Writes docs/data.js as `window.SIX7_DATA = {...}` (a JS file, not JSON, so the
site works from file:// AND GitHub Pages with no server / no CORS).

Run: .venv/bin/python build_web.py   (after backtest_six7.py)
"""

import os
import json
from datetime import datetime, timezone

OUT = "six7_backtest_output"
DOCS = "docs"
HORIZONS = [("full", "Full · ~16y"), ("10y", "10 years"), ("5y", "5 years"),
            ("3y", "3 years"), ("1y", "1 year")]

# Display order + labels + one-line definitions. Two requested renames:
#   stocks_current        -> "Univest + six7 Hybrid"  (today's live watchlist)
#   stocks.txt (OLD 61)   -> "Univest Old"            (previous watchlist)
META = {
    "top10":      ("Top 10",   "Highest 10 by Fundamental Score"),
    "top30":      ("Top 30",   "Highest 30 by Fundamental Score"),
    "top50":      ("Top 50",   "Highest 50 by Fundamental Score"),
    "top100":     ("Top 100",  "Highest 100 by Fundamental Score"),
    "strong_buy": ("Strong Buy", "Composite ≥ 8.0 (site 'Strong')"),
    "buy_plus":   ("Buy+",     "Composite ≥ 6.5 (site 'Buy+')"),
    "six_plus":   ("6+ Criteria", "≥ 6 criteria met · Financials 5/5"),
    "perfect7":   ("Perfect 7", "All criteria · 7/7 or 5/5"),
    "stocks_current":      ("Univest + six7 Hybrid", "Current live watchlist (stocks.txt)"),
    "stocks.txt (OLD 61)": ("Univest Old", "Previous 61-stock watchlist"),
}
CURVE_LISTS = ["top10", "top30", "top50", "top100", "strong_buy",
               "buy_plus", "six_plus", "perfect7", "stocks_current"]

# dashboard_data.json strategy labels -> short web names
SERIES = {
    "Your Strategy (Timed HODL)": "Timed HODL",
    "SIP on Your Stocks": "SIP",
    "Partial SIP+Timed": "Partial",
    "Timed Entry+Exit": "Exit",
    "SIP on NIFTY 50": "NIFTY 50",
}
EQUITY_KEEP = ["Timed HODL", "SIP", "NIFTY 50"]
DD_KEEP = ["Timed HODL", "SIP"]


def downsample(series, n=400):
    dates, vals = series["dates"], series["values"]
    if len(dates) <= n:
        return {"d": dates, "v": [round(float(x), 1) for x in vals]}
    step = len(dates) / n
    idx = sorted({int(i * step) for i in range(n)} | {len(dates) - 1})
    return {"d": [dates[i] for i in idx], "v": [round(float(vals[i]), 1) for i in idx]}


def slim_metrics(m):
    return {k: (round(float(m[k]), 3) if isinstance(m.get(k), (int, float)) else m.get(k))
            for k in ("final_value", "total_return", "cagr", "xirr", "sharpe",
                      "sortino", "max_drawdown", "calmar", "volatility")}


def comparison_row(r):
    key = r["list"]
    label = META.get(key, (key, ""))[0]
    t, s, n = r.get("timed", {}), r.get("sip", {}), r.get("nifty") or {}
    return {
        "key": key, "label": label, "n": r.get("n_with_data"),
        "invested": round(float(r.get("total_invested", 0))),
        "timed": {"final": t.get("final_value"), "xirr": t.get("xirr"), "cagr": t.get("cagr"),
                  "sharpe": t.get("sharpe"), "sortino": t.get("sortino"), "maxdd": t.get("max_drawdown")},
        "sip": {"final": s.get("final_value"), "xirr": s.get("xirr"), "maxdd": s.get("max_drawdown")},
        "nifty": {"final": n.get("final_value"), "xirr": n.get("xirr")},
    }


def main():
    manifest = json.load(open(os.path.join("six7_stocks", "lists", "_manifest.json")))
    counts = {k: v["count"] for k, v in manifest["lists"].items()}

    comparison = {}
    for h, _ in HORIZONS:
        path = os.path.join(OUT, f"comparison_{h}.json")
        if os.path.isfile(path):
            blob = json.load(open(path))
            comparison[h] = [comparison_row(r) for r in blob["results"]]

    curves = {}
    for key in CURVE_LISTS:
        path = os.path.join(OUT, key, "dashboard_data.json")
        if not os.path.isfile(path):
            continue
        d = json.load(open(path))
        eq, dd, mets = {}, {}, {}
        for raw, short in SERIES.items():
            if raw in d["equity"]:
                if short in EQUITY_KEEP:
                    eq[short] = downsample(d["equity"][raw])
                if short in DD_KEEP and raw in d["drawdowns"]:
                    dd[short] = downsample(d["drawdowns"][raw])
        for m in d["metrics"]:
            short = SERIES.get(m["name"], m["name"])
            mets[short] = slim_metrics(m)
        curves[key] = {
            "invested": round(float(d["total_invested"])),
            "summary": d["summary"], "assumptions": d["assumptions"],
            "equity": eq, "drawdowns": dd, "metrics": mets,
        }

    period_full = comparison.get("full", [{}])
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "snapshot_date": (manifest.get("snapshot_generated_at") or "")[:10],
        "universe": manifest.get("universe_scanned"),
        "horizons": [{"key": k, "label": lbl,
                      "period": (json.load(open(os.path.join(OUT, f"comparison_{k}.json"))).get("period")
                                 if os.path.isfile(os.path.join(OUT, f"comparison_{k}.json")) else "")}
                     for k, lbl in HORIZONS],
        "list_order": CURVE_LISTS,
        "meta": {k: {"label": v[0], "blurb": v[1], "count": counts.get(k)} for k, v in META.items()},
        "comparison": comparison,
        "curves": curves,
        "caveat": ("Lists are a current (2026-06-01) fundamental screen run backward — "
                   "survivorship / look-ahead biased hindsight, not a tradeable signal."),
    }

    os.makedirs(DOCS, exist_ok=True)
    payload = "window.SIX7_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n"
    with open(os.path.join(DOCS, "data.js"), "w") as f:
        f.write(payload)
    size = os.path.getsize(os.path.join(DOCS, "data.js")) / 1024
    print(f"  wrote {DOCS}/data.js  ({size:.0f} KB)")
    print(f"  horizons: {list(comparison)} | curve lists: {list(curves)}")


if __name__ == "__main__":
    main()

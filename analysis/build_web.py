#!/usr/bin/env python3
"""Assemble the static dashboard data (docs/data.js) from the six7 backtest output.

Reads:
  analysis/six7_stocks/lists/_manifest.json - list counts + definitions + snapshot date
  backtest_output/six7/comparison_<h>.json  - per-horizon metrics (raw numbers)
  backtest_output/six7/<list>/dashboard_data.json - full-horizon curves + metrics

Writes docs/data.js as `window.SIX7_DATA = {...}` (a JS file, not JSON, so the
site works from file:// AND GitHub Pages with no server / no CORS).

Run: python3 analysis/build_web.py   (from the repo root, after backtest_six7.py)
"""

import os
import glob
import json
from datetime import datetime, timezone

import run_paths

OUT = run_paths.SIX7
DOCS = "docs"
HORIZONS = [("full", "Full · ~16y"), ("10y", "10 years"), ("5y", "5 years"),
            ("3y", "3 years"), ("1y", "1 year")]
# Monthly investment model per horizon (mirrors FLAT_MONTHLY in backtest_six7.py):
# salary-growth model for full/10y, flat ₹20,000/mo for the short windows.
CONTRIB = {"full": "₹5,500/mo → +10%/yr", "10y": "₹5,500/mo → +10%/yr",
           "5y": "₹20,000/mo", "3y": "₹20,000/mo", "1y": "₹20,000/mo"}

# Display order + labels + one-line definitions. Renames:
#   stocks_current        -> "Live watchlist"  (today's six7.txt ∪ holdings.txt)
#   stocks.txt (OLD 61)   -> "Univest Old"            (previous watchlist)
META = {
    "top10":      ("Top 10",   "Highest 10 by Fundamental Score"),
    "top30":      ("Top 30",   "Highest 30 by Fundamental Score"),
    "top50":      ("Top 50",   "Highest 50 by Fundamental Score"),
    "top100":     ("Top 100",  "six7 watchlist · mcap > ₹2,000cr · PEG < 2 (== six7.txt)"),
    "strong_buy": ("Strong Buy", "Composite ≥ 8.0 (site 'Strong')"),
    "buy_plus":   ("Buy+",     "Composite ≥ 6.5 (site 'Buy+')"),
    "six_plus":   ("6+ Criteria", "≥ 6 criteria met · Financials 5/5"),
    "perfect7":   ("Perfect 7", "All criteria · 7/7 or 5/5"),
    "univest_old":    ("Univest Old", "Univest base · before six7 additions"),
    "stocks_current": ("Live watchlist", "six7 Top 100 ∪ your holdings (stocks.txt)"),
    "nifty50":        ("NIFTY 50", "Index SIP benchmark"),
    "nifty_midcap":   ("NIFTY Midcap 50", "Index SIP benchmark"),
}
CURVE_LISTS = ["top10", "top30", "top50", "top100", "strong_buy",
               "buy_plus", "six_plus", "perfect7", "univest_old", "stocks_current"]

# dashboard_data.json strategy labels -> short web names
SERIES = {
    "Your Strategy (Timed HODL)": "Timed HODL",
    "SIP on Your Stocks": "SIP",
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
    inv = float(r.get("total_invested", 0)) or None
    is_bench = bool(r.get("benchmark"))
    # honest total return = final/invested-1 (NOT the misleading portfolio-series CAGR)
    ret = (t.get("final_value") / inv - 1) * 100 if (inv and t.get("final_value") is not None) else None
    # an index benchmark IS a monthly SIP into the index: its timed value == its SIP value
    sip_final = t.get("final_value") if is_bench else s.get("final_value")
    sip_xirr = t.get("xirr") if is_bench else s.get("xirr")
    return {
        "key": key, "label": label, "n": r.get("n_with_data"),
        "invested": round(inv) if inv else None, "benchmark": is_bench,
        "timed": {"final": t.get("final_value"), "ret": ret, "xirr": t.get("xirr"),
                  "cagr": t.get("cagr"), "vol": t.get("volatility"),
                  "sharpe": t.get("sharpe"), "sortino": t.get("sortino"), "maxdd": t.get("max_drawdown")},
        "sip": {"final": sip_final, "xirr": sip_xirr},
        "nifty": {"final": n.get("final_value"), "xirr": n.get("xirr")},
    }


def build_curve(curve):
    """Per-horizon windowed curve (from a comparison row) -> web {equity, drawdowns}.

    Same SERIES rename + downsample as the full-history list curves, so the dashboard
    can re-base the Screens inspect chart per horizon instead of slicing a full curve.
    """
    eq, dd = {}, {}
    for raw, short in SERIES.items():
        e = curve.get("equity", {}).get(raw)
        if e and short in EQUITY_KEEP:
            eq[short] = downsample(e, 200)
        d = curve.get("drawdowns", {}).get(raw)
        if d and short in DD_KEEP:
            dd[short] = downsample(d, 200)
    return {"equity": eq, "drawdowns": dd}


# Extended ratios from analysis/ratios_six7.py (ratios.json) -> short web keys.
# Daily ratios are on the unit NAV; pos_* are whole-position stats at the window's
# last close (survivorship-dominated past ~3y, so the page shows them on 1Y/3Y only).
RATIO_KEYS = {"calmar": "calmar", "profit_factor": "pf", "ulcer": "ulcer", "martin": "martin",
              "pos_profit_factor": "pos_pf", "win_rate": "win", "payoff": "payoff"}
CHANGE_KEYS = {"n": None, "xirr": "xirr", "sharpe": "sharpe", "sortino": "sortino", "calmar": "calmar",
               "profit_factor": "pf", "ulcer": "ulcer", "martin": "martin", "max_dd": "maxdd"}


def _r(v):
    return round(float(v), 3) if isinstance(v, (int, float)) else v


def load_ratios(path):
    return json.load(open(path)) if os.path.isfile(path) else None


def merge_ratios(comparison, ratios):
    """Fold ratios.json into the comparison rows (timed + sip) in place."""
    if not ratios:
        return
    for h, rows in comparison.items():
        rr = ratios["horizons"].get(h, {}).get("rows", {})
        for row in rows:
            src = rr.get(row["key"])
            if not src:
                continue
            for side in ("timed", "sip"):
                if side in src:
                    row[side].update({web: _r(src[side].get(k)) for k, web in RATIO_KEYS.items()
                                      if src[side].get(k) is not None})


def screen_change():
    """Old screen vs new screen, Timed HODL, per horizon -> {h: {list: {old, same, new}}}.

    old  = archived almanac (backtest_output/six7_<date>/ratios.json): old lists, old window
    same = new lists rerun on the old window (six7/samewindow_<end>/ratios.json)
    new  = new lists, new window (six7/ratios.json)
    """
    archives = sorted(d for d in glob.glob(os.path.join(run_paths.BASE, "six7_*"))
                      if os.path.isfile(os.path.join(d, "ratios.json")))
    samewin = sorted(glob.glob(os.path.join(OUT, "samewindow_*", "ratios.json")))
    new = load_ratios(os.path.join(OUT, "ratios.json"))
    if not (archives and samewin and new):
        return None
    runs = {"old": load_ratios(os.path.join(archives[-1], "ratios.json")),
            "same": load_ratios(samewin[-1]), "new": new}
    old_manifest = os.path.join(archives[-1], "lists", "_manifest.json")
    om = json.load(open(old_manifest)) if os.path.isfile(old_manifest) else {}
    out = {"old_snapshot": (om.get("snapshot_generated_at") or "")[:10],
           "old_end": runs["old"]["end"], "new_end": runs["new"]["end"], "horizons": {}}
    for h, _ in HORIZONS:
        lists = {}
        for key in CURVE_LISTS + ["nifty50"]:
            cell = {}
            for tag, R in runs.items():
                row = R["horizons"].get(h, {}).get("rows", {}).get(key)
                if row:
                    t = row["timed"]
                    cell[tag] = {"n": row.get("n"), **{web: _r(t.get(k)) for k, web in CHANGE_KEYS.items() if web}}
            if cell:
                lists[key] = cell
        out["horizons"][h] = lists
    return out


def main():
    manifest = json.load(open(os.path.join("analysis", "six7_stocks", "lists", "_manifest.json")))
    counts = {k: v["count"] for k, v in manifest["lists"].items()}
    # the two watchlists aren't in the six7 manifest - count their files directly
    for key, path in [("univest_old", os.path.join("analysis", "six7_stocks", "lists", "univest_old.txt")),
                      ("stocks_current", "stocks.txt")]:
        if os.path.isfile(path):
            counts[key] = sum(1 for ln in open(path) if ln.strip())

    comparison = {}
    for h, _ in HORIZONS:
        path = os.path.join(OUT, f"comparison_{h}.json")
        if os.path.isfile(path):
            blob = json.load(open(path))
            comparison[h] = [comparison_row(r) for r in blob["results"]]

    merge_ratios(comparison, load_ratios(os.path.join(OUT, "ratios.json")))

    curves = {}
    for key in CURVE_LISTS:
        path = os.path.join(OUT, key, "dashboard_data.json")
        if not os.path.isfile(path):
            continue
        d = json.load(open(path))
        eq, dd = {}, {}
        for raw, short in SERIES.items():
            if raw in d["equity"]:
                if short in EQUITY_KEEP:
                    eq[short] = downsample(d["equity"][raw])
                if short in DD_KEEP and raw in d["drawdowns"]:
                    dd[short] = downsample(d["drawdowns"][raw])
        # metric cards read from the (NAV-based) full-horizon comparison row, so
        # curves only need the chart series + summary, not a metrics block.
        curves[key] = {
            "invested": round(float(d["total_invested"])),
            "summary": d["summary"], "equity": eq, "drawdowns": dd,
        }

    # per-horizon windowed curves (lists + index benchmarks), keyed by horizon then
    # list key. The dashboard prefers these for a horizon, falling back to the
    # full-history `curves` for "All" / lists with no windowed curve.
    curves_h = {}
    for h, _ in HORIZONS:
        path = os.path.join(OUT, f"comparison_{h}.json")
        if not os.path.isfile(path):
            continue
        ch = {}
        for r in json.load(open(path))["results"]:
            c = r.get("curve")
            if c:
                ch[r["list"]] = build_curve(c)
        if ch:
            curves_h[h] = ch

    period_full = comparison.get("full", [{}])
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "snapshot_date": (manifest.get("snapshot_generated_at") or "")[:10],
        "universe": manifest.get("universe_scanned"),
        "horizons": [{"key": k, "label": lbl, "contrib": CONTRIB.get(k, ""),
                      "period": (json.load(open(os.path.join(OUT, f"comparison_{k}.json"))).get("period")
                                 if os.path.isfile(os.path.join(OUT, f"comparison_{k}.json")) else "")}
                     for k, lbl in HORIZONS],
        "list_order": CURVE_LISTS,
        "meta": {k: {"label": v[0], "blurb": v[1], "count": counts.get(k)} for k, v in META.items()},
        "comparison": comparison,
        "curves": curves,
        "curves_h": curves_h,
        "screen_change": screen_change(),
        "caveat": (f"Lists are a current ({(manifest.get('snapshot_generated_at') or '')[:10]}) fundamental "
                   "screen run backward - survivorship / look-ahead biased hindsight, not a tradeable signal."),
    }

    os.makedirs(DOCS, exist_ok=True)
    payload = "window.SIX7_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n"
    with open(os.path.join(DOCS, "data.js"), "w") as f:
        f.write(payload)
    size = os.path.getsize(os.path.join(DOCS, "data.js")) / 1024
    print(f"  wrote {DOCS}/data.js  ({size:.0f} KB)")
    print(f"  horizons: {list(comparison)} | curve lists: {list(curves)}")
    print(f"  per-horizon curves: {{ {', '.join(f'{h}:{len(c)}' for h, c in curves_h.items())} }}")


if __name__ == "__main__":
    main()

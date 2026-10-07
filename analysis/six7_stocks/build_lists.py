#!/usr/bin/env python3
"""Generate six7 stock lists from a saved six7 production snapshot.

Reproduces the exact filter/score logic of the deployed dashboard
(six7stocks.vercel.app) so the lists match what you see on the site:

  - `score` is re-derived client-side from `peg_eff` (criterion #7 = peg_eff in
    (0, 1.5]), then summed across the per-criterion `passed` flags. This mirrors
    `normaliseLegacyScore` in dashboard/index.template.html.
  - the criteria floor passes a stock when `score >= min` OR `score == denominator`
    (Financials are scored out of 5, so a 5/5 financial bypasses a 6+ floor).
    This mirrors the row filter at index.template.html:1183.
  - clicking a verdict segment ("Strong"/"Buy+") adds a composite floor on top of
    the default criteria floor of 6 (index.template.html:1184).
  - the Top-N lists carry the watchlist gates of six7's Top 100 view (2026-10-07):
    market cap > MIN_MARKET_CAP_CR and 0 < peg_eff < MAX_TOP_PEG, NOT backfilled,
    so top100 can hold fewer than 100 names (88 on 2026-10-07). This mirrors
    six7 `sync_hodl_stocks.top_tickers`, so top100 == the live six7.txt. The
    verdict/criteria lists (strong_buy, buy_plus, six_plus, perfect7) take no
    gates, exactly as the site's presets drop them outside the Top 100 view.

The D/E rule (criterion #5, 0 <= D/E <= 0.6 since 2026-10-07) and the composite
are NOT re-derived here: the snapshot's `criteria` flags and `composite` are
whatever six7 scored at scan time, so use a snapshot taken under the rules you
want to test.

Lists written to lists/ (one ticker per line, no .NS suffix, stocks.txt format):
  top10/top30/top50/top100  - ranked by 0-10 composite (ties: criteria, mkt cap)
  strong_buy                - "Strong" segment: composite >= 8.0  & criteria 6+
  buy_plus                  - "Buy+"  segment: composite >= 6.5  & criteria 6+
  six_plus                  - criteria 6+ (incl. Financials 5/5)
  perfect7                  - criteria == denominator (7/7 or 5/5)

Run: python3 analysis/six7_stocks/build_lists.py [snapshot.json]
     (default: the newest snapshot_*.json next to this script)
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LISTS_DIR = os.path.join(HERE, "lists")

DEFAULT_MIN = 6          # site default criteria floor (scan mode)
STRONG_BUY_FUND = 8.0    # "Strong" verdict segment composite floor
BUY_PLUS_FUND = 6.5      # "Buy+"  verdict segment composite floor
# Top-N watchlist gates. Must equal six7 sync_hodl_stocks.MIN_MARKET_CAP_CR /
# MAX_TOP_PEG (and MIN_MARKET_CAP_CR / MAX_TOP_PEG in its dashboard template).
MIN_MARKET_CAP_CR = 2000 # strictly greater than; missing cap fails
MAX_TOP_PEG = 2.0        # 0 < peg_eff < 2.0; missing peg_eff fails


def latest_snapshot():
    snaps = sorted(glob.glob(os.path.join(HERE, "snapshot_*.json")))
    if not snaps:
        sys.exit(f"no snapshot_*.json in {HERE}")
    return snaps[-1]


def denominator(item):
    """Criteria denominator: Financials are exempt from D/E + FCF, so 5 not 7."""
    return item.get("denominator") or (5 if item.get("sector") == "Financials" else 7)


def normalise_score(item):
    """Re-derive criterion #7 (peg) and the integer criteria total, as the site does."""
    crit = item.get("criteria")
    if not crit or "peg" not in crit:
        return
    peg_eff = item.get("peg_eff")
    crit["peg"]["passed"] = peg_eff is not None and peg_eff > 0 and peg_eff <= 1.5
    item["score"] = sum(1 for c in crit.values() if c.get("passed"))


def passes_criteria(item, floor):
    """Site row filter: score >= floor OR perfect (score == denominator)."""
    s = item.get("score") or 0
    return s >= floor or s == denominator(item)


def watchlist_gates(item):
    """six7 Top-N gates: market cap > MIN_MARKET_CAP_CR and 0 < peg_eff < MAX_TOP_PEG."""
    peg_eff = item.get("peg_eff")
    return ((item.get("market_cap") or 0) > MIN_MARKET_CAP_CR
            and peg_eff is not None and 0 < peg_eff < MAX_TOP_PEG)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    snapshot = argv[0] if argv else latest_snapshot()
    with open(snapshot) as f:
        snap = json.load(f)
    items = snap["items"]
    for it in items:
        normalise_score(it)

    scored = [it for it in items if it.get("composite") is not None]
    # Top-N are drawn from the default 6+ universe (what you see when you sort by
    # Fundamental Score on the landing view) behind the watchlist gates, ranked
    # by composite then criteria then market cap. Not backfilled.
    universe6 = [it for it in scored if passes_criteria(it, DEFAULT_MIN)]
    gated = [it for it in universe6 if watchlist_gates(it)]
    ranked = sorted(
        gated,
        key=lambda x: (x.get("composite") or 0, x.get("score") or 0, x.get("market_cap") or 0),
        reverse=True,
    )

    lists = {
        "top10": ranked[:10],
        "top30": ranked[:30],
        "top50": ranked[:50],
        "top100": ranked[:100],
        "strong_buy": [it for it in items if (it.get("composite") or 0) >= STRONG_BUY_FUND and passes_criteria(it, DEFAULT_MIN)],
        "buy_plus":   [it for it in items if (it.get("composite") or 0) >= BUY_PLUS_FUND and passes_criteria(it, DEFAULT_MIN)],
        "six_plus":   [it for it in items if passes_criteria(it, DEFAULT_MIN)],
        "perfect7":   [it for it in items if (it.get("score") or 0) == denominator(it)],
    }

    os.makedirs(LISTS_DIR, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot": os.path.basename(snapshot),
        "snapshot_generated_at": snap.get("meta", {}).get("generatedAt"),
        "universe_scanned": len(items),
        "definitions": {
            "top10/30/50/100": (f"ranked by 0-10 composite within the 6+ criteria universe, gated on market cap > "
                                f"{MIN_MARKET_CAP_CR}cr and 0 < peg_eff < {MAX_TOP_PEG} (not backfilled); "
                                "ties -> criteria count -> market cap"),
            "strong_buy": f"composite >= {STRONG_BUY_FUND} AND (score >= {DEFAULT_MIN} OR perfect) -- site 'Strong' segment",
            "buy_plus": f"composite >= {BUY_PLUS_FUND} AND (score >= {DEFAULT_MIN} OR perfect) -- site 'Buy+' segment",
            "six_plus": f"score >= {DEFAULT_MIN} OR perfect (Financials 5/5 included)",
            "perfect7": "score == denominator (7/7, or 5/5 for Financials)",
        },
        "lists": {},
    }

    for name, rows in lists.items():
        # ranked lists keep their composite order; the rest sorted by composite desc
        if not name.startswith("top"):
            rows = sorted(rows, key=lambda x: (x.get("composite") or 0, x.get("score") or 0), reverse=True)
        tickers = [it["ticker"] for it in rows]
        path = os.path.join(LISTS_DIR, f"{name}.txt")
        with open(path, "w") as f:
            f.write("\n".join(tickers) + ("\n" if tickers else ""))
        manifest["lists"][name] = {"count": len(tickers)}
        print(f"  {name:12s}: {len(tickers):4d}  -> {os.path.relpath(path, HERE)}")

    with open(os.path.join(LISTS_DIR, "_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Manifest: {os.path.relpath(os.path.join(LISTS_DIR, '_manifest.json'), HERE)}")
    print(f"  Universe: {len(items)} scanned, {len(scored)} with composite, {len(universe6)} at 6+, "
          f"{len(gated)} through the Top-N gates")


if __name__ == "__main__":
    main()

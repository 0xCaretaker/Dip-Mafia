#!/usr/bin/env python3
"""Shared layout for backtest artifacts under a single parent folder.

All runs live in dated, self-describing subfolders of ``backtest_output/``:

    backtest_output/
      20260417_75sym_bb60/   <- a run (dashboard_data.json, *.png, meta.json, ...)
      20260417_62sym_bb30/   <- an earlier run
      six7/                  <- six7 almanac outputs (*.pkl caches git-ignored)
      dashboard.html

The "current" run is simply the newest one: highest ``meta.json`` date, ties
broken by folder name (descending). six7/ has no top-level dashboard_data.json,
so it is never mistaken for a run.

Every consumer (backtest.py, portfolio_view.py, horizon_compare.py,
backtest_six7.py) imports this module so the layout is defined in exactly one
place.
"""

import os
import glob
import json

BASE = "backtest_output"
SIX7 = os.path.join(BASE, "six7")


def run_name(end_date, n_stocks, bb_lookback):
    """Folder name for a run, e.g. ``20260417_75sym_bb60``.

    ``end_date`` may be a ``date``/``datetime``/``Timestamp``/ISO string; only
    its leading ``YYYY-MM-DD`` is used.
    """
    ymd = str(end_date)[:10].replace("-", "")
    return f"{ymd}_{n_stocks}sym_bb{bb_lookback}"


def _meta(d):
    mp = os.path.join(d, "meta.json")
    if os.path.isfile(mp):
        try:
            return json.load(open(mp))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def list_runs():
    """All run subfolders, newest first.

    A run is any direct subdirectory of ``BASE`` containing a top-level
    ``dashboard_data.json``. Returned as ``[(dir, meta_dict), ...]`` sorted by
    ``(meta.date, basename)`` descending.
    """
    runs = []
    for d in glob.glob(os.path.join(BASE, "*")):
        if not os.path.isdir(d):
            continue
        if not os.path.isfile(os.path.join(d, "dashboard_data.json")):
            continue
        runs.append((d, _meta(d)))
    runs.sort(key=lambda x: (str(x[1].get("date", "")), os.path.basename(x[0])),
              reverse=True)
    return runs


def current_run():
    """Newest run directory, or ``None`` if there are no runs yet."""
    runs = list_runs()
    return runs[0][0] if runs else None


def archived_runs():
    """Every run directory except the current (newest) one, newest first."""
    return [d for d, _ in list_runs()[1:]]

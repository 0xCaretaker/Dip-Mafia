"""Unit tests for the two-list watchlist loader.

Dependency-free (plain asserts). Run with:
    python tests/test_watchlist.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from watchlist import load_watchlist, _normalize


def _write(path, lines):
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def test_normalize_strips_series_suffix():
    assert _normalize("indotech-be") == "INDOTECH"   # uppercase + strip -BE
    assert _normalize("ARROWGREEN-BE") == "ARROWGREEN"
    assert _normalize("BAJAJ-AUTO") == "BAJAJ-AUTO"   # 4-letter tail kept
    assert _normalize("BSE") == "BSE"


def test_union_dedup_sorted_and_classified():
    with tempfile.TemporaryDirectory() as d:
        six7 = os.path.join(d, "six7.txt")
        holdings = os.path.join(d, "holdings.txt")
        _write(six7, ["BSE", "COFORGE", "# a comment", "", "ANANTRAJ"])
        _write(holdings, ["bse", "INDOTECH-BE", "SUZLON"])

        symbols, six7_set, holdings_set = load_watchlist(six7, holdings)

        # sorted, de-duplicated union (BSE appears once despite both lists)
        assert symbols == ["ANANTRAJ", "BSE", "COFORGE", "INDOTECH", "SUZLON"]
        # membership reflects normalized names
        assert six7_set == {"BSE", "COFORGE", "ANANTRAJ"}
        assert holdings_set == {"BSE", "INDOTECH", "SUZLON"}
        # overlap is in both sets; the caller decides six7 wins
        assert "BSE" in six7_set and "BSE" in holdings_set
        # holdings-only (non-six7) names
        assert {s for s in symbols if s not in six7_set} == {"INDOTECH", "SUZLON"}


def test_missing_files_are_tolerated():
    with tempfile.TemporaryDirectory() as d:
        only = os.path.join(d, "six7.txt")
        _write(only, ["BSE", "BSE"])  # duplicate within a file collapses too
        symbols, six7_set, holdings_set = load_watchlist(
            only, os.path.join(d, "does_not_exist.txt")
        )
        assert symbols == ["BSE"]
        assert six7_set == {"BSE"}
        assert holdings_set == set()


if __name__ == "__main__":
    test_normalize_strips_series_suffix()
    test_union_dedup_sorted_and_classified()
    test_missing_files_are_tolerated()
    print("✓ all watchlist tests passed")

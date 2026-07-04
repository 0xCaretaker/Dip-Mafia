"""Unit tests for the Bollinger band-position zone logic.

Dependency-free (plain asserts). Run with:
    python tests/test_bb_position.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from bollinger_signals import _position_from_levels, calculate_bb_mid_distance_pct


def test_zones():
    # close, lower, middle, upper
    assert _position_from_levels(90, 100, 110, 120) == "⏬"   # below lower band
    assert _position_from_levels(105, 100, 110, 120) == "🔽"  # lower..mid
    assert _position_from_levels(115, 100, 110, 120) == "🔼"  # mid..upper
    assert _position_from_levels(125, 100, 110, 120) == "⏫"   # above upper band


def test_boundaries():
    # Boundaries use < for the upper edge of each zone:
    assert _position_from_levels(100, 100, 110, 120) == "🔽"  # exactly lower -> not below
    assert _position_from_levels(110, 100, 110, 120) == "🔼"  # exactly mid
    assert _position_from_levels(120, 100, 110, 120) == "⏫"   # exactly upper -> extended


def test_fallback():
    nan = float("nan")
    assert _position_from_levels(None, 100, 110, 120) is None
    assert _position_from_levels(105, nan, 110, 120) is None
    assert _position_from_levels(105, 100, nan, 120) is None
    assert _position_from_levels(105, 100, 110, nan) is None


def _close_df(closes):
    return pd.DataFrame({"Close": closes})


def test_mid_distance():
    # constant series: last close == 200-SMA midline -> ~0%
    d = calculate_bb_mid_distance_pct(_close_df([100.0] * 250), length=200)
    assert d is not None and abs(d) < 1e-9

    # last close below the trailing average -> negative
    assert calculate_bb_mid_distance_pct(_close_df([100.0] * 249 + [50.0]), length=200) < 0

    # last close above the trailing average -> positive
    assert calculate_bb_mid_distance_pct(_close_df([100.0] * 249 + [150.0]), length=200) > 0

    # insufficient history (< length bars) -> None
    assert calculate_bb_mid_distance_pct(_close_df([100.0] * 150), length=200) is None


if __name__ == "__main__":
    test_zones()
    test_boundaries()
    test_fallback()
    test_mid_distance()
    print("✓ all bb position tests passed")

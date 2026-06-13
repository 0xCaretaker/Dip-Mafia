"""Unit tests for the Bollinger band-position zone logic.

Dependency-free (plain asserts). Run with:
    python tests/test_bb_position.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bollinger_signals import _position_from_levels


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


if __name__ == "__main__":
    test_zones()
    test_boundaries()
    test_fallback()
    print("✓ all bb position tests passed")

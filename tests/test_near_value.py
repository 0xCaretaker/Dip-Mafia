"""Unit tests for the Cheap Bargains notification section (a.k.a. near-value).

Plain asserts; imports bot (needs yfinance installed). Run with:
    python tests/test_near_value.py
"""
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import build_message

TS = datetime(2026, 7, 4, tzinfo=ZoneInfo("Asia/Kolkata"))


def _msg():
    six7 = {"ECLERX", "FOO", "ABOVE"}
    bollinger = {
        # Top-50, deep below mid, fresh iMACD Buy -> gets the zap
        "ECLERX.NS": {"action": "Hold", "time": TS, "price": 1488.8,
                      "position": "🔽", "mid_dist_pct": -21.0},
        # Top-50, below mid, no fresh cross -> kept, no zap
        "FOO.NS": {"action": "Hold", "time": TS, "price": 100.0,
                   "position": "🔽", "mid_dist_pct": -3.1},
        # Top-50 but ABOVE the midline -> excluded (below-mid only, no cushion)
        "ABOVE.NS": {"action": "Hold", "time": TS, "price": 10.0,
                     "position": "🔼", "mid_dist_pct": 2.4},
        # below mid but NOT Top-50 -> excluded
        "BAR.NS": {"action": "Hold", "time": TS, "price": 10.0,
                   "position": "🔽", "mid_dist_pct": -3.0},
    }
    all_signals = {
        "1d": {},
        "1d Impulse MACD": {
            "ECLERX.NS": {"action": "Buy", "time": TS, "price": 1488.8},
        },
    }
    return build_message(all_signals, bollinger, None, six7)


def test_near_value_section():
    msg = _msg()
    assert msg is not None
    lines = msg.splitlines()

    assert "📉 *Cheap Bargains*" in msg
    assert "below 200" in msg           # title reflects below-midline only
    assert "cash in hand" in msg        # actionable prompt under the heading

    # ECLERX line: identified by its unique % string, carries position + zap
    ecl = [l for l in lines if "-21.0%" in l][0]
    assert "ECLERX" in ecl and "🔽" in ecl and ecl.rstrip().endswith("⚡")

    # FOO line: below mid, no fresh cross -> no zap
    foo = [l for l in lines if "-3.1%" in l][0]
    assert "FOO" in foo and "⚡" not in foo

    # cheapest-first ordering
    assert msg.index("-21.0%") < msg.index("-3.1%")

    # exclusions: above the midline (no +5% cushion), and non-Top-50
    assert "ABOVE" not in msg
    assert "BAR" not in msg


def test_no_unescaped_markdownv2_specials():
    """A single unescaped MarkdownV2 special outside a code span makes Telegram
    400-reject the whole message. Guard the chars that are never used as
    formatting markers here (notably '>' in the idle-cash footnote)."""
    msg = _msg()
    # These are never intentional markers in this bot (unlike * _ ` used for
    # bold/italic/code), so any unescaped occurrence outside a code span is a bug.
    never_marker = r">#+=|{}!"
    for line in msg.splitlines():
        nocode = re.sub(r"`[^`]*`", "", line)      # drop `...` code spans
        for ch in never_marker:
            for m in re.finditer(re.escape(ch), nocode):
                prev = nocode[m.start() - 1] if m.start() > 0 else ""
                assert prev == "\\", f"unescaped {ch!r} in: {line!r}"


if __name__ == "__main__":
    test_near_value_section()
    test_no_unescaped_markdownv2_specials()
    print("✓ near value section tests passed")

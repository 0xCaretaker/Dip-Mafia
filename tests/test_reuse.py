"""Unit tests for the scan-scoped reuse path in bot.py.

Plain-assert script (repo convention). Run with:
    python3 tests/test_reuse.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bot


def test_build_message_renders_without_io():
    # A single Hold signal makes a MACD section render (build_message returns
    # None only when nothing renders). build_message must do no network I/O.
    signals = {"1d": {"TCS.NS": {"action": "Hold", "time": "x", "price": 100.0}}}
    msg = bot.build_message(signals, {}, None, {"TCS"})
    assert isinstance(msg, str) and "DIP MAFIA" in msg


if __name__ == "__main__":
    test_build_message_renders_without_io()
    print("✓ build_message test passed")

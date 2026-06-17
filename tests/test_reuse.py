"""Unit tests for the scan-scoped reuse path in bot.py.

Plain-assert script (repo convention). Run with:
    python3 tests/test_reuse.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bot


def test_build_message_renders_without_io():
    # A single Hold signal makes a MACD section render (build_message returns
    # None only when nothing renders). build_message must do no network I/O.
    signals = {"1d": {"TCS.NS": {"action": "Hold", "time": "x", "price": 100.0}}}
    msg = bot.build_message(signals, {}, None, {"TCS"})
    assert isinstance(msg, str) and "DIP MAFIA" in msg


def test_watchlist_signature_distinguishes_membership():
    a = bot.watchlist_signature(["TCS", "INFY"], {"TCS"})
    b = bot.watchlist_signature(["INFY", "TCS"], {"TCS"})   # order-independent
    c = bot.watchlist_signature(["TCS", "INFY"], {"INFY"})  # membership moved
    assert a == b
    assert a != c


def test_cache_round_trip_and_missing():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "sub", "last_post.json")
        assert bot.read_cache(p) is None           # missing -> None
        bot.write_cache(p, "2026-06-17", "sig123", "msg-body")
        got = bot.read_cache(p)
        assert got["data_date"] == "2026-06-17"
        assert got["watchlist_signature"] == "sig123"
        assert got["message_md"] == "msg-body"


def test_read_cache_malformed_returns_none():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "bad.json")
        with open(p, "w") as f:
            f.write("{not json")
        assert bot.read_cache(p) is None


import pandas as pd


class _FakeYF:
    def __init__(self, frame=None, raise_exc=False):
        self._frame = frame
        self._raise = raise_exc

    def download(self, *a, **k):
        if self._raise:
            raise RuntimeError("network down")
        return self._frame


def test_latest_trading_date_parses_last_bar():
    frame = pd.DataFrame(
        {"Close": [1.0, 2.0]},
        index=pd.to_datetime(["2026-06-16", "2026-06-17"]),
    )
    saved = bot.yf
    try:
        bot.yf = _FakeYF(frame=frame)
        assert bot.latest_trading_date() == "2026-06-17"
    finally:
        bot.yf = saved


def test_latest_trading_date_none_on_empty_and_error():
    saved = bot.yf
    try:
        bot.yf = _FakeYF(frame=pd.DataFrame())           # empty
        assert bot.latest_trading_date() is None
        bot.yf = _FakeYF(raise_exc=True)                 # exception
        assert bot.latest_trading_date() is None
    finally:
        bot.yf = saved


if __name__ == "__main__":
    test_build_message_renders_without_io()
    test_watchlist_signature_distinguishes_membership()
    test_cache_round_trip_and_missing()
    test_read_cache_malformed_returns_none()
    test_latest_trading_date_parses_last_bar()
    test_latest_trading_date_none_on_empty_and_error()
    print("✓ build_message + signature + cache + probe tests passed")

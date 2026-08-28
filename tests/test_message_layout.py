"""Message layout: section order, and naming the Wait-for-Buy stocks.

Two things this locks down:

  1. **Cheap Bargains comes before the Verdict.** Most days the Verdict has no
     buys, so leading with it buried the section that always has something to
     act on.
  2. **Wait for Buy names its stocks.** A bare "3/3" told you how many were
     waiting but never which — so the one list you might want to watch was the
     one you couldn't see.

Plain asserts; imports bot (needs yfinance installed). Run with:
    python tests/test_message_layout.py
"""
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import build_message

TS = datetime(2026, 8, 20, tzinfo=ZoneInfo("Asia/Kolkata"))
SIX7 = {"AAA", "BBB", "CCC"}


def _bollinger(**overrides):
    """Three Top-50 names, all through the Bollinger gate and below the mid."""
    base = {
        "AAA.NS": {"action": "Buy", "time": TS, "price": 100.0,
                   "position": "⏬", "mid_dist_pct": -10.0},
        "BBB.NS": {"action": "Watch", "time": TS, "price": 200.0,
                   "position": "🔽", "mid_dist_pct": -5.0},
        "CCC.NS": {"action": "Watch", "time": TS, "price": 300.0,
                   "position": "🔽", "mid_dist_pct": -2.0},
    }
    base.update(overrides)
    return base


def _impulse():
    return {
        "AAA.NS": {"action": "Buy", "time": TS, "price": 100.0},
        "BBB.NS": {"action": "Wait for Buy", "time": TS, "price": 200.0},
        "CCC.NS": {"action": "Wait for Buy", "time": TS, "price": 300.0},
    }


def _msg(bollinger=None, impulse=None, six7=SIX7):
    return build_message(
        {"1d": {}, "1d Impulse MACD": _impulse() if impulse is None else impulse},
        _bollinger() if bollinger is None else bollinger,
        None,
        six7,
    )


def test_cheap_bargains_renders_before_the_verdict():
    msg = _msg()
    assert "📉 *Cheap Bargains*" in msg and "🎯 *Verdict*" in msg
    assert msg.index("📉 *Cheap Bargains*") < msg.index("🎯 *Verdict*")


def test_how_to_act_footer_follows_the_same_order():
    msg = _msg()
    assert msg.index("spare cash") < msg.index("buy the")


def test_wait_for_buy_lists_every_name():
    msg = _msg()
    assert "2/3" in msg                       # the count survives
    wait_block = msg.split("Wait for Buy")[1]
    assert "BBB" in wait_block and "CCC" in wait_block
    # AAA is a Buy — it belongs in the buy rows, not in the waiting list.
    assert "AAA" not in wait_block.split("Hold")[0]


def test_wait_names_carry_their_class_tag():
    """Same ⭐ / 💼 vocabulary as the buy rows, so the list reads consistently."""
    msg = _msg(six7={"BBB"})               # CCC is then a holding, not six7
    wait_block = msg.split("Wait for Buy")[1].split("Hold")[0]
    assert "⭐" in wait_block and "💼" in wait_block


def test_no_names_listed_when_nothing_is_waiting():
    """The 0/N stats line stays (it's a real reading); it just names nobody."""
    impulse = {"AAA.NS": {"action": "Buy", "time": TS, "price": 100.0}}
    msg = _msg(impulse=impulse)
    assert "0/1" in msg
    wait_block = msg.split("Wait for Buy")[1].split("Hold")[0]
    assert "⭐" not in wait_block and "💼" not in wait_block


def test_empty_bargains_still_reported_when_the_verdict_has_content():
    """Reordering must not silently drop the 'none near the midline' note."""
    above = _bollinger()
    for info in above.values():
        info["mid_dist_pct"] = 5.0         # nothing below the midline
    msg = _msg(bollinger=above)
    assert "none near the midline" in msg
    assert msg.index("Cheap Bargains") < msg.index("Verdict")


def test_nothing_at_all_sends_nothing():
    """The guard that stops a message that would only say 'none near the mid'."""
    empty = {"ZZZ.NS": {"action": "Hold", "time": TS, "price": 1.0,
                        "position": "🔼", "mid_dist_pct": 3.0}}
    assert _msg(bollinger=empty, impulse={}, six7=set()) is None


def test_no_buys_line_is_separated_from_the_wait_stats():
    """'no buys today' used to sit flush against the Wait-for-Buy stats, so the
    verdict and the roster below it read as one undifferentiated block."""
    impulse = {
        "AAA.NS": {"action": "Wait for Buy", "time": TS, "price": 100.0},
        "BBB.NS": {"action": "Wait for Buy", "time": TS, "price": 200.0},
    }
    lines = _msg(impulse=impulse).splitlines()
    i = next(n for n, ln in enumerate(lines) if "no buys today" in ln)
    assert lines[i + 1] == "", "expected a blank line under 'no buys today'"
    assert "Wait for Buy" in lines[i + 2]


def test_no_unescaped_markdownv2_specials():
    msg = _msg()
    never_marker = r">#+=|{}!"
    for line in msg.splitlines():
        nocode = re.sub(r"`[^`]*`", "", line)
        for ch in never_marker:
            for m in re.finditer(re.escape(ch), nocode):
                prev = nocode[m.start() - 1] if m.start() > 0 else ""
                assert prev == "\\", f"unescaped {ch!r} in: {line!r}"


if __name__ == "__main__":
    test_cheap_bargains_renders_before_the_verdict()
    test_how_to_act_footer_follows_the_same_order()
    test_wait_for_buy_lists_every_name()
    test_wait_names_carry_their_class_tag()
    test_no_names_listed_when_nothing_is_waiting()
    test_no_buys_line_is_separated_from_the_wait_stats()
    test_empty_bargains_still_reported_when_the_verdict_has_content()
    test_nothing_at_all_sends_nothing()
    test_no_unescaped_markdownv2_specials()
    print("✓ message layout tests passed")

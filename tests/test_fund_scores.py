"""Fund. Score on the 💼 rows of the Verdict.

A ⭐ row is a six7 Top 50 name — its fundamentals are why it is on the list at
all. A 💼 row is a stock you already hold, kept in the watchlist after the Top
50 rotated past it, and it arrived with no fundamental context whatsoever. So
six7 mirrors `six7_scores.json` ({SYMBOL: 0-10 Fund. Score}) into this repo and
the Verdict annotates its 💼 rows with it — buy/sell lines and the Wait-for-Buy
roster alike.

The bot must never depend on that file: a stale mirror, a broken sync, or a
holding six7 has not scored yet all degrade to a clean, unannotated row.

Plain asserts; imports bot (needs yfinance installed). Run with:
    python tests/test_fund_scores.py
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot
from bot import build_message, load_fund_scores

TS = datetime(2026, 8, 21, tzinfo=ZoneInfo("Asia/Kolkata"))

# AAA is a Top 50 name (⭐); BBB and CCC are holdings (💼).
SIX7 = {"AAA"}
SCORES = {"BBB": 7.2, "CCC": 4.5}


def _bollinger():
    return {
        "AAA.NS": {"action": "Buy", "time": TS, "price": 100.0,
                   "position": "⏬", "mid_dist_pct": -10.0},
        "BBB.NS": {"action": "Buy", "time": TS, "price": 200.0,
                   "position": "🔽", "mid_dist_pct": -5.0},
        "CCC.NS": {"action": "Watch", "time": TS, "price": 300.0,
                   "position": "🔽", "mid_dist_pct": -2.0},
    }


def _impulse():
    return {
        "AAA.NS": {"action": "Buy", "time": TS, "price": 100.0},
        "BBB.NS": {"action": "Buy", "time": TS, "price": 200.0},
        "CCC.NS": {"action": "Wait for Buy", "time": TS, "price": 300.0},
    }


def _msg(scores=SCORES, six7=SIX7, impulse=None, bollinger=None):
    return build_message(
        {"1d": {}, "1d Impulse MACD": _impulse() if impulse is None else impulse},
        _bollinger() if bollinger is None else bollinger,
        None,
        six7,
        scores,
    )


def _verdict(msg):
    return msg.split("🎯 *Verdict*")[1]


def _buy_rows(msg):
    return _verdict(msg).split("Wait for Buy")[0]


def _wait_rows(msg):
    return _verdict(msg).split("Wait for Buy")[1].split("Hold")[0]


def test_holding_buy_row_carries_its_fund_score():
    rows = _buy_rows(_msg())
    line = [ln for ln in rows.splitlines() if "BBB" in ln][0]
    assert "💼" in line and "7.2" in line


def test_top50_buy_row_carries_no_score():
    """Only 💼 rows are annotated — a ⭐ name's fundamentals are why it is listed."""
    rows = _buy_rows(_msg(scores={"AAA": 9.9, **SCORES}))
    line = [ln for ln in rows.splitlines() if "AAA" in ln][0]
    assert "⭐" in line and "9.9" not in line


def test_holding_wait_row_carries_its_fund_score():
    line = [ln for ln in _wait_rows(_msg()).splitlines() if "CCC" in ln][0]
    assert "💼" in line and "4.5" in line


def test_unscored_holding_renders_clean():
    """A stock bought since the last six7 scan has no score yet. Render the row
    without one rather than printing 'n/a' — absence of data is not a reading."""
    rows = _buy_rows(_msg(scores={}))
    line = [ln for ln in rows.splitlines() if "BBB" in ln][0]
    assert "💼" in line and "₹200.00" in line
    assert "n/a" not in line.lower()


def test_no_scores_at_all_leaves_the_message_intact():
    """A missing/broken mirror must not change how the bot behaves today."""
    assert _msg(scores={}) == _msg(scores=None)


def test_columns_stay_aligned_across_scored_and_unscored_rows():
    """Monospace columns are the whole point of the code spans — a 💼 row with a
    score and a ⭐ row without must still line up at the price column."""
    rows = [ln for ln in _buy_rows(_msg()).splitlines() if "₹" in ln]
    assert len(rows) == 2
    assert len({ln.index("₹") for ln in rows}) == 1


def test_legend_explains_the_number():
    """A bare 7.2 next to a ticker is unreadable without being told what it is."""
    msg = _msg()
    assert "Fund" in msg and "0" in msg
    assert "score" in msg.lower()


def test_legend_is_absent_when_nothing_is_scored():
    assert "Fund" not in _msg(scores={})


def test_load_fund_scores_reads_the_mirror(tmp_path):
    p = tmp_path / "six7_scores.json"
    p.write_text(json.dumps({"BBB": 7.2}))
    assert load_fund_scores(str(p)) == {"BBB": 7.2}


def test_load_fund_scores_tolerates_a_missing_file(tmp_path):
    assert load_fund_scores(str(tmp_path / "nope.json")) == {}


def test_load_fund_scores_tolerates_corrupt_json(tmp_path):
    """A half-written mirror must not take the signal bot down."""
    p = tmp_path / "six7_scores.json"
    p.write_text("{not json")
    assert load_fund_scores(str(p)) == {}


def test_load_fund_scores_ignores_non_numeric_values(tmp_path):
    p = tmp_path / "six7_scores.json"
    p.write_text(json.dumps({"BBB": 7.2, "CCC": None, "DDD": "n/a"}))
    assert load_fund_scores(str(p)) == {"BBB": 7.2}


def test_score_never_breaks_markdownv2_escaping():
    """The '.' in 7.2 is a MarkdownV2 special — it is only safe inside a code
    span, so this guards against it ever leaking into plain text."""
    import re

    for line in _msg().splitlines():
        nocode = re.sub(r"`[^`]*`", "", line)
        for m in re.finditer(re.escape("."), nocode):
            prev = nocode[m.start() - 1] if m.start() > 0 else ""
            assert prev == "\\", f"unescaped '.' in: {line!r}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            if fn.__code__.co_argcount:
                continue  # tmp_path fixtures need pytest
            fn()
    print("✓ fund score tests passed (run pytest for the tmp_path cases)")

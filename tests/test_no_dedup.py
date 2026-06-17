"""Guards that bot.py posts every run (no signal-dedup gate).

Dependency-free (plain asserts). Run with:
    python3 tests/test_no_dedup.py
"""
import os
import py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT = os.path.join(ROOT, "bot.py")


def _src():
    with open(BOT, encoding="utf-8") as f:
        return f.read()


def test_no_dedup_machinery():
    src = _src()
    removed = (
        "hashlib",
        ".last_signal_hash",
        "DIP_MAFIA_FORCE",
        "current_hash",
        "prev_hash",
        "Skipping Telegram",
    )
    for token in removed:
        assert token not in src, f"bot.py still references removed dedup token: {token!r}"


def test_bot_still_compiles():
    py_compile.compile(BOT, doraise=True)


if __name__ == "__main__":
    test_no_dedup_machinery()
    test_bot_still_compiles()
    print("✓ all no-dedup tests passed")

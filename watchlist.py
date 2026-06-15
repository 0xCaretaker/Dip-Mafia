"""Watchlist loader: the two source lists that feed the live bot.

The bot signals on the union of two hand/mirror-maintained files:

  six7.txt      the six7 NSE Top 50 (overwritten by the external six7 mirror)
  holdings.txt  the user's real Zerodha book (synced from Portfolio-Analyzer)

Splitting them keeps signals flowing for stocks you already hold even after the
mirror rewrites the Top 50. `stocks.txt` is a *derived* file (the sorted union)
regenerated from here so the analysis/backtest tooling keeps reading one list.

Symbols are stored without the `.NS` suffix (bot.py appends it). NSE series
suffixes like `-BE`/`-BZ`/`-SM` are stripped so the ticker resolves on yfinance
(e.g. `INDOTECH-BE` -> `INDOTECH`); the two-letter constraint leaves legitimate
hyphenated tickers such as `BAJAJ-AUTO` untouched.

Run `python3 watchlist.py` to (re)write the derived stocks.txt after either
source list changes.
"""
import re

SIX7_FILE = "six7.txt"
HOLDINGS_FILE = "holdings.txt"
DERIVED_FILE = "stocks.txt"

# NSE trade-segment series code, e.g. -BE (trade-to-trade), -BZ, -SM, -ST.
_SERIES_SUFFIX = re.compile(r"-[A-Z]{2}$")


def _read(path):
    """One symbol per line; blanks and `#` comments skipped. Missing file -> []."""
    try:
        with open(path, "r") as f:
            lines = [ln.strip() for ln in f]
    except FileNotFoundError:
        return []
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _normalize(symbol):
    """Uppercase and drop a trailing NSE series suffix for yfinance."""
    return _SERIES_SUFFIX.sub("", symbol.upper())


def load_watchlist(six7_path=SIX7_FILE, holdings_path=HOLDINGS_FILE):
    """Return (symbols, six7_set, holdings_set), all normalized and .NS-free.

    `symbols` is the sorted, de-duplicated union. A symbol in both lists is in
    both sets; callers treat six7 membership as winning (it's the Top 50 tag).
    """
    six7 = {_normalize(s) for s in _read(six7_path)}
    holdings = {_normalize(s) for s in _read(holdings_path)}
    symbols = sorted(six7 | holdings)
    return symbols, six7, holdings


def regenerate_stocks_txt(derived_path=DERIVED_FILE):
    """Write the sorted union to stocks.txt for the analysis/backtest tooling."""
    symbols, _, _ = load_watchlist()
    with open(derived_path, "w") as f:
        f.write("\n".join(symbols) + "\n")
    return symbols


if __name__ == "__main__":
    syms = regenerate_stocks_txt()
    print(f"✓ Wrote {len(syms)} symbols to {DERIVED_FILE} (union of {SIX7_FILE} + {HOLDINGS_FILE})")

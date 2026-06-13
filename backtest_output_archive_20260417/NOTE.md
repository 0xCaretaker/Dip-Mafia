# Archived strat-test run — data as of 2026-04-17

Snapshot of the `backtest.py` strategy backtest (the "strat test") preserved for
history before re-running against the updated, larger watchlist.

- **Watchlist:** 62 symbols (see `stocks.txt` here; git commit `88bb51a`, 2026-02-08)
- **Reported in run:** 61 stocks with sufficient history
- **Period:** 2010-01-04 → 2026-04-17 (16.3 years)
- **Bollinger watch lookback:** 30 bars (`bb_lookback`)
- **Headline (from this folder's `dashboard_data.json`):**
  Timed HODL ₹207.1L (XIRR 27.6%, Sharpe 1.27, MaxDD -55.5%) ·
  SIP on stocks ₹197.3L (27.0%) · NIFTY 50 SIP ₹52.3L (10.9%) ·
  signals 152 days / 46 of 61 stocks · cash drag 5.9%

  (Note: the README in this repo previously displayed ₹194.2L for Timed HODL,
  which was stale — it did not match this run's own JSON. The authoritative
  figure for this archived run is ₹207.1L.)

Files are the full `backtest_output/` contents at that time plus the generated
`dashboard.html` (the HTML view that fed off this data).

Superseded by a fresh run against the 75-symbol `stocks.txt` with the expanded
Bollinger watch window (`bb_lookback` 60), which now lives in `backtest_output/`.

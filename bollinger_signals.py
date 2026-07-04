import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# Utility helpers
# =========================

def to_1d(x):
    arr = np.asarray(x)
    return arr.reshape(-1)


def colored_output(action):
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

    return {
        "Buy": f"{GREEN}{action}{RESET}",
        "Watch": f"{MAGENTA}{action}{RESET}",
        "Hold": f"{YELLOW}{action}{RESET}",
    }.get(action, action)


# =========================
# Bollinger Bands (Length=200)
# =========================

def calculate_bollinger_bands(df, length=200, std_dev=2):
    """
    Signal: Buy when current price touches or goes below lower band
    """
    if df.empty or len(df) < length:
        return "Hold"

    close = to_1d(df["Close"])
    low = to_1d(df["Low"])

    middle = pd.Series(close).rolling(window=length).mean().values
    std = pd.Series(close).rolling(window=length).std().values
    lower_band = middle - (std_dev * std)

    current_close = close[-1]
    current_low = low[-1]
    current_lower_band = lower_band[-1]

    if current_low <= current_lower_band or current_close <= current_lower_band:
        return "Buy"
    else:
        return "Hold"


def calculate_bb_past_lower_touch(df, length=200, std_dev=2, lookback=60):
    """
    Detect if price touched or went below lower Bollinger Band at any time in
    the past `lookback` bars (excluding current bar). Only bars where the
    rolling band is defined count, so with ~1y of data the effective window is
    capped at however many bars follow the `length`-bar warmup (~50 for 250
    bars / length=200), even if `lookback` is larger.
    """
    if df.empty or len(df) < length + 30:
        return False

    close = to_1d(df["Close"])
    low = to_1d(df["Low"])

    middle = pd.Series(close).rolling(length).mean()
    std = pd.Series(close).rolling(length).std()
    lower = middle - (std_dev * std)

    # Exclude current candle
    recent_low = low[-(lookback + 1):-1]
    recent_close = close[-(lookback + 1):-1]
    recent_lower = lower.values[-(lookback + 1):-1]

    touched = (recent_low <= recent_lower) | (recent_close <= recent_lower)
    return bool(np.any(touched))


def _position_from_levels(close, lower, middle, upper):
    """Map a price to a band-position icon. Returns None if any value is
    missing or NaN (`v != v` is True only for NaN)."""
    for v in (close, lower, middle, upper):
        if v is None or v != v:
            return None
    if close < lower:
        return "⏬"      # below lower band — deepest dip
    if close < middle:
        return "🔽"     # below mid-line
    if close < upper:
        return "🔼"     # above mid-line
    return "⏫"          # above upper band — extended


def calculate_bb_position(df, length=200, std_dev=2):
    """Where the latest close sits inside its Bollinger envelope:
    ⏬ below lower, 🔽 below mid, 🔼 above mid, ⏫ above upper.
    Returns None when there is insufficient history for the band.
    """
    if df.empty or len(df) < length:
        return None

    close = to_1d(df["Close"])
    middle = pd.Series(close).rolling(window=length).mean().values
    std = pd.Series(close).rolling(window=length).std().values

    m = middle[-1]
    s = std[-1]
    if m != m or s != s:  # NaN guard (warmup)
        return None

    lower = m - std_dev * s
    upper = m + std_dev * s
    return _position_from_levels(close[-1], lower, m, upper)


def calculate_bb_mid_distance_pct(df, length=200):
    """Signed % distance of the latest close from the 200-SMA midline
    (the Bollinger middle band). Negative = below mid (cheaper).
    Returns None on insufficient history / NaN warmup."""
    if df.empty or len(df) < length:
        return None
    close = to_1d(df["Close"])
    middle = pd.Series(close).rolling(window=length).mean().values
    m = middle[-1]
    if m != m or m == 0:  # NaN guard (warmup) / avoid div-by-zero
        return None
    return (close[-1] - m) / m * 100.0


# =========================
# Process signals from pre-downloaded data
# =========================

def process_bollinger_signals(data, stocks, length=200):
    bollinger_actions = {}

    if data.empty:
        print("Empty dataset provided")
        return bollinger_actions

    print(f"\nProcessing Bollinger Bands signals for {len(stocks)} stocks...")

    for idx, stock in enumerate(stocks, 1):
        try:
            print(f"  [{idx}/{len(stocks)}] {stock}...", end=" ", flush=True)

            if stock not in data.columns.get_level_values(1):
                raise ValueError("No data returned")

            df = data.xs(stock, axis=1, level=1)
            df = df.dropna()

            if df.empty or len(df) < length + 30:
                raise ValueError(f"Insufficient data (only {len(df)} bars, need {length + 30})")

            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
            else:
                df.index = df.index.tz_convert("Asia/Kolkata")

            action = calculate_bollinger_bands(df, length=length)

            past_touch = calculate_bb_past_lower_touch(
                df,
                length=length,
                lookback=60
            )

            if action != "Buy" and past_touch:
                action = "Watch"

            position = calculate_bb_position(df, length=length)

            bollinger_actions[stock] = {
                "action": action,
                "time": df.index[-1],
                "price": float(df["Close"].iloc[-1]),
                "position": position,
                "mid_dist_pct": calculate_bb_mid_distance_pct(df, length=length),
            }

            print("✓")

        except Exception as e:
            print(f"✗ ({str(e)[:60]})")

    return bollinger_actions


# =========================
# LEGACY: Data fetch + process
# =========================

def fetch_bollinger_signals(stocks, interval, length=200):
    print(f"\nDownloading {len(stocks)} symbols for Bollinger Bands analysis...")

    data = yf.download(
        stocks,
        period="1y",
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data.empty:
        print("Download failed: empty dataset")
        return {}

    return process_bollinger_signals(data, stocks, length)


# =========================
# Main
# =========================

if __name__ == "__main__":
    try:
        with open("stocks.txt", "r") as f:
            stocks = [line.strip() + ".NS" for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: stocks.txt not found")
        exit(1)

    interval = "1d"

    print(f"Fetching Bollinger Bands signals (Length=200) for interval: {interval}")

    results = fetch_bollinger_signals(stocks, interval, length=200)

    print("\n" + "=" * 60)
    print("BOLLINGER BANDS (Length=200)")
    print("=" * 60)

    # Separate signals
    buy_signals = {s: i for s, i in results.items() if i['action'] == 'Buy'}
    watch_signals = {s: i for s, i in results.items() if i['action'] == 'Watch'}
    hold_signals = {s: i for s, i in results.items() if i['action'] == 'Hold'}

    if buy_signals:
        print("\n🟢 BUY SIGNALS:")
        for stock, info in buy_signals.items():
            print(f"{stock} @ ₹{info['price']:.2f}: {colored_output(info['action'])}")
    else:
        print("\n🟢 No Buy signals at this time")

    if watch_signals:
        print("\n🟣 WATCH SIGNALS:")
        for stock, info in watch_signals.items():
            print(f"{stock} @ ₹{info['price']:.2f}: {colored_output(info['action'])}")
    else:
        print("\n🟣 No Watch signals")

    print(f"\n🟡 HOLD: {len(hold_signals)} stocks")


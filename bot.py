import os
import hashlib
import requests
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import yfinance as yf

from macd_signals import process_both_signals, colored_output
from bollinger_signals import process_bollinger_signals


# =========================
# Escape for Telegram MarkdownV2
# =========================
def escape_md(text):
    """Escape special characters for Telegram MarkdownV2"""
    text = str(text)
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


# =========================
# Market-hours guard (IST)
# =========================
# =========================
# Index movement
# =========================
def get_index_moves():
    index_symbols = {
        "NIFTY 50": "^NSEI",
        "NIFTY Midcap 100": "NIFTY_MIDCAP_100.NS"
    }

    index_moves = {}

    try:
        history = yf.download(
            list(index_symbols.values()),
            period="10y",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        for name, symbol in index_symbols.items():
            try:
                hist_close = history['Close'][symbol].dropna()
                if len(hist_close) == 0:
                    print(f"  ✗ {name}: no data")
                    continue
                ath = hist_close.max()

                hist_open = history['Open'][symbol].dropna()
                latest_close = hist_close.iloc[-1]
                latest_open = hist_open.iloc[-1] if len(hist_open) > 0 else latest_close

                pct_move = ((latest_close - latest_open) / latest_open) * 100 if latest_open else 0
                from_ath_pct = ((latest_close - ath) / ath) * 100 if ath else 0

                index_moves[name] = {
                    "pct_move": round(pct_move, 2),
                    "from_ath": round(from_ath_pct, 2),
                }
            except Exception as e:
                print(f"  ✗ {name}: {e}")

    except Exception as e:
        print(f"Error fetching index data: {e}")

    return index_moves


# =========================
# Telegram sender (Filtered by Bollinger Bands)
# =========================
def send_bulk_telegram_message(all_interval_signals, bollinger_signals, index_moves):
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "").split(",")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS[0]:
        print("Error: TELEGRAM_TOKEN and TELEGRAM_CHAT_IDS env vars required")
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'

    emoji = {
        "Buy": "🟢",
        "Sell": "🔴",
        "Hold": "🟡",
        "Wait for Buy": "🟣",
        "Watch": "🟣"
    }

    # Create filter set: only stocks with Bollinger Buy or Watch signals
    bollinger_filter = {
        stock for stock, info in bollinger_signals.items()
        if info["action"] in ["Buy", "Watch"]
    }

    # Column widths over the lines that actually render (Buy/Sell across all
    # sections), so the ticker and price columns line up in monospace.
    name_widths = [0]
    price_widths = [0]
    for all_signals in all_interval_signals.values():
        for stock, info in all_signals.items():
            action, time, price = info["action"], info["time"], info["price"]
            if action in ("Buy", "Sell") and time and price:
                name = stock.replace(".NS", "").replace(".BO", "")
                name_widths.append(len(name))
                price_widths.append(len(f"{price:.2f}"))

    max_len = max(name_widths)
    price_width = max(price_widths)

    combined_lines = []
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    day = now.strftime('%d %b').lstrip('0')
    clock = now.strftime('%I:%M %p').lstrip('0')
    combined_lines.append("🩸 *DIP MAFIA*")
    combined_lines.append(f"_signal alert · {escape_md(day)} · {escape_md(clock)} IST_")
    combined_lines.append("")

    # Index summary
    if index_moves:
        for name, info in index_moves.items():
            pct = info['pct_move']
            ath_diff = info['from_ath']
            arrow = "🔺" if pct > 0 else "🔻"
            short = {"NIFTY Midcap 100": "MIDCAP 100"}.get(name, name)
            pct_str = f"{pct:+.2f}%"
            ath_str = f"{ath_diff:+.1f}%"
            combined_lines.append(
                f"{arrow} *{escape_md(short)}*  `{pct_str}`  ·  ATH `{ath_str}`"
            )
        combined_lines.append("")

    # Compute sentiment first (need it before MACD sections)
    sentiment_parts = []
    for interval, all_signals in all_interval_signals.items():
        total = hold_count = wait_count = 0
        for stock, info in all_signals.items():
            if stock not in bollinger_filter:
                continue
            action = info["action"]
            if action:
                total += 1
                if action == "Hold":
                    hold_count += 1
                elif action == "Wait for Buy":
                    wait_count += 1
        if total > 0:
            sentiment_parts.append((interval, (hold_count / total) * 100, (wait_count / total) * 100))

    if sentiment_parts:
        avg_hold = sum(h for _, h, _ in sentiment_parts) / len(sentiment_parts)
        avg_wait = sum(w for _, _, w in sentiment_parts) / len(sentiment_parts)
        if avg_hold >= 70:
            mood, icon = "Bullish", "🟢"
        elif avg_hold >= 40:
            mood, icon = "Neutral", "🟡"
        elif avg_wait >= 70:
            mood, icon = "Bearish", "🔴"
        else:
            mood, icon = "Cautious", "🟠"
        combined_lines.append(f"{icon} *Sentiment: {mood}*")

    # A monospace rule sized to the data columns: long enough to feel like a
    # real divider, but never wider than the rows (so it can't wrap on mobile).
    content_width = max_len + 2 + price_width  # "{ticker} ₹{price}"
    divider = "`" + "─" * max(content_width, 10) + "`"
    rendered = [False]

    # MACD section builder. filter_set=None renders the full universe;
    # otherwise only symbols in filter_set (e.g. the Bollinger filter) render.
    def append_macd_section(title, all_signals, filter_set):
        entries = []
        total = hold_count = wait_count = 0

        for stock, info in all_signals.items():
            if filter_set is not None and stock not in filter_set:
                continue
            action, time, price = info["action"], info["time"], info["price"]
            if action and time and price:
                total += 1
                if action == "Hold":
                    hold_count += 1
                elif action == "Wait for Buy":
                    wait_count += 1
            if action in ["Buy", "Sell"] and time and price:
                stock_clean = stock.replace(".NS", "").replace(".BO", "")
                position = bollinger_signals.get(stock, {}).get("position")
                entries.append((stock_clean, action, price, position))

        if not entries and total == 0:
            return

        combined_lines.append("")
        if rendered[0]:          # divider only *between* sections, not before the first
            combined_lines.append(divider)
        rendered[0] = True
        combined_lines.append(title)

        for stock, action, price, position in entries:
            padded_stock = stock.ljust(max_len)
            price_str = f"{price:.2f}".rjust(price_width)
            pos_prefix = f"{position} " if position else ""
            combined_lines.append(
                f"{emoji[action]} {pos_prefix}`{padded_stock} ₹{price_str}`"
            )

        if total > 0:
            wait_pct = (wait_count / total) * 100
            hold_pct = (hold_count / total) * 100
            combined_lines.append("")
            combined_lines.append(
                f"🟣 Wait for Buy `{wait_count}/{total} · {wait_pct:.1f}%`"
            )
            combined_lines.append(
                f"🟡 Hold `{hold_count}/{total} · {hold_pct:.1f}%`"
            )

    std_signals = all_interval_signals.get("1d", {})
    impulse_signals = all_interval_signals.get("1d Impulse MACD", {})

    # 1) Standard MACD — full universe, no Bollinger gate (earlier, noisier read)
    append_macd_section("📈 *Early Signal* _\\(MACD\\)_", std_signals, None)
    # 2) Impulse MACD — full universe, no Bollinger gate (stronger confirmation)
    append_macd_section("⚡ *Strong Signal* _\\(iMACD\\)_", impulse_signals, None)
    # 3) Bollinger + Impulse MACD — impulse gated by the Bollinger filter (the verdict)
    append_macd_section("🎯 *THE VERDICT* _\\(Boll \\+ iMACD\\)_", impulse_signals, bollinger_filter)

    # Footer: arrow legend + the "we never sell" reminder.
    if rendered[0]:
        combined_lines.append("")
        combined_lines.append(divider)
        combined_lines.append("ℹ️ *BTW — what the arrows mean*")
        combined_lines.append("⏬ deep dip · 🔽 undervalued")
        combined_lines.append("🔼 above avg · ⏫ overvalued")
        combined_lines.append("")
        combined_lines.append(
            "_Dip Mafia never sells — red just flags weakness · we only buy dips & HODL_"
        )

    # Nothing rendered → nothing worth sending.
    if not rendered[0]:
        return

    # Collapse runs of blank lines and trim edges for even spacing.
    cleaned = []
    for line in combined_lines:
        if line == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    final_message = "\n".join(cleaned)

    # Hash raw signal data (actions + prices) — independent of formatting/timestamps
    signal_data = []
    for interval, all_signals in all_interval_signals.items():
        for stock in sorted(all_signals):
            info = all_signals[stock]
            signal_data.append(f"{interval}:{stock}:{info['action']}:{info['price']:.2f}")
    for stock in sorted(bollinger_signals):
        signal_data.append(f"BB:{stock}:{bollinger_signals[stock]['action']}")
    current_hash = hashlib.sha256("\n".join(signal_data).encode()).hexdigest()[:16]

    hash_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_signal_hash")
    prev_hash = ""
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            prev_hash = f.read().strip()

    print("\n" + "=" * 60)
    print("TELEGRAM MESSAGE:")
    print("=" * 60)
    print(final_message)
    print("=" * 60)

    if current_hash == prev_hash:
        print("⏭️  Skipping Telegram — signals unchanged from last run")
        return

    with open(hash_file, "w") as f:
        f.write(current_hash)

    print(f"📤 Sending to Telegram (hash: {current_hash})\n")

    for chat_id in TELEGRAM_CHAT_IDS:
        data = {
            'chat_id': chat_id,
            'text': final_message,
            'parse_mode': 'MarkdownV2'
        }
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Telegram Error: {e}")


# =========================
# Main logic
# =========================
def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(ZoneInfo("Asia/Kolkata"))

    print("UTC Time:", now_utc.strftime('%Y-%m-%d %H:%M:%S'))
    print("IST Time:", now_ist.strftime('%Y-%m-%d %H:%M:%S'))

    try:
        with open("stocks.txt", "r") as f:
            stocks = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: stocks.txt file not found.")
        return

    stocks = [s + ".NS" for s in stocks]
    intervals = ["1d"]

    index_moves = get_index_moves()

    print("\n" + "=" * 60)
    print("DOWNLOADING DATA...")
    print("=" * 60)

    data = yf.download(
        stocks,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data.empty:
        print("Download failed: empty dataset")
        return

    print(f"✓ Downloaded data for {len(stocks)} stocks")

    all_interval_signals = {}

    for interval in intervals:
        results_macd, results_impulse = process_both_signals(data, stocks)

        all_interval_signals[interval] = results_macd
        all_interval_signals[f"{interval} Impulse MACD"] = results_impulse

    bollinger_results = process_bollinger_signals(data, stocks, length=200)

    from bollinger_signals import colored_output as bb_colored_output

    bollinger_filter = {
        s for s, i in bollinger_results.items()
        if i["action"] in ["Buy", "Watch"]
    }

    # Console: Bollinger Bands
    print("\n" + "=" * 60)
    print("BOLLINGER BANDS (Length=200)")
    print("=" * 60)

    buy_signals = {s: i for s, i in bollinger_results.items() if i['action'] == 'Buy'}
    watch_signals = {s: i for s, i in bollinger_results.items() if i['action'] == 'Watch'}
    hold_signals = {s: i for s, i in bollinger_results.items() if i['action'] == 'Hold'}

    if buy_signals:
        print("\n🟢 BUY SIGNALS:")
        for stock, info in buy_signals.items():
            print(f"  {stock:<20} ₹{info['price']:>10.2f}  {bb_colored_output(info['action'])}")
    else:
        print("\n🟢 No Buy signals at this time")

    if watch_signals:
        print("\n🟣 WATCH SIGNALS:")
        for stock, info in watch_signals.items():
            print(f"  {stock:<20} ₹{info['price']:>10.2f}  {bb_colored_output(info['action'])}")
    else:
        print("\n🟣 No Watch signals")

    print(f"\n🟡 HOLD: {len(hold_signals)} stocks")

    # Console: MACD signals (full detail)
    for interval, all_signals in all_interval_signals.items():
        print("\n" + "=" * 60)
        label = "IMPULSE MACD (LazyBear)" if "Impulse" in interval else "STANDARD MACD"
        print(f"{label} — {interval}")
        print("=" * 60)

        grouped = {"Buy": [], "Sell": [], "Hold": [], "Wait for Buy": []}
        for stock, info in all_signals.items():
            action = info["action"]
            if action in grouped:
                bb = bollinger_results.get(stock, {}).get("action", "-")
                grouped[action].append((stock, info["price"], bb))

        total = sum(len(v) for v in grouped.values())
        for action_name, items in grouped.items():
            if not items:
                continue
            pct = (len(items) / total) * 100 if total else 0
            print(f"\n  {colored_output(action_name)} ({len(items)}/{total}, {pct:.0f}%):")
            for stock, price, bb in items:
                in_filter = "✓" if stock in bollinger_filter else " "
                print(f"    {in_filter} {stock:<20} ₹{price:>10.2f}  [BB:{bb}]")

        if total > 0:
            hold_n = len(grouped["Hold"])
            wait_n = len(grouped["Wait for Buy"])
            hold_pct = (hold_n / total) * 100
            wait_pct = (wait_n / total) * 100
            if hold_pct >= 70:
                mood = "\033[92mBullish\033[0m"
            elif hold_pct >= 40:
                mood = "\033[93mNeutral\033[0m"
            elif wait_pct >= 70:
                mood = "\033[91mBearish\033[0m"
            else:
                mood = "\033[95mCautious\033[0m"
            print(f"\n  Sentiment: {mood}")

    print()
    send_bulk_telegram_message(all_interval_signals, bollinger_results, index_moves)


if __name__ == "__main__":
    main()

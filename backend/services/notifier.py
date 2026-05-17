"""
Telegram Notifier — VMC + Money Flow + MTF Confirmation alerts.
"""

import os
import httpx

SIGNAL_EMOJI = {
    "green_dot": "🟢", "red_dot": "🔴", "gold_dot": "🟡",
    "bull_div": "🔵", "bear_div": "🟠",
    "bull_div_hidden": "🫐", "bear_div_hidden": "🍊",
}

SIGNAL_LABEL = {
    "green_dot": "Green Dot (BUY)", "red_dot": "Red Dot (SELL)",
    "gold_dot": "Gold Dot (STRONG BUY)", "bull_div": "Bullish Divergence",
    "bear_div": "Bearish Divergence", "bull_div_hidden": "Hidden Bull Divergence",
    "bear_div_hidden": "Hidden Bear Divergence",
}

DIRECTION = {
    "green_dot": "LONG", "gold_dot": "LONG",
    "bull_div": "LONG",  "bull_div_hidden": "LONG",
    "red_dot": "SHORT",  "bear_div": "SHORT", "bear_div_hidden": "SHORT",
}

STRENGTH_EMOJI  = {"STRONG": "🔥", "MODERATE": "⚡", "WEAK": "⚠️"}
BIAS_EMOJI      = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➖"}
CONFIRM_EMOJI   = {"CONFIRMED": "✅", "NEUTRAL": "⚡", "AGAINST": "❌"}


def _build_message(
    symbol: str,
    timeframe: str,
    signal_type: str,
    bar: dict,
    mf: dict = None,
    mtf: dict = None,
) -> str:
    emoji  = SIGNAL_EMOJI.get(signal_type, "⚡")
    label  = SIGNAL_LABEL.get(signal_type, signal_type)
    direc  = DIRECTION.get(signal_type, "—")
    price  = bar.get("close", 0)
    wt1    = bar.get("wt1", 0)
    wt2    = bar.get("wt2", 0)
    rsimfi = bar.get("rsimfi", 0)
    ts     = bar.get("timestamp", "")

    dir_line = "📈 Direction : LONG  (look for longs)" if direc == "LONG" \
               else "📉 Direction : SHORT (look for shorts)"

    msg = (
        f"{emoji} *VMC Cipher B Alert*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Signal   : *{label}*\n"
        f"💎 Pair     : `{symbol}`\n"
        f"⏱ Timeframe: `{timeframe}`\n"
        f"💰 Price    : `{price:,.4f}`\n"
        f"{dir_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Indicator Values*\n"
        f"  WT1     : `{wt1:.2f}`\n"
        f"  WT2     : `{wt2:.2f}`\n"
        f"  RSI+MFI : `{rsimfi:.2f}`\n"
    )

    # Money Flow section
    if mf and mf.get("strength") not in (None, "UNKNOWN"):
        strength   = mf.get("strength", "—")
        mf_bias    = mf.get("mf_bias", "NEUTRAL")
        score      = mf.get("score", 50)
        cmf        = mf.get("cmf", 0)
        mfi_val    = mf.get("mfi", 50)
        obv        = mf.get("obv_trend", "—")
        vol_ratio  = mf.get("vol_ratio", 1.0)
        spike      = mf.get("vol_spike", False)
        confluence = mf.get("confluence", 0)
        s_emoji    = STRENGTH_EMOJI.get(strength, "⚡")
        b_emoji    = BIAS_EMOJI.get(mf_bias, "➖")
        reasons    = mf.get("reasons", [])

        msg += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Money Flow*\n"
            f"  {b_emoji} Bias      : *{mf_bias}*\n"
            f"  {s_emoji} Strength  : *{strength}* ({score}/100)\n"
            f"  📐 Confluence: {confluence}/5\n"
            f"  CMF  : `{cmf:+.3f}` {'🟢' if cmf > 0.1 else '🔴' if cmf < -0.1 else '⚪'}\n"
            f"  MFI  : `{mfi_val:.0f}` {'🟢' if mfi_val < 30 else '🔴' if mfi_val > 70 else '⚪'}\n"
            f"  OBV  : `{obv}`\n"
            f"  Vol  : `{vol_ratio:.1f}x` {'🔥 SPIKE' if spike else ''}\n"
        )
        if reasons:
            msg += f"  💡 _{reasons[0]}_\n"

    # MTF Confirmation section
    if mtf:
        htf_tf     = mtf.get("htf_label", mtf.get("htf_timeframe", "HTF"))
        confirm    = mtf.get("htf_confirmation", "NEUTRAL")
        htf_score  = mtf.get("htf_score", 50)
        htf_trend  = mtf.get("htf_trend", "—")
        htf_wt1    = mtf.get("htf_wt1", 0)
        htf_wt2    = mtf.get("htf_wt2", 0)
        htf_cmf    = mtf.get("htf_cmf", 0)
        c_emoji    = CONFIRM_EMOJI.get(confirm, "⚡")
        filter_r   = mtf.get("filter_reason")
        htf_reasons = mtf.get("htf_reasons", [])

        msg += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔭 *{htf_tf} Confirmation*\n"
            f"  {c_emoji} Status : *{confirm}* ({htf_score}/100)\n"
            f"  📊 Trend  : `{htf_trend}`\n"
            f"  WT1/WT2  : `{htf_wt1:.1f}` / `{htf_wt2:.1f}`\n"
            f"  CMF      : `{htf_cmf:+.3f}`\n"
        )
        if htf_reasons:
            msg += f"  💡 _{htf_reasons[0]}_\n"
        if filter_r and confirm == "AGAINST":
            msg += f"  🚫 _{filter_r}_\n"

        # Overall grade
        if mf and mtf:
            mf_score  = mf.get("score", 50)
            overall   = max(0, min(100, round((mf_score * 0.4) + (htf_score * 0.6))))
            if overall >= 75:
                grade = "A 🔥 High Confidence"
            elif overall >= 60:
                grade = "B ⚡ Moderate Confidence"
            elif overall >= 45:
                grade = "C ⚠️ Low Confidence"
            else:
                grade = "D ❌ Avoid"
            msg += f"  🏆 Grade  : *{grade}*\n"

    msg += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Candle   : `{ts}`\n"
        f"⚠️ _For reference only. Not financial advice._"
    )
    return msg


async def send_alert(
    symbol: str,
    timeframe: str,
    signal_type: str,
    bar: dict,
    mf: dict = None,
    mtf: dict = None,
) -> bool:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("[Notifier] Telegram not configured — skipping alert")
        return False

    message = _build_message(symbol, timeframe, signal_type, bar, mf, mtf)
    url     = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id, "text": message, "parse_mode": "Markdown",
            })
            resp.raise_for_status()
            print(f"[Notifier] Sent: {symbol} {timeframe} {signal_type}")
            return True
    except Exception as e:
        print(f"[Notifier] Failed: {e}")
        return False


async def send_startup_message(pairs: list) -> None:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return

    pairs_str = "\n".join([f"  • `{p['symbol']}` @ {p['timeframe']}" for p in pairs])
    msg = (
        f"🚀 *VMC Monitor Started*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Watching:\n{pairs_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ VMC Cipher B signals\n"
        f"💵 Money Flow analysis\n"
        f"🔭 Multi-timeframe confirmation\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 Green/Gold = Buy  |  🔴 Red = Sell"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            )
    except Exception as e:
        print(f"[Notifier] Startup message failed: {e}")
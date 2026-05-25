"""
AI Chat & Auto-Analysis Service
- chat(): answers user questions using live dashboard context
- generate_auto_analysis(): writes a full trade breakdown for Telegram alerts
"""

import os
import json
import httpx

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-sonnet-4-5"


# ─── System Prompts ───────────────────────────────────────────────────────────

CHAT_SYSTEM = """You are an expert crypto trading analyst specialising in the 
VuManChu Cipher B divergence indicator, money flow analysis, and multi-timeframe 
confirmation. You have access to REAL computed data from live market candles.

Your job is to give clear, direct, actionable analysis. Never be vague.
Always reference the actual numbers in your response.
Keep responses concise — 3-6 sentences max unless asked for more detail.
Format key numbers in backticks. Use ✅ ⚠️ ❌ for quick visual scanning.
Never give financial advice — frame everything as analysis, not instruction.
End responses with one clear takeaway line."""

AUTO_ANALYSIS_SYSTEM = """You are an expert crypto trading analyst. 
Write a concise trade analysis paragraph (4-6 sentences) based on the provided 
signal data. Be specific, reference actual numbers, and give a clear recommendation.
Do not use headers or bullet points — write flowing prose.
End with one sentence stating the overall trade quality grade (A/B/C/D)."""


# ─── Chat ─────────────────────────────────────────────────────────────────────

async def chat(
    message:       str,
    symbol:        str,
    timeframe:     str,
    signal_type:   str = None,
    backtest_stats: dict = None,
    money_flow:    dict = None,
    mtf:           dict = None,
    latest_bar:    dict = None,
    history:       list = None,
) -> str:
    """
    Answer a user question using all available dashboard context.
    history: list of {role, content} previous messages
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Build context block
    context_parts = [f"Current analysis context: {symbol} {timeframe}"]

    if latest_bar:
        context_parts.append(
            f"Latest closed candle: price={latest_bar.get('close', 'N/A')}, "
            f"WT1={latest_bar.get('wt1', 'N/A')}, WT2={latest_bar.get('wt2', 'N/A')}, "
            f"RSI+MFI={latest_bar.get('rsimfi', 'N/A')}"
        )

    if signal_type:
        context_parts.append(f"Active signal: {signal_type}")

    if backtest_stats and not backtest_stats.get("error"):
        context_parts.append(
            f"Backtest results ({backtest_stats.get('total_trades', 0)} trades): "
            f"win rate={backtest_stats.get('win_rate', 0)}%, "
            f"avg R:R={backtest_stats.get('avg_rr', 0)}, "
            f"profit factor={backtest_stats.get('profit_factor', 'N/A')}, "
            f"max drawdown={backtest_stats.get('max_drawdown', 0)}%"
        )
        by_signal = backtest_stats.get("by_signal", {})
        if by_signal:
            sig_summary = ", ".join(
                [f"{k}: {v['win_rate']}% ({v['total']} trades)"
                 for k, v in by_signal.items()]
            )
            context_parts.append(f"Signal breakdown: {sig_summary}")

    if money_flow:
        context_parts.append(
            f"Money flow: bias={money_flow.get('mf_bias', 'N/A')}, "
            f"strength={money_flow.get('strength', 'N/A')} ({money_flow.get('score', 0)}/100), "
            f"CMF={money_flow.get('cmf', 0)}, MFI={money_flow.get('mfi', 50)}, "
            f"OBV={money_flow.get('obv_trend', 'N/A')}, "
            f"volume={money_flow.get('vol_ratio', 1.0)}x avg "
            f"{'(SPIKE)' if money_flow.get('vol_spike') else ''}"
        )

    if mtf:
        context_parts.append(
            f"HTF confirmation ({mtf.get('htf_label', 'HTF')}): "
            f"{mtf.get('htf_confirmation', 'N/A')} ({mtf.get('htf_score', 0)}/100), "
            f"trend={mtf.get('htf_trend', 'N/A')}, "
            f"WT1={mtf.get('htf_wt1', 0)}, WT2={mtf.get('htf_wt2', 0)}, "
            f"CMF={mtf.get('htf_cmf', 0)}"
        )
        if mtf.get("grade"):
            context_parts.append(f"Overall grade: {mtf.get('grade')}")

    context_block = "\n".join(context_parts)

    # Build messages
    messages = []

    # Add history (last 10 messages to stay within context)
    if history:
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})

    # Add current message with context
    user_content = f"{context_block}\n\nUser question: {message}"
    messages.append({"role": "user", "content": user_content})

    headers = {
        "Content-Type":    "application/json",
        "x-api-key":       api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model":      MODEL,
        "max_tokens": 1000,
        "system":     CHAT_SYSTEM,
        "messages":   messages,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Anthropic error {response.status_code}: {response.text}")
        data = response.json()

    return data["content"][0]["text"]


# ─── Auto Analysis (for Telegram) ────────────────────────────────────────────

async def generate_auto_analysis(
    symbol:      str,
    timeframe:   str,
    signal_type: str,
    bar:         dict,
    mf:          dict,
    mtf:         dict,
) -> str:
    """
    Generate a concise written analysis paragraph for a signal alert.
    This gets appended to Telegram notifications.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""

    # Map signal to readable name
    signal_labels = {
        "green_dot": "Green Dot (WT bullish cross at oversold)",
        "red_dot":   "Red Dot (WT bearish cross at overbought)",
        "gold_dot":  "Gold Dot (extreme oversold WT cross)",
        "bull_div":  "Bullish Divergence (price lower low, WT higher low)",
        "bear_div":  "Bearish Divergence (price higher high, WT lower high)",
        "bull_div_hidden": "Hidden Bullish Divergence",
        "bear_div_hidden": "Hidden Bearish Divergence",
    }
    sig_label = signal_labels.get(signal_type, signal_type)

    mf_strength  = mf.get("strength", "UNKNOWN")
    mf_bias      = mf.get("mf_bias", "NEUTRAL")
    mf_score     = mf.get("score", 50)
    cmf          = mf.get("cmf", 0)
    mfi          = mf.get("mfi", 50)
    obv          = mf.get("obv_trend", "Unknown")
    vol_ratio    = mf.get("vol_ratio", 1.0)
    vol_spike    = mf.get("vol_spike", False)
    confluence   = mf.get("confluence", 0)

    htf_label    = mtf.get("htf_label", "HTF")
    htf_confirm  = mtf.get("htf_confirmation", "NEUTRAL")
    htf_score    = mtf.get("htf_score", 50)
    htf_trend    = mtf.get("htf_trend", "UNKNOWN")
    htf_wt2      = mtf.get("htf_wt2", 0)
    htf_cmf      = mtf.get("htf_cmf", 0)
    should_trade = mtf.get("should_trade", True)
    overall_score = round((mf_score * 0.4) + (htf_score * 0.6))

    if overall_score >= 75:
        grade = "A"
    elif overall_score >= 60:
        grade = "B"
    elif overall_score >= 45:
        grade = "C"
    else:
        grade = "D"

    prompt = f"""Analyse this crypto trade signal and write 4-5 sentences of clear analysis:

Signal: {sig_label} on {symbol} {timeframe}
Price: {bar.get('close', 0):,.4f}
WT1: {bar.get('wt1', 0):.2f} | WT2: {bar.get('wt2', 0):.2f} | RSI+MFI: {bar.get('rsimfi', 0):.2f}

Money Flow ({mf_strength} — {mf_score}/100):
- Bias: {mf_bias}
- CMF: {cmf:+.3f} | MFI: {mfi:.0f} | OBV: {obv}
- Volume: {vol_ratio:.1f}x average {'(SPIKE detected)' if vol_spike else ''}
- {confluence}/5 indicators confirming

{htf_label} Confirmation ({htf_confirm} — {htf_score}/100):
- Trend: {htf_trend} | WT2: {htf_wt2:.1f} | CMF: {htf_cmf:+.3f}
- Should trade: {'Yes' if should_trade else 'No — HTF opposes signal'}

Overall score: {overall_score}/100

Write a clear analysis paragraph. Reference specific numbers.
End the last sentence with: "Grade: {grade} — [one word quality description]."
Keep it under 5 sentences total."""

    headers = {
        "Content-Type":    "application/json",
        "x-api-key":       api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model":    MODEL,
        "max_tokens": 400,
        "system":   AUTO_ANALYSIS_SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
            if response.status_code != 200:
                print(f"[AI Chat] Auto-analysis failed: {response.status_code}")
                return ""
            data = response.json()
            return data["content"][0]["text"]
    except Exception as e:
        print(f"[AI Chat] Auto-analysis error: {e}")
        return ""
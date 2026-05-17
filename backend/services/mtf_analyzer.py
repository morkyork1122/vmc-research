"""
Multi-Timeframe Confirmation Analyzer
Checks the higher timeframe before confirming a primary timeframe signal.

TF ladder:
  1m → 15m → 1H → 4H → 1D → 1W

Confirmation rating:
  CONFIRMED (score >= 70) → HTF agrees, trade with confidence
  NEUTRAL   (score 45-69) → HTF is mixed, trade with caution
  AGAINST   (score < 45)  → HTF disagrees, skip this trade
"""

from indicators.vmc_cipher_b import compute_all
from indicators.money_flow import compute_money_flow
from services.data_fetcher import fetch_ohlcv


HIGHER_TF_MAP = {
    "1m": "15m", "5m": "1H", "15m": "1H",
    "30m": "4H", "1H": "4H", "4H": "1D", "1D": "1W", "1W": "1W",
}

TF_LABEL = {
    "1m": "1 Min", "5m": "5 Min", "15m": "15 Min", "30m": "30 Min",
    "1H": "1 Hour", "4H": "4 Hour", "1D": "Daily", "1W": "Weekly",
}

LONG_SIGNALS  = ["green_dot", "gold_dot", "bull_div", "bull_div_hidden"]
SHORT_SIGNALS = ["red_dot",   "bear_div", "bear_div_hidden"]


def get_higher_timeframe(tf: str) -> str:
    return HIGHER_TF_MAP.get(tf, "1D")


async def analyze_htf(symbol: str, primary_tf: str, signal_type: str) -> dict:
    htf      = get_higher_timeframe(primary_tf)
    is_long  = signal_type in LONG_SIGNALS
    is_short = signal_type in SHORT_SIGNALS

    if htf == primary_tf:
        return _neutral_result(htf, "Already on highest supported timeframe")

    try:
        df = await fetch_ohlcv(symbol, htf, limit=100)
        df = compute_all(df)
        df = compute_money_flow(df)
    except Exception as e:
        return _neutral_result(htf, f"Could not fetch HTF data: {e}")

    if len(df) < 3:
        return _neutral_result(htf, "Not enough HTF candles")

    bar      = df.iloc[-2]
    score    = 50
    reasons  = []

    wt1      = float(bar.get("wt1", 0) or 0)
    wt2      = float(bar.get("wt2", 0) or 0)
    cmf      = float(bar.get("cmf", 0) or 0)
    mfi      = float(bar.get("mfi", 50) or 50)
    obv_bull = bool(bar.get("obv_trend", False))
    wt_cross_up   = bool(bar.get("wt_cross_up", False))
    wt_cross_down = bool(bar.get("wt_cross_down", False))
    label    = TF_LABEL.get(htf, htf)

    # ── WT Trend (+/-20) ──────────────────────────────────────────────────────
    htf_bull = wt1 > wt2
    if is_long and htf_bull:
        score += 20
        reasons.append(f"✅ {label} WT bullish — WT1 above WT2")
    elif is_short and not htf_bull:
        score += 20
        reasons.append(f"✅ {label} WT bearish — WT1 below WT2")
    elif is_long:
        score -= 20
        reasons.append(f"❌ {label} WT bearish — opposes buy signal")
    else:
        score -= 20
        reasons.append(f"❌ {label} WT bullish — opposes sell signal")

    # ── WT Level (+/-15) ──────────────────────────────────────────────────────
    if is_long and wt2 < 0:
        score += 10
        reasons.append(f"✅ {label} WT2 {wt2:.1f} — below zero, room to rally")
    elif is_long and wt2 > 53:
        score -= 15
        reasons.append(f"⚠️ {label} WT2 overbought at {wt2:.1f} — risky for longs")
    elif is_short and wt2 > 0:
        score += 10
        reasons.append(f"✅ {label} WT2 {wt2:.1f} — above zero, room to fall")
    elif is_short and wt2 < -53:
        score -= 15
        reasons.append(f"⚠️ {label} WT2 oversold at {wt2:.1f} — risky for shorts")

    # ── CMF (+/-12) ───────────────────────────────────────────────────────────
    if is_long and cmf > 0.05:
        score += 12
        reasons.append(f"✅ {label} CMF {cmf:+.3f} — money flowing in")
    elif is_short and cmf < -0.05:
        score += 12
        reasons.append(f"✅ {label} CMF {cmf:+.3f} — money flowing out")
    elif is_long and cmf < -0.05:
        score -= 10
        reasons.append(f"❌ {label} CMF {cmf:+.3f} — outflow on HTF")
    elif is_short and cmf > 0.05:
        score -= 10
        reasons.append(f"❌ {label} CMF {cmf:+.3f} — inflow opposes short")
    else:
        reasons.append(f"➖ {label} CMF {cmf:+.3f} — neutral")

    # ── MFI (+/-10) ───────────────────────────────────────────────────────────
    if is_long and mfi < 40:
        score += 10
        reasons.append(f"✅ {label} MFI {mfi:.0f} — not overbought")
    elif is_short and mfi > 60:
        score += 10
        reasons.append(f"✅ {label} MFI {mfi:.0f} — not oversold")
    elif is_long and mfi > 75:
        score -= 10
        reasons.append(f"⚠️ {label} MFI {mfi:.0f} — overbought on HTF")
    elif is_short and mfi < 25:
        score -= 10
        reasons.append(f"⚠️ {label} MFI {mfi:.0f} — oversold on HTF")

    # ── OBV (+8) ─────────────────────────────────────────────────────────────
    if is_long and obv_bull:
        score += 8
        reasons.append(f"✅ {label} OBV rising — institutional accumulation")
    elif is_short and not obv_bull:
        score += 8
        reasons.append(f"✅ {label} OBV falling — institutional distribution")
    else:
        reasons.append(f"➖ {label} OBV {'rising' if obv_bull else 'falling'} — mixed")

    # ── Fresh HTF Cross bonus (+10) ───────────────────────────────────────────
    if is_long and wt_cross_up:
        score += 10
        reasons.append(f"🔥 {label} fresh bullish WT cross — exceptional timing!")
    elif is_short and wt_cross_down:
        score += 10
        reasons.append(f"🔥 {label} fresh bearish WT cross — exceptional timing!")

    score = max(0, min(100, score))

    # ── Confirmation label ────────────────────────────────────────────────────
    if score >= 70:
        confirmation = "CONFIRMED"
        should_trade = True
        filter_reason = None
    elif score >= 45:
        confirmation = "NEUTRAL"
        should_trade = True
        filter_reason = f"{label} is mixed — trade smaller size"
    else:
        confirmation = "AGAINST"
        should_trade = False
        filter_reason = f"{label} opposes signal — skip this trade"

    # ── HTF trend label ───────────────────────────────────────────────────────
    if wt1 > wt2 and wt2 < -10:
        htf_trend = "BULLISH (Oversold)"
    elif wt1 > wt2:
        htf_trend = "BULLISH"
    elif wt1 < wt2 and wt2 > 10:
        htf_trend = "BEARISH (Overbought)"
    elif wt1 < wt2:
        htf_trend = "BEARISH"
    else:
        htf_trend = "NEUTRAL"

    return {
        "htf_timeframe":    htf,
        "htf_label":        label,
        "htf_confirmation": confirmation,
        "htf_score":        score,
        "htf_trend":        htf_trend,
        "htf_wt1":          round(wt1, 2),
        "htf_wt2":          round(wt2, 2),
        "htf_cmf":          round(cmf, 4),
        "htf_mfi":          round(mfi, 1),
        "htf_obv_trend":    "Rising ↑" if obv_bull else "Falling ↓",
        "htf_reasons":      reasons,
        "should_trade":     should_trade,
        "filter_reason":    filter_reason,
    }


def combined_score(mf_score: int, htf_score: int) -> dict:
    overall = max(0, min(100, round((mf_score * 0.4) + (htf_score * 0.6))))
    if overall >= 75:
        grade = "A — High Confidence"
    elif overall >= 60:
        grade = "B — Moderate Confidence"
    elif overall >= 45:
        grade = "C — Low Confidence"
    else:
        grade = "D — Avoid"
    return {"overall_score": overall, "grade": grade}


def _neutral_result(htf: str, reason: str) -> dict:
    return {
        "htf_timeframe": htf, "htf_label": TF_LABEL.get(htf, htf),
        "htf_confirmation": "NEUTRAL", "htf_score": 50,
        "htf_trend": "UNKNOWN", "htf_wt1": 0, "htf_wt2": 0,
        "htf_cmf": 0, "htf_mfi": 50, "htf_obv_trend": "Unknown",
        "htf_reasons": [f"➖ {reason}"],
        "should_trade": True, "filter_reason": reason,
    }
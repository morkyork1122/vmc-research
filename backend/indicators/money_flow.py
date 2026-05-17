"""
Money Flow Analysis
Computes: OBV, CMF, MFI, Volume Delta, Volume Spike, Signal Strength Scorer
"""

import pandas as pd
import numpy as np


def compute_obv(df: pd.DataFrame) -> pd.DataFrame:
    obv = [0]
    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv.append(obv[-1] + df["volume"].iloc[i])
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv.append(obv[-1] - df["volume"].iloc[i])
        else:
            obv.append(obv[-1])
    df["obv"]       = obv
    df["obv_ema"]   = df["obv"].ewm(span=20, adjust=False).mean()
    df["obv_trend"] = df["obv"] > df["obv_ema"]
    return df


def compute_cmf(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    hl_range = (df["high"] - df["low"]).replace(0, np.nan)
    mfm      = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl_range
    mfv      = mfm.fillna(0) * df["volume"]
    df["cmf"] = mfv.rolling(period).sum() / df["volume"].rolling(period).sum()
    return df


def compute_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    tp     = (df["high"] + df["low"] + df["close"]) / 3
    raw_mf = tp * df["volume"]
    pos_mf = raw_mf.where(tp > tp.shift(1), 0)
    neg_mf = raw_mf.where(tp < tp.shift(1), 0)
    mfr    = pos_mf.rolling(period).sum() / neg_mf.rolling(period).sum().replace(0, np.nan)
    df["mfi"] = (100 - (100 / (1 + mfr))).fillna(50)
    return df


def compute_volume_delta(df: pd.DataFrame) -> pd.DataFrame:
    hl_range            = (df["high"] - df["low"]).replace(0, np.nan)
    buy_ratio           = ((df["close"] - df["low"]) / hl_range).fillna(0.5)
    df["buy_volume"]    = df["volume"] * buy_ratio
    df["sell_volume"]   = df["volume"] * (1 - buy_ratio)
    df["volume_delta"]  = df["buy_volume"] - df["sell_volume"]
    df["cum_delta"]     = df["volume_delta"].cumsum()
    df["cum_delta_ema"] = df["cum_delta"].ewm(span=20, adjust=False).mean()
    return df


def compute_volume_spike(df: pd.DataFrame, period: int = 20, threshold: float = 2.0) -> pd.DataFrame:
    df["volume_avg"]   = df["volume"].rolling(period).mean()
    df["volume_ratio"] = df["volume"] / df["volume_avg"].replace(0, np.nan)
    df["volume_spike"] = df["volume_ratio"] >= threshold
    return df


def compute_signal_strength(df: pd.DataFrame, signal_type: str, bar_idx: int) -> dict:
    if bar_idx < 0:
        bar_idx = len(df) + bar_idx
    if bar_idx < 0 or bar_idx >= len(df):
        return _empty_strength()

    bar     = df.iloc[bar_idx]
    is_long = signal_type in ["green_dot", "gold_dot", "bull_div", "bull_div_hidden"]
    score   = 50
    reasons = []
    confluence = 0

    if "obv_trend" in df.columns:
        obv_bull = bool(bar.get("obv_trend", False))
        if is_long and obv_bull:
            score += 10; confluence += 1
            reasons.append("✅ OBV rising — buying pressure confirmed")
        elif not is_long and not obv_bull:
            score += 10; confluence += 1
            reasons.append("✅ OBV falling — selling pressure confirmed")
        elif is_long:
            score -= 8
            reasons.append("⚠️ OBV falling — diverges from buy signal")
        else:
            score -= 8
            reasons.append("⚠️ OBV rising — diverges from sell signal")

    if "cmf" in df.columns:
        cmf = float(bar.get("cmf", 0) or 0)
        if is_long and cmf > 0.1:
            score += 15; confluence += 1
            reasons.append(f"✅ CMF {cmf:+.3f} — institutions buying")
        elif not is_long and cmf < -0.1:
            score += 15; confluence += 1
            reasons.append(f"✅ CMF {cmf:+.3f} — institutions selling")
        elif is_long and cmf < -0.05:
            score -= 10
            reasons.append(f"⚠️ CMF {cmf:+.3f} — institutional selling detected")
        elif not is_long and cmf > 0.05:
            score -= 10
            reasons.append(f"⚠️ CMF {cmf:+.3f} — institutional buying detected")
        else:
            reasons.append(f"➖ CMF {cmf:+.3f} — neutral money flow")

    if "mfi" in df.columns:
        mfi = float(bar.get("mfi", 50) or 50)
        if is_long and mfi < 25:
            score += 15; confluence += 1
            reasons.append(f"✅ MFI {mfi:.0f} — deeply oversold, reversal likely")
        elif not is_long and mfi > 75:
            score += 15; confluence += 1
            reasons.append(f"✅ MFI {mfi:.0f} — deeply overbought, reversal likely")
        elif is_long and mfi < 40:
            score += 5
            reasons.append(f"✅ MFI {mfi:.0f} — oversold territory")
        elif not is_long and mfi > 60:
            score += 5
            reasons.append(f"✅ MFI {mfi:.0f} — overbought territory")
        else:
            reasons.append(f"➖ MFI {mfi:.0f} — neutral zone")

    if "volume_delta" in df.columns:
        delta = float(bar.get("volume_delta", 0) or 0)
        if is_long and delta > 0:
            score += 10; confluence += 1
            reasons.append("✅ Volume delta positive — buyers dominating")
        elif not is_long and delta < 0:
            score += 10; confluence += 1
            reasons.append("✅ Volume delta negative — sellers dominating")
        else:
            reasons.append(f"➖ Volume delta {'positive' if delta > 0 else 'negative'} — mixed pressure")

    if "volume_spike" in df.columns:
        spike     = bool(bar.get("volume_spike", False))
        vol_ratio = float(bar.get("volume_ratio", 1.0) or 1.0)
        if spike:
            score += 10; confluence += 1
            reasons.append(f"✅ Volume spike {vol_ratio:.1f}x average — strong conviction")
        else:
            reasons.append(f"➖ Volume {vol_ratio:.1f}x average — normal activity")

    if signal_type == "gold_dot":
        score += 10
        reasons.append("✅ Gold Dot — extreme oversold, highest priority signal")

    score    = max(0, min(100, score))
    cmf_val  = float(bar.get("cmf", 0) or 0) if "cmf" in df.columns else 0
    obv_bull = bool(bar.get("obv_trend", False)) if "obv_trend" in df.columns else True

    if cmf_val > 0.05 and obv_bull:
        mf_bias = "BULLISH"
    elif cmf_val < -0.05 and not obv_bull:
        mf_bias = "BEARISH"
    else:
        mf_bias = "NEUTRAL"

    strength = "STRONG" if score >= 75 else "MODERATE" if score >= 55 else "WEAK"

    return {
        "strength":   strength,
        "score":      score,
        "reasons":    reasons,
        "mf_bias":    mf_bias,
        "confluence": confluence,
        "cmf":        round(cmf_val, 4),
        "mfi":        round(float(bar.get("mfi", 50) or 50), 1),
        "obv_trend":  "Rising ↑" if obv_bull else "Falling ↓",
        "vol_ratio":  round(float(bar.get("volume_ratio", 1.0) or 1.0), 2),
        "vol_spike":  bool(bar.get("volume_spike", False)) if "volume_spike" in df.columns else False,
    }


def _empty_strength() -> dict:
    return {
        "strength": "UNKNOWN", "score": 50, "reasons": [],
        "mf_bias": "NEUTRAL",  "confluence": 0,
        "cmf": 0, "mfi": 50,   "obv_trend": "Unknown",
        "vol_ratio": 1.0,      "vol_spike": False,
    }


def compute_money_flow(df: pd.DataFrame) -> pd.DataFrame:
    df = compute_obv(df)
    df = compute_cmf(df)
    df = compute_mfi(df)
    df = compute_volume_delta(df)
    df = compute_volume_spike(df)
    return df


def get_money_flow_summary(df: pd.DataFrame, bar_idx: int = -2) -> dict:
    idx = bar_idx if bar_idx >= 0 else len(df) + bar_idx
    if idx < 0 or idx >= len(df):
        return _empty_strength()

    bar      = df.iloc[idx]
    cmf      = round(float(bar.get("cmf", 0) or 0), 4)
    mfi      = round(float(bar.get("mfi", 50) or 50), 1)
    obv_bull = bool(bar.get("obv_trend", False))
    delta    = round(float(bar.get("volume_delta", 0) or 0), 2)
    vol_rat  = round(float(bar.get("volume_ratio", 1.0) or 1.0), 2)
    spike    = bool(bar.get("volume_spike", False))

    bias = "BULLISH" if (cmf > 0.05 and obv_bull) else "BEARISH" if (cmf < -0.05 and not obv_bull) else "NEUTRAL"

    return {
        "cmf":          cmf,
        "mfi":          mfi,
        "obv_trend":    "Rising ↑" if obv_bull else "Falling ↓",
        "volume_delta": delta,
        "vol_ratio":    vol_rat,
        "vol_spike":    spike,
        "mf_bias":      bias,
    }
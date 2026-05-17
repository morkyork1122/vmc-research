"""
VMC Cipher B (VuManChu Cipher B) — Full Python Implementation
Computes: WaveTrend, RSI+MFI, Signal Dots, Regular & Hidden Divergences
"""

import pandas as pd
import numpy as np


# ─── Moving Average Helpers ───────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


# ─── WaveTrend Oscillator ─────────────────────────────────────────────────────

def compute_wavetrend(df: pd.DataFrame, chlen: int = 10, avg: int = 21, smalen: int = 4) -> pd.DataFrame:
    """
    Core WaveTrend oscillator.
    Formula (from LazyBear's original Pine Script):
      hlc3  = (H + L + C) / 3
      esa   = EMA(hlc3, chlen)
      d     = EMA(|hlc3 - esa|, chlen)
      ci    = (hlc3 - esa) / (0.015 * d)
      tci   = EMA(ci, avg)
      wt1   = tci
      wt2   = SMA(wt1, smalen)
    """
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    esa = ema(hlc3, chlen)
    d = ema((hlc3 - esa).abs(), chlen)
    ci = (hlc3 - esa) / (0.015 * d.replace(0, np.nan))
    tci = ema(ci.fillna(0), avg)

    df["wt1"] = tci
    df["wt2"] = sma(df["wt1"], smalen)
    df["wt_diff"] = df["wt1"] - df["wt2"]
    return df


# ─── RSI + MFI ────────────────────────────────────────────────────────────────

def compute_rsimfi(df: pd.DataFrame, period: int = 60, multiplier: float = 150) -> pd.DataFrame:
    """
    RSI+MFI composite (VMC's money flow component).
    Uses the candle body direction weighted by wick size.
    """
    hl_range = (df["high"] - df["low"]).replace(0, np.nan)
    raw = ((df["close"] - df["open"]) / hl_range) * multiplier
    df["rsimfi"] = sma(raw.fillna(0), period)
    return df


# ─── Signal Crosses & Dots ────────────────────────────────────────────────────

def compute_signals(df: pd.DataFrame, overbought: float = 53, oversold: float = -53) -> pd.DataFrame:
    """
    Detect all VMC Cipher B signal dots.
      Green Dot  : WT cross up  AND wt2 < oversold
      Red Dot    : WT cross down AND wt2 > overbought
      Gold Dot   : WT cross up  AND wt2 < -80  (strong buy)
    """
    wt1, wt2 = df["wt1"], df["wt2"]

    cross_up   = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))

    df["wt_cross_up"]   = cross_up
    df["wt_cross_down"] = cross_down
    df["green_dot"]     = cross_up   & (wt2 < oversold)
    df["red_dot"]       = cross_down & (wt2 > overbought)
    df["gold_dot"]      = cross_up   & (wt2 < -80)
    df["overbought"]    = wt2 >= overbought
    df["oversold"]      = wt2 <= oversold
    return df


# ─── Divergence Detection ─────────────────────────────────────────────────────

def _pivot_high(series: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    """Returns True at bars that are a local pivot high."""
    result = pd.Series(False, index=series.index)
    vals = series.values
    for i in range(left, len(vals) - right):
        if all(vals[i] >= vals[i - j] for j in range(1, left + 1)) and \
           all(vals[i] >= vals[i + j] for j in range(1, right + 1)):
            result.iloc[i] = True
    return result


def _pivot_low(series: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    """Returns True at bars that are a local pivot low."""
    result = pd.Series(False, index=series.index)
    vals = series.values
    for i in range(left, len(vals) - right):
        if all(vals[i] <= vals[i - j] for j in range(1, left + 1)) and \
           all(vals[i] <= vals[i + j] for j in range(1, right + 1)):
            result.iloc[i] = True
    return result


def compute_divergences(df: pd.DataFrame, lookback: int = 30) -> pd.DataFrame:
    """
    Detect regular and hidden divergences between price and WT1.

    Regular Bullish  (bull_div)        : price lower low,  WT higher low  → reversal up
    Regular Bearish  (bear_div)        : price higher high, WT lower high → reversal down
    Hidden  Bullish  (bull_div_hidden) : price higher low,  WT lower low  → trend continuation up
    Hidden  Bearish  (bear_div_hidden) : price lower high,  WT higher high→ trend continuation down
    """
    df["fractal_top"] = _pivot_high(df["wt1"])
    df["fractal_bot"] = _pivot_low(df["wt1"])

    for col in ["bull_div", "bear_div", "bull_div_hidden", "bear_div_hidden"]:
        df[col] = False

    idxs = df.index.tolist()

    for i in range(lookback + 4, len(df)):
        window_start = max(0, i - lookback - 4)
        window_end   = i - 2  # must be confirmed (2 bars ago)

        # ── Bullish (look at fractal bottoms) ──────────────────────
        bot_mask = df["fractal_bot"].iloc[window_start:window_end]
        bot_positions = [df.index.get_loc(ix) for ix in bot_mask[bot_mask].index]

        if len(bot_positions) >= 2:
            p_idx = bot_positions[-2]
            c_idx = bot_positions[-1]
            low_curr  = df["low"].iloc[c_idx]
            low_prev  = df["low"].iloc[p_idx]
            wt_curr   = df["wt1"].iloc[c_idx]
            wt_prev   = df["wt1"].iloc[p_idx]

            if low_curr < low_prev and wt_curr > wt_prev:   # regular bullish
                df.at[idxs[c_idx], "bull_div"] = True
            if low_curr > low_prev and wt_curr < wt_prev:   # hidden bullish
                df.at[idxs[c_idx], "bull_div_hidden"] = True

        # ── Bearish (look at fractal tops) ─────────────────────────
        top_mask = df["fractal_top"].iloc[window_start:window_end]
        top_positions = [df.index.get_loc(ix) for ix in top_mask[top_mask].index]

        if len(top_positions) >= 2:
            p_idx = top_positions[-2]
            c_idx = top_positions[-1]
            high_curr = df["high"].iloc[c_idx]
            high_prev = df["high"].iloc[p_idx]
            wt_curr   = df["wt1"].iloc[c_idx]
            wt_prev   = df["wt1"].iloc[p_idx]

            if high_curr > high_prev and wt_curr < wt_prev: # regular bearish
                df.at[idxs[c_idx], "bear_div"] = True
            if high_curr < high_prev and wt_curr > wt_prev: # hidden bearish
                df.at[idxs[c_idx], "bear_div_hidden"] = True

    return df


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def compute_all(
    df: pd.DataFrame,
    chlen: int = 10,
    avg: int = 21,
    smalen: int = 4,
    overbought: float = 53,
    oversold: float = -53,
    mfi_period: int = 60,
    div_lookback: int = 30,
) -> pd.DataFrame:
    """
    Run the full VMC Cipher B computation pipeline.
    Input df must have columns: open, high, low, close, volume, timestamp
    Returns df with all indicator columns added.
    """
    df = df.copy()
    df = compute_wavetrend(df, chlen=chlen, avg=avg, smalen=smalen)
    df = compute_rsimfi(df, period=mfi_period)
    df = compute_signals(df, overbought=overbought, oversold=oversold)
    df = compute_divergences(df, lookback=div_lookback)
    return df


def get_latest_signals(df: pd.DataFrame, n: int = 50) -> dict:
    """
    Extract the most recent n bars of signals for the API response.
    Returns a concise dict for JSON serialisation.
    """
    recent = df.tail(n).copy()
    recent["timestamp"] = recent["timestamp"].astype(str)

    signal_cols = [
        "timestamp", "open", "high", "low", "close", "volume",
        "wt1", "wt2", "rsimfi",
        "green_dot", "red_dot", "gold_dot",
        "bull_div", "bear_div", "bull_div_hidden", "bear_div_hidden",
        "overbought", "oversold",
    ]

    return recent[signal_cols].where(pd.notnull(recent[signal_cols]), None).to_dict(orient="records")
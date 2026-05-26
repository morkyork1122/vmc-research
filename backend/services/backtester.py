import math
import pandas as pd
import numpy as np
from dataclasses import dataclass


# ─── NaN/Inf Sanitizer ────────────────────────────────────────────────────────

def _safe(val, default=0):
    try:
        if val is None:
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


# ─── Trade Dataclass ──────────────────────────────────────────────────────────

@dataclass
class Trade:
    direction:       str
    entry_bar:       int
    entry_price:     float
    stop_loss:       float
    take_profit:     float
    exit_bar:        int   = -1
    exit_price:      float = 0.0
    result:          str   = "open"
    pnl_pct:         float = 0.0
    signal_type:     str   = ""
    wt1_at_entry:    float = 0.0
    wt2_at_entry:    float = 0.0
    rsimfi_at_entry: float = 0.0


# ─── Backtest Config ──────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    use_green_dot:       bool  = True
    use_red_dot:         bool  = True
    use_gold_dot:        bool  = True
    use_bull_div:        bool  = True
    use_bear_div:        bool  = True
    use_bull_div_hidden: bool  = False
    use_bear_div_hidden: bool  = False
    stop_loss_pct:       float = 0.02
    risk_reward_ratio:   float = 2.0
    atr_multiplier:      float = 1.5
    use_atr:             bool  = True
    atr_period:          int   = 14
    exit_on_opposite_signal: bool = True
    max_bars_in_trade:   int   = 50


# ─── ATR ──────────────────────────────────────────────────────────────────────

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ─── Backtester ───────────────────────────────────────────────────────────────

class VMCBacktester:
    def __init__(self, df: pd.DataFrame, config: BacktestConfig = None):
        self.df  = df.copy().reset_index(drop=True)
        self.cfg = config or BacktestConfig()
        self.trades = []
        if self.cfg.use_atr:
            self.df["atr"] = compute_atr(self.df, self.cfg.atr_period)

    def _get_sl_tp(self, idx: int, direction: str, entry: float):
        if self.cfg.use_atr:
            atr = self.df["atr"].iloc[idx]
            sl_dist = atr * self.cfg.atr_multiplier if not np.isnan(atr) else entry * self.cfg.stop_loss_pct
        else:
            sl_dist = entry * self.cfg.stop_loss_pct
        tp_dist = sl_dist * self.cfg.risk_reward_ratio
        if direction == "long":
            return entry - sl_dist, entry + tp_dist
        else:
            return entry + sl_dist, entry - tp_dist

    def _collect_signals(self):
        signals = []
        df = self.df
        for i in range(1, len(df)):
            try:
                if self.cfg.use_green_dot and "green_dot" in df.columns and df["green_dot"].iloc[i]:
                    signals.append((i, "long",  "green_dot"))
                if self.cfg.use_gold_dot and "gold_dot" in df.columns and df["gold_dot"].iloc[i]:
                    signals.append((i, "long",  "gold_dot"))
                if self.cfg.use_bull_div and "bull_div" in df.columns and df["bull_div"].iloc[i]:
                    signals.append((i, "long",  "bull_div"))
                if self.cfg.use_bull_div_hidden and "bull_div_hidden" in df.columns and df["bull_div_hidden"].iloc[i]:
                    signals.append((i, "long",  "bull_div_hidden"))
                if self.cfg.use_red_dot and "red_dot" in df.columns and df["red_dot"].iloc[i]:
                    signals.append((i, "short", "red_dot"))
                if self.cfg.use_bear_div and "bear_div" in df.columns and df["bear_div"].iloc[i]:
                    signals.append((i, "short", "bear_div"))
                if self.cfg.use_bear_div_hidden and "bear_div_hidden" in df.columns and df["bear_div_hidden"].iloc[i]:
                    signals.append((i, "short", "bear_div_hidden"))
            except Exception:
                continue
        return signals

    def run(self):
        self.trades = []
        signals = self._collect_signals()
        df = self.df

        for entry_bar, direction, sig_type in signals:
            entry_price = df["close"].iloc[entry_bar]
            sl, tp = self._get_sl_tp(entry_bar, direction, entry_price)

            trade = Trade(
                direction    = direction,
                entry_bar    = entry_bar,
                entry_price  = entry_price,
                stop_loss    = sl,
                take_profit  = tp,
                signal_type  = sig_type,
                wt1_at_entry = float(df["wt1"].iloc[entry_bar]),
                wt2_at_entry = float(df["wt2"].iloc[entry_bar]),
                rsimfi_at_entry = float(df["rsimfi"].iloc[entry_bar])
                    if pd.notna(df["rsimfi"].iloc[entry_bar]) else 0.0,
            )

            for j in range(entry_bar + 1, min(entry_bar + self.cfg.max_bars_in_trade + 1, len(df))):
                bar = df.iloc[j]
                if self.cfg.exit_on_opposite_signal:
                    if direction == "long" and (
                        bar.get("red_dot", False) or bar.get("bear_div", False)
                    ):
                        trade.exit_bar   = j
                        trade.exit_price = float(bar["close"])
                        break
                    if direction == "short" and (
                        bar.get("green_dot", False) or bar.get("bull_div", False)
                    ):
                        trade.exit_bar   = j
                        trade.exit_price = float(bar["close"])
                        break
                if direction == "long":
                    if bar["low"]  <= sl: trade.exit_bar = j; trade.exit_price = sl; break
                    if bar["high"] >= tp: trade.exit_bar = j; trade.exit_price = tp; break
                else:
                    if bar["high"] >= sl: trade.exit_bar = j; trade.exit_price = sl; break
                    if bar["low"]  <= tp: trade.exit_bar = j; trade.exit_price = tp; break
            else:
                trade.exit_bar   = min(entry_bar + self.cfg.max_bars_in_trade, len(df) - 1)
                trade.exit_price = float(df["close"].iloc[trade.exit_bar])

            if direction == "long":
                trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
            else:
                trade.pnl_pct = (trade.entry_price - trade.exit_price) / trade.entry_price * 100

            trade.result = "win" if trade.pnl_pct > 0 else "loss"
            self.trades.append(trade)

        return BacktestResult(self.trades, df)


# ─── Backtest Result ──────────────────────────────────────────────────────────

class BacktestResult:
    def __init__(self, trades, df):
        self.trades = trades
        self.df     = df

    def summary(self):
        if not self.trades:
            return {"error": "No signals found in the data range."}

        wins   = [t for t in self.trades if t.result == "win"]
        losses = [t for t in self.trades if t.result == "loss"]
        total  = len(self.trades)

        win_rate = _safe(round(len(wins) / total * 100, 1)) if total else 0
        avg_win  = _safe(round(float(np.mean([t.pnl_pct for t in wins])),   2)) if wins   else 0
        avg_loss = _safe(round(float(np.mean([t.pnl_pct for t in losses])), 2)) if losses else 0
        avg_rr   = _safe(round(abs(avg_win / avg_loss), 2))                      if avg_loss != 0 else 0

        pnls         = [t.pnl_pct for t in self.trades]
        cumulative   = np.cumsum(pnls)
        peak         = np.maximum.accumulate(cumulative)
        max_drawdown = _safe(round(float(np.max(peak - cumulative)), 2)) if len(pnls) else 0

        loss_sum      = sum(t.pnl_pct for t in losses)
        win_sum       = sum(t.pnl_pct for t in wins)
        profit_factor = _safe(round(win_sum / abs(loss_sum), 2)) \
            if losses and loss_sum != 0 else None

        by_signal = {}
        for sig in [
            "green_dot", "red_dot", "gold_dot",
            "bull_div", "bear_div", "bull_div_hidden", "bear_div_hidden",
        ]:
            st = [t for t in self.trades if t.signal_type == sig]
            if not st:
                continue
            sw = [t for t in st if t.result == "win"]
            by_signal[sig] = {
                "total":    len(st),
                "win_rate": _safe(round(len(sw) / len(st) * 100, 1)),
                "avg_pnl":  _safe(round(float(np.mean([t.pnl_pct for t in st])), 2)),
            }

        return {
            "total_trades":  total,
            "win_count":     len(wins),
            "loss_count":    len(losses),
            "win_rate":      win_rate,
            "avg_win_pct":   avg_win,
            "avg_loss_pct":  avg_loss,
            "avg_rr":        avg_rr,
            "profit_factor": profit_factor,
            "max_drawdown":  max_drawdown,
            "total_pnl":     _safe(round(sum(pnls), 2)),
            "by_signal":     by_signal,
            "avg_wt2_at_winning_entry": _safe(round(float(np.mean(
                [t.wt2_at_entry for t in wins])), 2)) if wins else 0,
            "avg_wt2_at_losing_entry":  _safe(round(float(np.mean(
                [t.wt2_at_entry for t in losses])), 2)) if losses else 0,
        }

    def recent_trades(self, n: int = 10):
        recent = list(reversed(self.trades[-n:]))
        result = []
        for t in recent:
            result.append({
                "signal_type":     t.signal_type,
                "direction":       t.direction,
                "entry_price":     _safe(round(t.entry_price, 4)),
                "exit_price":      _safe(round(t.exit_price,  4)),
                "stop_loss":       _safe(round(t.stop_loss,   4)),
                "take_profit":     _safe(round(t.take_profit, 4)),
                "pnl_pct":         _safe(round(t.pnl_pct,     2)),
                "result":          t.result,
                "entry_time":      str(self.df["timestamp"].iloc[t.entry_bar])
                    if t.entry_bar < len(self.df) else "",
                "exit_time":       str(self.df["timestamp"].iloc[t.exit_bar])
                    if t.exit_bar  < len(self.df) else "",
                "wt2_at_entry":    _safe(round(t.wt2_at_entry,    2)),
                "rsimfi_at_entry": _safe(round(t.rsimfi_at_entry, 2)),
            })
        return result
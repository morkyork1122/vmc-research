"""
Signal Monitor — VMC + Money Flow + MTF Confirmation.
Only fires Telegram alerts when HTF agrees (or is neutral).
AGAINST signals are logged but suppressed.
"""

import asyncio
import json
from pathlib import Path
import pandas as pd

from indicators.vmc_cipher_b import compute_all
from indicators.money_flow import compute_money_flow, compute_signal_strength
from services.data_fetcher import fetch_ohlcv, validate_symbol
from services.mtf_analyzer import analyze_htf, combined_score
from services.notifier import send_alert, send_startup_message

STATE_FILE = Path("monitor_state.json")

POLL_INTERVALS = {
    "1m": 30, "5m": 90, "15m": 180, "30m": 300,
    "1H": 600, "4H": 1800, "1D": 3600, "1W": 7200,
}

ACTIVE_SIGNALS = [
    "green_dot", "red_dot", "gold_dot",
    "bull_div",  "bear_div", "bull_div_hidden", "bear_div_hidden",
]

# Minimum money flow score to fire an alert (0 = disabled)
MIN_MF_SCORE = 0

# If True, suppress alerts when HTF says AGAINST
FILTER_AGAINST_HTF = True


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"[Monitor] State save failed: {e}")


class PairMonitor:
    def __init__(self, symbol: str, timeframe: str, signals: list = None):
        self.symbol    = validate_symbol(symbol)
        self.timeframe = timeframe
        self.signals   = signals or ACTIVE_SIGNALS
        self.interval  = POLL_INTERVALS.get(timeframe, 600)
        self.state     = _load_state()
        self._running  = True

    def _state_key(self, signal_type: str) -> str:
        return f"{self.symbol}|{self.timeframe}|{signal_type}"

    def _already_alerted(self, signal_type: str, timestamp: str) -> bool:
        return self.state.get(self._state_key(signal_type)) == timestamp

    def _mark_alerted(self, signal_type: str, timestamp: str) -> None:
        self.state[self._state_key(signal_type)] = timestamp
        _save_state(self.state)

    async def _check_once(self) -> None:
        # ── Fetch + compute ───────────────────────────────────────────────────
        try:
            df = await fetch_ohlcv(self.symbol, self.timeframe, limit=150)
        except Exception as e:
            print(f"[Monitor] {self.symbol} {self.timeframe} — fetch error: {e}")
            return

        try:
            df = compute_all(df)
            df = compute_money_flow(df)
        except Exception as e:
            print(f"[Monitor] {self.symbol} {self.timeframe} — compute error: {e}")
            return

        if len(df) < 3:
            return

        closed_idx    = len(df) - 2
        latest_closed = df.iloc[closed_idx]

        bar = {
            "timestamp": str(latest_closed["timestamp"]),
            "open":      float(latest_closed["open"]),
            "high":      float(latest_closed["high"]),
            "low":       float(latest_closed["low"]),
            "close":     float(latest_closed["close"]),
            "volume":    float(latest_closed["volume"]),
            "wt1":       float(latest_closed["wt1"]),
            "wt2":       float(latest_closed["wt2"]),
            "rsimfi":    float(latest_closed["rsimfi"]) if pd.notna(latest_closed["rsimfi"]) else 0.0,
        }
        ts = bar["timestamp"]

        for sig in self.signals:
            if sig not in df.columns:
                continue
            if not bool(latest_closed[sig]):
                continue
            if self._already_alerted(sig, ts):
                continue

            # ── Money Flow strength ───────────────────────────────────────────
            mf = compute_signal_strength(df, sig, closed_idx)

            # Skip if below minimum score threshold
            if MIN_MF_SCORE > 0 and mf["score"] < MIN_MF_SCORE:
                print(f"[Monitor] Filtered (low MF score {mf['score']}) — {self.symbol} {sig}")
                self._mark_alerted(sig, ts)
                continue

            # ── MTF Confirmation ──────────────────────────────────────────────
            mtf = await analyze_htf(self.symbol, self.timeframe, sig)

            # Suppress if HTF is against and filter is enabled
            if FILTER_AGAINST_HTF and not mtf["should_trade"]:
                print(
                    f"[Monitor] Suppressed (HTF AGAINST) — {self.symbol} {self.timeframe} "
                    f"{sig} | {mtf['filter_reason']}"
                )
                self._mark_alerted(sig, ts)
                continue

            # ── Overall grade ─────────────────────────────────────────────────
            grade_info = combined_score(mf["score"], mtf["htf_score"])

            print(
                f"[Monitor] 🔔 {sig} | {self.symbol} {self.timeframe} | "
                f"price={bar['close']:.2f} | "
                f"MF={mf['strength']} | "
                f"HTF={mtf['htf_confirmation']} ({mtf['htf_timeframe']}) | "
                f"Grade={grade_info['grade']}"
            )

            await send_alert(self.symbol, self.timeframe, sig, bar, mf, mtf)
            self._mark_alerted(sig, ts)

    async def run(self) -> None:
        print(f"[Monitor] Started {self.symbol} {self.timeframe} (every {self.interval}s)")
        while self._running:
            await self._check_once()
            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False


class MonitorManager:
    def __init__(self):
        self._monitors = []
        self._tasks    = []

    def configure(self, pairs: list) -> None:
        self._monitors = [
            PairMonitor(
                symbol    = p["symbol"],
                timeframe = p["timeframe"],
                signals   = p.get("signals", ACTIVE_SIGNALS),
            )
            for p in pairs
        ]

    async def start(self) -> None:
        if not self._monitors:
            print("[Monitor] No pairs configured")
            return
        pairs_info = [{"symbol": m.symbol, "timeframe": m.timeframe} for m in self._monitors]
        await send_startup_message(pairs_info)
        self._tasks = [
            asyncio.create_task(m.run(), name=f"monitor-{m.symbol}-{m.timeframe}")
            for m in self._monitors
        ]
        print(f"[Monitor] Started {len(self._tasks)} monitor task(s)")

    async def stop(self) -> None:
        for m in self._monitors:
            m.stop()
        for t in self._tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        print("[Monitor] Stopped")


monitor_manager = MonitorManager()
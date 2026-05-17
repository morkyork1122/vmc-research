"""
TradingView Webhook Receiver
Receives POST requests from TradingView alerts and forwards to Telegram.

TradingView sends the alert message as plain text (the JSON string you
defined in the alertcondition message field).

Endpoint: POST /api/webhook/tradingview
Optional secret header for security: X-Webhook-Secret
"""

import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

from services.notifier import send_alert, SIGNAL_LABEL, SIGNAL_EMOJI


router = APIRouter(prefix="/api/webhook", tags=["webhook"])


def _verify_secret(secret: Optional[str]) -> None:
    """Optionally verify a shared secret to reject unauthorised requests."""
    expected = os.getenv("WEBHOOK_SECRET", "")
    if expected and secret != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post("/tradingview")
async def tradingview_webhook(
    request: Request,
    x_webhook_secret: Optional[str] = Header(None),
):
    """
    Receives TradingView alert webhooks and sends Telegram notifications.

    TradingView sends the alert message as raw text in the request body.
    Our Pine Script formats it as JSON, so we parse it here.

    Expected payload (from Pine Script alertcondition message):
    {
        "signal":    "green_dot",
        "symbol":    "BTCUSDT",
        "timeframe": "240",
        "price":     45123.45,
        "wt1":       -60.2,
        "wt2":       -62.1,
        "rsimfi":    -8.4,
        "direction": "long",
        "bar_time":  "2024-01-01T04:00:00Z"
    }
    """
    _verify_secret(x_webhook_secret)

    # Read raw body — TradingView sends plain text, not application/json
    body = await request.body()
    raw  = body.decode("utf-8").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {raw[:200]}")

    # ── Extract fields ────────────────────────────────────────────────────────
    signal_type = data.get("signal", "unknown")
    symbol      = _normalise_symbol(data.get("symbol", "UNKNOWN"))
    timeframe   = _normalise_timeframe(data.get("timeframe", "?"))
    price       = float(data.get("price", 0))
    wt1         = float(data.get("wt1", 0))
    wt2         = float(data.get("wt2", 0))
    rsimfi      = float(data.get("rsimfi", 0))
    bar_time    = data.get("bar_time", "")

    if signal_type not in SIGNAL_LABEL:
        raise HTTPException(status_code=400, detail=f"Unknown signal type: {signal_type}")

    # ── Log the incoming signal ───────────────────────────────────────────────
    emoji = SIGNAL_EMOJI.get(signal_type, "⚡")
    print(f"[Webhook] {emoji} {signal_type} | {symbol} {timeframe} | price={price} | wt2={wt2}")

    # ── Build bar dict for notifier ───────────────────────────────────────────
    bar = {
        "timestamp": bar_time,
        "close":     price,
        "wt1":       wt1,
        "wt2":       wt2,
        "rsimfi":    rsimfi,
    }

    # ── Send Telegram alert ───────────────────────────────────────────────────
    sent = await send_alert(symbol, timeframe, signal_type, bar)

    return {
        "status":      "ok" if sent else "telegram_failed",
        "signal":      signal_type,
        "symbol":      symbol,
        "timeframe":   timeframe,
        "price":       price,
        "alert_sent":  sent,
    }


@router.get("/tradingview/test")
async def test_webhook():
    """Quick health check — confirms the webhook endpoint is reachable."""
    return {"status": "ok", "message": "Webhook endpoint is live. Point TradingView here."}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _normalise_symbol(tv_symbol: str) -> str:
    """
    TradingView sends symbols like 'BINANCE:BTCUSDT' or 'BTCUSDT'.
    Normalise to 'BTC/USDT'.
    """
    # Strip exchange prefix (e.g. 'BINANCE:BTCUSDT' → 'BTCUSDT')
    if ":" in tv_symbol:
        tv_symbol = tv_symbol.split(":")[1]

    tv_symbol = tv_symbol.upper().strip()

    # Already has slash
    if "/" in tv_symbol:
        return tv_symbol

    # Try splitting known quote currencies
    for quote in ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"]:
        if tv_symbol.endswith(quote):
            base = tv_symbol[: -len(quote)]
            return f"{base}/{quote}"

    return tv_symbol


def _normalise_timeframe(tv_tf: str) -> str:
    """
    TradingView sends timeframes as numbers: '60' = 1H, '240' = 4H, 'D' = 1D.
    Map to our display format.
    """
    mapping = {
        "1": "1m",  "3": "3m",  "5": "5m",  "15": "15m",
        "30": "30m", "45": "45m", "60": "1H", "120": "2H",
        "180": "3H", "240": "4H", "360": "6H", "480": "8H",
        "720": "12H", "D": "1D", "1D": "1D", "W": "1W", "1W": "1W",
        "M": "1M",
    }
    return mapping.get(str(tv_tf).upper(), tv_tf)
"""
VMC Cipher B Research API v5
VMC + Money Flow + MTF + AI Chat + Auto-Analysis + 24/7 Monitor
"""

from dotenv import load_dotenv
load_dotenv()

import math
import json
import pandas as pd
import os

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from monitor_config import MONITORED_PAIRS, DEFAULT_SIGNALS
from models import ResearchRequest, ResearchResponse
from indicators.vmc_cipher_b import compute_all, get_latest_signals
from indicators.money_flow import (
    compute_money_flow, get_money_flow_summary, compute_signal_strength
)
from services.data_fetcher import fetch_ohlcv, validate_symbol
from services.backtester import VMCBacktester, BacktestConfig
from services.ai_analyst import generate_research_report
from services.ai_chat import chat, generate_auto_analysis
from services.mtf_analyzer import analyze_htf, combined_score, get_higher_timeframe
from services.monitor import monitor_manager
from services.notifier import send_alert
from services.webhook_receiver import router as webhook_router


# ─── NaN Sanitizer ────────────────────────────────────────────────────────────

def sanitize(obj):
    """Recursively replace NaN/Infinity with None in any structure."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    return obj


class SanitizedJSONResponse(Response):
    """Custom response class that strips NaN/Inf before serialising."""
    media_type = "application/json"

    def render(self, content) -> bytes:
        return json.dumps(
            sanitize(content),
            allow_nan=False,
            default=str,
        ).encode("utf-8")


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[App] Starting VMC Research API v5")
    for pair in MONITORED_PAIRS:
        if "signals" not in pair:
            pair["signals"] = DEFAULT_SIGNALS
    monitor_manager.configure(MONITORED_PAIRS)
    await monitor_manager.start()
    yield
    print("[App] Shutting down")
    await monitor_manager.stop()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="VMC Cipher B Research API",
    version="5.0.0",
    lifespan=lifespan,
    default_response_class=SanitizedJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)


# ─── Global Error Handler (returns CORS headers even on crash) ────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


# ─── Chat Model ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message:        str
    symbol:         str            = "BTC/USDT"
    timeframe:      str            = "4H"
    signal_type:    Optional[str]  = None
    backtest_stats: Optional[dict] = None
    money_flow:     Optional[dict] = None
    mtf:            Optional[dict] = None
    latest_bar:     Optional[dict] = None
    history:        Optional[list] = None


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    monitors = [
        {"symbol": m.symbol, "timeframe": m.timeframe, "interval_s": m.interval}
        for m in monitor_manager._monitors
    ]
    return {"status": "ok", "version": "5.0.0", "monitors": monitors}


# ─── AI Chat ─────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def ai_chat(req: ChatMessage):
    try:
        response = await chat(
            message        = req.message,
            symbol         = req.symbol,
            timeframe      = req.timeframe,
            signal_type    = req.signal_type,
            backtest_stats = req.backtest_stats,
            money_flow     = req.money_flow,
            mtf            = req.mtf,
            latest_bar     = req.latest_bar,
            history        = req.history or [],
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Live Scan ────────────────────────────────────────────────────────────────

@app.get("/api/live-scan")
async def live_scan(
    symbol:    str = Query("BTC/USDT"),
    timeframe: str = Query("4H"),
    signal:    str = Query("green_dot"),
):
    symbol = validate_symbol(symbol)

    try:
        df = await fetch_ohlcv(symbol, timeframe, limit=150)
        df = compute_all(df)
        df = compute_money_flow(df)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}")

    closed_idx    = len(df) - 2
    latest_closed = df.iloc[closed_idx]

    bar = {
        "timestamp": str(latest_closed["timestamp"]),
        "close":     round(float(latest_closed["close"]), 4),
        "wt1":       round(float(latest_closed["wt1"]),   2),
        "wt2":       round(float(latest_closed["wt2"]),   2),
        "rsimfi":    round(float(latest_closed["rsimfi"])
                     if pd.notna(latest_closed["rsimfi"]) else 0.0, 2),
    }

    signal_types   = ["green_dot","red_dot","gold_dot","bull_div","bear_div","bull_div_hidden","bear_div_hidden"]
    active_signals = [s for s in signal_types if bool(latest_closed.get(s, False))]

    mf = compute_signal_strength(df, signal, closed_idx)

    try:
        mtf = await analyze_htf(symbol, timeframe, signal)
    except Exception:
        mtf = None

    analysis = ""
    if mtf:
        try:
            analysis = await generate_auto_analysis(
                symbol=symbol, timeframe=timeframe,
                signal_type=signal, bar=bar, mf=mf, mtf=mtf or {},
            )
        except Exception:
            pass

    grade_info = combined_score(mf["score"], mtf["htf_score"] if mtf else 50)

    return {
        "symbol":         symbol,
        "timeframe":      timeframe,
        "signal":         signal,
        "timestamp":      bar["timestamp"],
        "close":          bar["close"],
        "wt1":            bar["wt1"],
        "wt2":            bar["wt2"],
        "rsimfi":         bar["rsimfi"],
        "active_signals": active_signals,
        "money_flow":     mf,
        "mtf":            mtf,
        "overall_score":  grade_info["overall_score"],
        "grade":          grade_info["grade"],
        "ai_analysis":    analysis,
    }


# ─── Money Flow ───────────────────────────────────────────────────────────────

@app.get("/api/money-flow")
async def get_money_flow(
    symbol:    str = Query("BTC/USDT"),
    timeframe: str = Query("4H"),
    signal:    str = Query("green_dot"),
):
    symbol = validate_symbol(symbol)
    try:
        df = await fetch_ohlcv(symbol, timeframe, limit=150)
        df = compute_all(df)
        df = compute_money_flow(df)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    closed_idx = len(df) - 2
    summary    = get_money_flow_summary(df, bar_idx=closed_idx)
    strength   = compute_signal_strength(df, signal, closed_idx)
    bar        = df.iloc[closed_idx]

    return {
        "symbol":    symbol,
        "timeframe": timeframe,
        "signal":    signal,
        "timestamp": str(bar["timestamp"]),
        "close":     round(float(bar["close"]), 4),
        **summary,
        **strength,
    }


# ─── MTF ─────────────────────────────────────────────────────────────────────

@app.get("/api/mtf")
async def get_mtf(
    symbol:    str = Query("BTC/USDT"),
    timeframe: str = Query("4H"),
    signal:    str = Query("green_dot"),
):
    symbol = validate_symbol(symbol)

    try:
        df_primary = await fetch_ohlcv(symbol, timeframe, limit=150)
        df_primary = compute_all(df_primary)
        df_primary = compute_money_flow(df_primary)
        mf = compute_signal_strength(df_primary, signal, len(df_primary) - 2)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Primary TF failed: {e}")

    try:
        mtf = await analyze_htf(symbol, timeframe, signal)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HTF analysis failed: {e}")

    grade_info = combined_score(mf["score"], mtf["htf_score"])

    return {
        "symbol":        symbol,
        "primary_tf":    timeframe,
        "htf":           get_higher_timeframe(timeframe),
        "signal":        signal,
        "mf_score":      mf["score"],
        "mf_strength":   mf["strength"],
        "mf_bias":       mf["mf_bias"],
        "mf_confluence": mf["confluence"],
        **mtf,
        "overall_score": grade_info["overall_score"],
        "grade":         grade_info["grade"],
    }


# ─── Monitor Control ──────────────────────────────────────────────────────────

@app.get("/api/monitor/status")
async def monitor_status():
    import json as _json
    from pathlib import Path
    state_file = Path("monitor_state.json")
    state = {}
    if state_file.exists():
        try:
            state = _json.loads(state_file.read_text())
        except Exception:
            pass

    monitors = []
    for m in monitor_manager._monitors:
        last_signals = {
            k.split("|")[2]: v for k, v in state.items()
            if k.startswith(f"{m.symbol}|{m.timeframe}|")
        }
        monitors.append({
            "symbol":       m.symbol,
            "timeframe":    m.timeframe,
            "signals":      m.signals,
            "poll_every_s": m.interval,
            "last_alerts":  last_signals,
        })
    return {"active_monitors": monitors, "total": len(monitors)}


@app.post("/api/monitor/test-alert")
async def test_alert(symbol: str = "BTC/USDT", timeframe: str = "4H"):
    fake_bar = {
        "timestamp": "2024-01-01 00:00:00+00:00",
        "close": 45000.0, "wt1": -58.3, "wt2": -61.2, "rsimfi": -12.5,
    }
    fake_mf = {
        "strength": "STRONG", "score": 82, "mf_bias": "BULLISH",
        "confluence": 4, "cmf": 0.18, "mfi": 22.0,
        "obv_trend": "Rising ↑", "vol_ratio": 2.4, "vol_spike": True,
        "reasons": [
            "✅ CMF +0.180 — institutions buying",
            "✅ MFI 22 — deeply oversold",
        ],
    }
    fake_mtf = {
        "htf_timeframe": "1D", "htf_label": "Daily",
        "htf_confirmation": "CONFIRMED", "htf_score": 78,
        "htf_trend": "BULLISH", "htf_wt1": 12.3, "htf_wt2": -5.4,
        "htf_cmf": 0.12, "htf_mfi": 38.0, "htf_obv_trend": "Rising ↑",
        "htf_reasons": ["✅ Daily WT bullish — WT1 above WT2"],
        "should_trade": True, "filter_reason": None,
    }
    fake_analysis = (
        "This Green Dot signal on BTC/USDT 4H shows strong confluence across all layers. "
        "WT2 at -61 indicates deeply oversold conditions while the Daily confirms bullish momentum. "
        "Volume running at 2.4x average suggests institutional participation. "
        "All five money flow indicators align bullishly. Grade: A — Excellent."
    )
    ok = await send_alert(symbol, timeframe, "green_dot", fake_bar, fake_mf, fake_mtf, fake_analysis)
    return {
        "status":  "sent" if ok else "failed",
        "message": "Check your Telegram" if ok else "Check .env credentials",
    }


@app.post("/api/monitor/check-now")
async def check_now(symbol: str = "BTC/USDT", timeframe: str = "4H"):
    symbol = validate_symbol(symbol)
    try:
        df = await fetch_ohlcv(symbol, timeframe, limit=150)
        df = compute_all(df)
        df = compute_money_flow(df)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    latest_closed = df.iloc[-2]
    signal_types  = [
        "green_dot", "red_dot", "gold_dot",
        "bull_div",  "bear_div", "bull_div_hidden", "bear_div_hidden",
    ]
    active = [s for s in signal_types if bool(latest_closed.get(s, False))]
    mf     = get_money_flow_summary(df, bar_idx=-2)

    return {
        "symbol":         symbol,
        "timeframe":      timeframe,
        "timestamp":      str(latest_closed["timestamp"]),
        "close":          float(latest_closed["close"]),
        "wt1":            round(float(latest_closed["wt1"]), 2),
        "wt2":            round(float(latest_closed["wt2"]), 2),
        "active_signals": active,
        "money_flow":     mf,
        "message":        f"{len(active)} signal(s) active" if active else "No signals on latest candle",
    }


# ─── Indicator ────────────────────────────────────────────────────────────────

@app.get("/api/indicator")
async def get_indicator(
    symbol:    str = Query("BTC/USDT"),
    timeframe: str = Query("4H"),
    limit:     int = Query(100, ge=50, le=500),
):
    symbol = validate_symbol(symbol)
    try:
        df = await fetch_ohlcv(symbol, timeframe, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    df = compute_all(df)
    return {
        "symbol":    symbol,
        "timeframe": timeframe,
        "candles":   len(df),
        "signals":   get_latest_signals(df, n=limit),
    }


# ─── Full Research ────────────────────────────────────────────────────────────

@app.post("/api/research", response_model=ResearchResponse)
async def run_research(req: ResearchRequest):
    symbol = validate_symbol(req.symbol)

    try:
        df = await fetch_ohlcv(symbol, req.timeframe, limit=req.candle_limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if len(df) < 100:
        raise HTTPException(status_code=400, detail="Insufficient data.")

    df = compute_all(df, chlen=req.chlen, avg=req.avg, smalen=req.smalen,
                     overbought=req.overbought, oversold=req.oversold)
    df = compute_money_flow(df)

    signal_set = [s.value for s in req.signals]
    config = BacktestConfig(
        use_green_dot       = "green_dot"       in signal_set,
        use_red_dot         = "red_dot"         in signal_set,
        use_gold_dot        = "gold_dot"        in signal_set,
        use_bull_div        = "bull_div"        in signal_set,
        use_bear_div        = "bear_div"        in signal_set,
        use_bull_div_hidden = "bull_div_hidden" in signal_set,
        use_bear_div_hidden = "bear_div_hidden" in signal_set,
        stop_loss_pct       = req.stop_loss_pct,
        risk_reward_ratio   = req.risk_reward_ratio,
        use_atr             = req.use_atr,
    )

    bt_result  = VMCBacktester(df, config).run()
    bt_summary = bt_result.summary()
    bt_trades  = bt_result.recent_trades(n=10)
    latest     = get_latest_signals(df, n=20)

    try:
        ai_report = await generate_research_report(
            symbol=symbol, timeframe=req.timeframe,
            backtest_summary=bt_summary, recent_trades=bt_trades,
            latest_signals=latest, selected_signals=signal_set,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")

    return ResearchResponse(
        symbol=symbol, timeframe=req.timeframe, candles_used=len(df),
        backtest_stats=bt_summary, recent_trades=bt_trades,
        ai_report=ai_report, latest_signals=latest[-10:],
    )


# ─── Backtest Only ────────────────────────────────────────────────────────────

@app.post("/api/backtest")
async def backtest_only(req: ResearchRequest):
    symbol = validate_symbol(req.symbol)

    try:
        df = await fetch_ohlcv(symbol, req.timeframe, limit=req.candle_limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    df = compute_all(df, chlen=req.chlen, avg=req.avg, smalen=req.smalen,
                     overbought=req.overbought, oversold=req.oversold)
    df = compute_money_flow(df)

    signal_set = [s.value for s in req.signals]
    config = BacktestConfig(
        use_green_dot       = "green_dot"       in signal_set,
        use_red_dot         = "red_dot"         in signal_set,
        use_gold_dot        = "gold_dot"        in signal_set,
        use_bull_div        = "bull_div"        in signal_set,
        use_bear_div        = "bear_div"        in signal_set,
        use_bull_div_hidden = "bull_div_hidden" in signal_set,
        use_bear_div_hidden = "bear_div_hidden" in signal_set,
        stop_loss_pct       = req.stop_loss_pct,
        risk_reward_ratio   = req.risk_reward_ratio,
        use_atr             = req.use_atr,
    )

    bt_result = VMCBacktester(df, config).run()
    return {
        "symbol":         symbol,
        "timeframe":      req.timeframe,
        "candles_used":   len(df),
        "summary":        bt_result.summary(),
        "recent_trades":  bt_result.recent_trades(n=20),
        "latest_signals": get_latest_signals(df, n=10),
    }


# ─── Meta ─────────────────────────────────────────────────────────────────────

@app.get("/api/meta")
async def meta():
    return {
        "supported_symbols": [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
            "XRP/USDT", "DOGE/USDT", "AVAX/USDT", "MATIC/USDT",
        ],
        "supported_timeframes": ["1m", "5m", "15m", "30m", "1H", "4H", "1D", "1W"],
        "htf_map": {
            "1m": "15m", "5m": "1H", "15m": "1H", "30m": "4H",
            "1H": "4H",  "4H": "1D", "1D": "1W",
        },
    }


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
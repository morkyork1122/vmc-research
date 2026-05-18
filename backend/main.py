"""
VMC Cipher B Research API v4
VMC + Money Flow + Multi-Timeframe Confirmation + 24/7 Monitor
"""

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
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
from services.mtf_analyzer import analyze_htf, combined_score, get_higher_timeframe
from services.monitor import monitor_manager
from services.notifier import send_alert
from services.webhook_receiver import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[App] Starting VMC Research API v4")
    for pair in MONITORED_PAIRS:
        if "signals" not in pair:
            pair["signals"] = DEFAULT_SIGNALS
    monitor_manager.configure(MONITORED_PAIRS)
    await monitor_manager.start()
    yield
    print("[App] Shutting down")
    await monitor_manager.stop()


app = FastAPI(title="VMC Cipher B Research API", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(webhook_router)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    monitors = [
        {"symbol": m.symbol, "timeframe": m.timeframe, "interval_s": m.interval}
        for m in monitor_manager._monitors
    ]
    return {"status": "ok", "version": "4.0.0", "monitors": monitors}


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
        "symbol": symbol, "timeframe": timeframe, "signal": signal,
        "timestamp": str(bar["timestamp"]), "close": round(float(bar["close"]), 4),
        **summary, **strength,
    }


# ─── MTF Confirmation ─────────────────────────────────────────────────────────

@app.get("/api/mtf")
async def get_mtf(
    symbol:    str = Query("BTC/USDT"),
    timeframe: str = Query("4H"),
    signal:    str = Query("green_dot"),
):
    """
    Fetch higher timeframe data and compute confirmation score for a signal.
    Also computes money flow on the primary timeframe for a combined grade.
    """
    symbol = validate_symbol(symbol)
    htf    = get_higher_timeframe(timeframe)

    # Primary TF money flow
    try:
        df_primary = await fetch_ohlcv(symbol, timeframe, limit=150)
        df_primary = compute_all(df_primary)
        df_primary = compute_money_flow(df_primary)
        mf = compute_signal_strength(df_primary, signal, len(df_primary) - 2)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Primary TF fetch failed: {e}")

    # HTF confirmation
    try:
        mtf = await analyze_htf(symbol, timeframe, signal)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HTF analysis failed: {e}")

    grade_info = combined_score(mf["score"], mtf["htf_score"])

    return {
        "symbol":        symbol,
        "primary_tf":    timeframe,
        "htf":           htf,
        "signal":        signal,
        # Primary TF money flow
        "mf_score":      mf["score"],
        "mf_strength":   mf["strength"],
        "mf_bias":       mf["mf_bias"],
        "mf_confluence": mf["confluence"],
        # HTF confirmation
        **mtf,
        # Combined grade
        "overall_score": grade_info["overall_score"],
        "grade":         grade_info["grade"],
    }


# ─── Monitor Control ──────────────────────────────────────────────────────────

@app.get("/api/monitor/status")
async def monitor_status():
    import json
    from pathlib import Path
    state_file = Path("monitor_state.json")
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass
    monitors = []
    for m in monitor_manager._monitors:
        last_signals = {
            k.split("|")[2]: v for k, v in state.items()
            if k.startswith(f"{m.symbol}|{m.timeframe}|")
        }
        monitors.append({
            "symbol": m.symbol, "timeframe": m.timeframe,
            "signals": m.signals, "poll_every_s": m.interval,
            "last_alerts": last_signals,
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
        "reasons": ["✅ CMF +0.180 — institutions buying",
                    "✅ MFI 22 — deeply oversold"],
    }
    fake_mtf = {
        "htf_timeframe": "1D", "htf_label": "Daily",
        "htf_confirmation": "CONFIRMED", "htf_score": 78,
        "htf_trend": "BULLISH", "htf_wt1": 12.3, "htf_wt2": -5.4,
        "htf_cmf": 0.12, "htf_mfi": 38.0, "htf_obv_trend": "Rising ↑",
        "htf_reasons": ["✅ Daily WT bullish — WT1 above WT2",
                        "✅ Daily CMF +0.120 — money flowing in"],
        "should_trade": True, "filter_reason": None,
    }
    ok = await send_alert(symbol, timeframe, "green_dot", fake_bar, fake_mf, fake_mtf)
    return {"status": "sent" if ok else "failed",
            "message": "Check your Telegram" if ok else "Check .env credentials"}


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
    return {"symbol": symbol, "timeframe": timeframe, "candles": len(df),
            "signals": get_latest_signals(df, n=limit)}


# ─── Research ─────────────────────────────────────────────────────────────────

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
        "symbol": symbol, "timeframe": req.timeframe, "candles_used": len(df),
        "summary": bt_result.summary(), "recent_trades": bt_result.recent_trades(n=20),
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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
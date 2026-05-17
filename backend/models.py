"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TimeframeEnum(str, Enum):
    m1  = "1m"
    m5  = "5m"
    m15 = "15m"
    m30 = "30m"
    h1  = "1H"
    h4  = "4H"
    d1  = "1D"
    w1  = "1W"


class SignalTypeEnum(str, Enum):
    green_dot       = "green_dot"
    red_dot         = "red_dot"
    gold_dot        = "gold_dot"
    bull_div        = "bull_div"
    bear_div        = "bear_div"
    bull_div_hidden = "bull_div_hidden"
    bear_div_hidden = "bear_div_hidden"


class ResearchRequest(BaseModel):
    symbol:     str             = Field(..., example="BTC/USDT")
    timeframe:  TimeframeEnum   = Field(TimeframeEnum.h4, example="4H")
    signals:    List[SignalTypeEnum] = Field(
        default=["green_dot", "red_dot", "gold_dot", "bull_div", "bear_div"],
        description="Signal types to include in backtest and analysis"
    )
    candle_limit: Optional[int] = Field(None, ge=100, le=1000, description="Number of candles to fetch")

    # VMC indicator settings (optional overrides)
    chlen:      int   = Field(10,    ge=1,  le=50,  description="WaveTrend channel length")
    avg:        int   = Field(21,    ge=1,  le=100, description="WaveTrend average length")
    smalen:     int   = Field(4,     ge=1,  le=20,  description="WaveTrend signal SMA length")
    overbought: float = Field(53.0,  description="Overbought level")
    oversold:   float = Field(-53.0, description="Oversold level")

    # Backtest settings (optional overrides)
    stop_loss_pct:     float = Field(0.02, ge=0.005, le=0.1)
    risk_reward_ratio: float = Field(2.0,  ge=0.5,   le=10.0)
    use_atr:           bool  = Field(True)


class SignalBreakdown(BaseModel):
    total:    int
    win_rate: float
    avg_pnl:  float


class BacktestStats(BaseModel):
    total_trades:  int
    win_count:     int
    loss_count:    int
    win_rate:      float
    avg_win_pct:   float
    avg_loss_pct:  float
    avg_rr:        float
    profit_factor: Optional[float]
    max_drawdown:  float
    total_pnl:     float
    by_signal:     dict


class RecentTrade(BaseModel):
    signal_type:      str
    direction:        str
    entry_price:      float
    exit_price:       float
    stop_loss:        float
    take_profit:      float
    pnl_pct:          float
    result:           str
    entry_time:       str
    exit_time:        str
    wt2_at_entry:     float
    rsimfi_at_entry:  float


class ResearchResponse(BaseModel):
    symbol:         str
    timeframe:      str
    candles_used:   int
    backtest_stats: dict
    recent_trades:  list
    ai_report:      dict
    latest_signals: list
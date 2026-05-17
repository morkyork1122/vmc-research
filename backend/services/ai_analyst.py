"""
AI Analyst — sends real computed VMC Cipher B backtest data to Claude
and returns a structured research report grounded in actual numbers.
"""

import os
import json
import httpx
from typing import Any


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-5"


async def generate_research_report(
    symbol: str,
    timeframe: str,
    backtest_summary: dict,
    recent_trades: list[dict],
    latest_signals: list[dict],
    selected_signals: list[str],
) -> dict:
    """
    Send real backtest data to Claude and get back a structured research report.

    Args:
        symbol:           e.g. "BTC/USDT"
        timeframe:        e.g. "4H"
        backtest_summary: output from BacktestResult.summary()
        recent_trades:    output from BacktestResult.recent_trades()
        latest_signals:   output from get_latest_signals()
        selected_signals: which signal types the user wants to focus on

    Returns:
        Parsed JSON research report dict.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Build the prompt with real data
    prompt = f"""You are an expert crypto technical analyst specialising in the VuManChu Cipher B (VMC Cipher B) divergence indicator.

You have been given REAL computed backtest results from {symbol} on the {timeframe} timeframe.
Signal focus: {", ".join(selected_signals) if selected_signals else "all signals"}

=== REAL BACKTEST STATISTICS ===
{json.dumps(backtest_summary, indent=2)}

=== LAST 10 TRADES ===
{json.dumps(recent_trades, indent=2)}

=== LATEST INDICATOR VALUES (last 5 bars) ===
{json.dumps(latest_signals[-5:] if latest_signals else [], indent=2)}

Based on this REAL data, generate a comprehensive research report.
Reference the actual numbers in your analysis (win rate, R:R, drawdown, signal breakdown, etc.).
Be specific, data-driven, and actionable. If the data shows a signal type underperforms, say so clearly.

Return ONLY valid JSON (no markdown, no code blocks) with this exact structure:
{{
  "overview": {{
    "summary": "2-3 sentence data-grounded overview referencing actual win rate and profit factor",
    "bestFor": "What market condition this works best for based on the backtest data",
    "reliability": "High/Medium/Low — justified by the actual backtest numbers"
  }},
  "stats": {{
    "winRate": "{backtest_summary.get('win_rate', 'N/A')}% (actual)",
    "bestTimeframe": "whether {timeframe} is optimal based on the results or mention alternative",
    "avgRR": "{backtest_summary.get('avg_rr', 'N/A')} (actual from backtest)",
    "falseSignalRate": "derived from the loss count and by_signal breakdown"
  }},
  "signalAnalysis": {{
    "bullishSetup": "Data-backed analysis of bullish signals — reference win rate from by_signal if available",
    "bearishSetup": "Data-backed analysis of bearish signals — reference win rate from by_signal if available",
    "divergenceStrength": "Analysis of bull_div/bear_div performance specifically from the backtest data",
    "goldDotSignificance": "Gold dot performance — note avg_wt2_at_winning_entry threshold from the data"
  }},
  "strategy": {{
    "entryRules": [
      "Rule grounded in the actual data — e.g. wt2 threshold for entries based on avg_wt2_at_winning_entry",
      "Rule about confirming with rsimfi direction",
      "Rule about signal confluence (multiple signals at same bar)",
      "Rule about timeframe alignment",
      "Rule about avoiding signals in certain WT zones based on the loss data"
    ],
    "exitRules": [
      "Exit rule based on opposite signal performance",
      "Exit rule based on WT reaching overbought/oversold",
      "Time-based exit rule based on avg trade duration in data"
    ],
    "filters": [
      "Filter based on avg_wt2_at_winning_entry vs avg_wt2_at_losing_entry",
      "MFI/rsimfi filter to reduce false signals",
      "Volume or trend filter recommendation"
    ],
    "optimalSettings": "Recommendation on WaveTrend channel length and avg based on the asset behaviour seen in data"
  }},
  "riskManagement": {{
    "stopLoss": "Stop loss recommendation based on max_drawdown and avg_loss_pct from backtest",
    "positionSizing": "Sizing recommendation based on win_rate and profit_factor from real data",
    "avoidWhen": "Specific conditions to avoid based on losing trade patterns in the data",
    "maxDrawdown": "Expected drawdown of {backtest_summary.get('max_drawdown', 'N/A')}% — context and mitigation"
  }},
  "marketContext": {{
    "trendingMarkets": "How the signals performed in trending conditions — infer from the data patterns",
    "rangingMarkets": "How the signals performed in ranging/sideways conditions",
    "volumeImportance": "Role of rsimfi values at entry — reference the rsimfi_at_entry from recent trades",
    "correlation": "Higher timeframe alignment recommendation for {symbol}"
  }},
  "verdict": "2-3 sentence verdict referencing the profit_factor of {backtest_summary.get('profit_factor', 'N/A')} and win_rate of {backtest_summary.get('win_rate', 'N/A')}%. Include one specific, actionable improvement based on the data."
}}"""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"[AI Analyst] Anthropic error {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()

    raw_text = data["content"][0]["text"]
    # Strip any accidental markdown fences
    clean = raw_text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip().rstrip("`").strip()

    return json.loads(clean)
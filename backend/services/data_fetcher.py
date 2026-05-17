import pandas as pd
from typing import Optional
import httpx

TIMEFRAME_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1H": "60min", "4H": "4hour", "1D": "1day", "1W": "1week",
}

CANDLE_COUNT = {
    "1min": 500, "5min": 500, "15min": 500, "30min": 500,
    "60min": 500, "4hour": 500, "1day": 365, "1week": 104,
}

HTX_BASE = "https://api.huobi.pro"


async def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    limit: Optional[int] = None,
    exchange_id: str = "htx",
) -> pd.DataFrame:

    htx_tf = TIMEFRAME_MAP.get(timeframe, "60min")
    n = limit or CANDLE_COUNT.get(htx_tf, 500)

    # Convert symbol: BTC/USDT → btcusdt
    htx_symbol = symbol.replace("/", "").lower()

    url = f"{HTX_BASE}/market/history/kline"
    params = {"symbol": htx_symbol, "period": htx_tf, "size": n}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "ok" or not data.get("data"):
        raise ValueError(f"HTX returned no data for {symbol}: {data.get('err-msg', '')}")

    # HTX returns newest first — reverse to oldest first
    candles = list(reversed(data["data"]))

    df = pd.DataFrame(candles)
    df["timestamp"] = pd.to_datetime(df["id"], unit="s", utc=True)
    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "vol": "volume"})
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df.reset_index(drop=True)


def validate_symbol(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if "/" not in symbol:
        for quote in ["USDT", "BUSD", "BTC", "ETH", "BNB"]:
            if symbol.endswith(quote):
                base = symbol[: -len(quote)]
                return f"{base}/{quote}"
    return symbol
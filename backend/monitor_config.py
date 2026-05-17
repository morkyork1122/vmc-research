"""
Monitor Configuration — edit this to control which pairs are watched.
"""

ACTIVE_SIGNALS = [
    "green_dot",
    "red_dot",
    "gold_dot",
    "bull_div",
    "bear_div",
    "bull_div_hidden",
    "bear_div_hidden",
]

MONITORED_PAIRS = [
    {"symbol": "BTC/USDT", "timeframe": "4H"},
    {"symbol": "ETH/USDT", "timeframe": "4H"},
    {"symbol": "SOL/USDT", "timeframe": "4H"},
]

DEFAULT_SIGNALS = [
    "green_dot",
    "red_dot",
    "gold_dot",
    "bull_div",
    "bear_div",
]
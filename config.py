"""
Configuration settings for the Options Trading Framework
Based on the edge hypothesis: Trend-Following Debit Spreads
"""
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# API KEYS
# =============================================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

# =============================================================================
# UNIVERSE - S&P 100 Tickers (OEX)
# =============================================================================
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK-B", "C",
    "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS",
    "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX",
    "GD", "GE", "GILD", "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM",
    "INTC", "JNJ", "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA",
    "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT",
    "NEE", "NFLX", "NKE", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM", "PYPL",
    "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS",
    "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WBA", "WFC", "WMT", "XOM"
]

# Tickers to exclude (too volatile/meme-like)
EXCLUDED_TICKERS = ["GME", "AMC", "BBBY", "RIVN", "LCID"]

# =============================================================================
# EDGE #1: TREND-FOLLOWING DEBIT SPREAD FILTERS
# =============================================================================

# Liquidity Filters (NON-NEGOTIABLE)
LIQUIDITY_FILTERS = {
    "max_spread_pct": 0.08,      # Bid-ask spread <= 8% of mid
    "min_open_interest": 500,    # Minimum OI
    "min_daily_volume": 200,     # Minimum daily option volume
}

# Trend Filters (Numeric, not vibes)
TREND_FILTERS = {
    "ma_short": 20,              # Short-term MA period
    "ma_long": 50,               # Long-term MA period
    "min_return_pct": 0.03,      # 3% move for trend confirmation
    "lookback_days": 20,         # Days for return calculation
}

# Volatility Filters
VOLATILITY_FILTERS = {
    "iv_rank_min": 20,           # Below 20 = options too cheap
    "iv_rank_max": 60,           # Above 60 = IV crush risk
}

# Event Filters
EVENT_FILTERS = {
    "min_days_to_earnings": 10,  # Don't trade within 10 days of earnings
    "avoid_fomc": True,          # Avoid macro-sensitive names around FOMC
}

# =============================================================================
# OPTION STRUCTURE RULES
# =============================================================================
OPTION_STRUCTURE = {
    "min_dte": 30,               # Minimum days to expiration
    "max_dte": 45,               # Maximum days to expiration
    "buy_delta_target": 0.35,    # Delta for long leg
    "sell_delta_target": 0.175,  # Delta for short leg (0.15-0.20)
    "delta_tolerance": 0.05,     # Acceptable deviation from target
}

# =============================================================================
# RISK MANAGEMENT (CRITICAL)
# =============================================================================
RISK_RULES = {
    "max_debit_pct_of_width": 0.30,  # Max debit <= 30% of spread width
    "max_risk_per_trade_pct": 0.02,  # Max 2% of account per trade
    "take_profit_pct": 0.50,         # Take profits at 50% of max gain
    "stop_loss_pct": 0.50,           # Cut loss at 50% of debit
    "max_concurrent_trades": 5,      # Maximum open positions
}

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
LLM_CONFIG = {
    "provider": "anthropic",     # "anthropic" or "openai"
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1000,
    "temperature": 0.3,          # Low temp for consistency
}

# =============================================================================
# DATA REFRESH INTERVALS (seconds)
# =============================================================================
REFRESH_INTERVALS = {
    "prices": 60,                # Stock prices
    "options_chain": 300,        # Options data (5 min)
    "news": 600,                 # News scraping (10 min)
    "fundamentals": 86400,       # Daily
}

# =============================================================================
# NEWS SOURCES
# =============================================================================
NEWS_SOURCES = {
    "rss_feeds": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ],
    "scrape_sites": [
        "https://finviz.com/news.ashx",
    ]
}


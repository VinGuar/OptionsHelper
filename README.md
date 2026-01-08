# Options Edge Scanner

A scanner that finds stocks matching proven options trading strategies. No AI/LLM needed - just filters based on documented market edges that output actionable trade candidates.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# List available strategies
python quick_scan.py --list

# Quick scan with strategy selection (interactive)
python quick_scan.py

# Quick scan with specific strategy
python quick_scan.py -s 1          # By number
python quick_scan.py -s trend      # By name
python quick_scan.py -s condor     # Iron Condor

# Full S&P 100 scan (interactive strategy selection)
python scanner.py
```

## Available Strategies

| # | Strategy | Edge Type | Win Rate | Risk | Best For |
|---|----------|-----------|----------|------|----------|
| 1 | Trend Following Debit | Trend | 58% | Medium | Trending markets |
| 2 | IV Crush Credit | Volatility | 68% | Medium | Post-earnings, high IV |
| 3 | Mean Reversion OTM | Mean Reversion | 45% | High | Oversold/overbought |
| 4 | Breakout Momentum | Trend | 55% | Med-High | Bull markets |
| 5 | Iron Condor Range | Volatility | 72% | Medium | Range-bound stocks |

See `STRATEGIES.txt` for detailed documentation on each strategy.

## Project Structure

```
Options/
├── scanner.py              # Full scanner with strategy selection
├── quick_scan.py           # Fast 25-ticker scan
├── config.py               # Settings and S&P 100 ticker list
├── STRATEGIES.txt          # Detailed strategy documentation
├── requirements.txt        # Dependencies
└── src/
    ├── strategies/         # Each strategy in its own file
    │   ├── base.py                  # Base strategy class
    │   ├── trend_following_debit.py # Strategy 1
    │   ├── iv_crush_credit.py       # Strategy 2
    │   ├── mean_reversion_otm.py    # Strategy 3
    │   ├── breakout_momentum.py     # Strategy 4
    │   ├── iron_condor_range.py     # Strategy 5
    │   └── loader.py                # Strategy loader
    ├── data/
    │   ├── market_data.py   # Price/options fetcher (Yahoo Finance)
    │   └── news_scraper.py  # News from RSS feeds
    └── analysis/
        ├── filters.py       # Legacy filters (still works)
        └── candidates.py    # Spread generator
```

## Adding New Strategies

1. Create a new file in `src/strategies/` (e.g., `my_strategy.py`)
2. Inherit from `BaseStrategy`
3. Implement `check_entry()`, `get_option_structure()`, `get_exit_rules()`
4. Add to `src/strategies/loader.py`

Example:
```python
from .base import BaseStrategy, StrategyResult

class MyStrategy(BaseStrategy):
    NAME = "My Custom Strategy"
    DESCRIPTION = "Description of the edge"
    EDGE_TYPE = "trend"  # or 'volatility', 'mean_reversion'
    RISK_LEVEL = "medium"
    EXPECTED_WIN_RATE = 0.55
    TYPICAL_HOLD_DAYS = 14
    
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        # Your filter logic here
        pass
```

## Data Sources (Free, No API Key)

- **Prices & Options**: Yahoo Finance (via yfinance)
- **News**: RSS feeds (Yahoo Finance, Google News, MarketWatch)

## Example Output

```
============================================================
QUICK SCANNER - Iron Condor Range
============================================================
Time: 2026-01-07 22:22:42
Tickers: 25
Win Rate: 72% | Risk: MEDIUM

[OK] 10/25 passed

------------------------------------------------------------
Ticker   Direction  Type              Strength
------------------------------------------------------------
MSFT     NEUTRAL    IRON_CONDOR            85%
PFE      NEUTRAL    IRON_CONDOR            85%
HD       NEUTRAL    IRON_CONDOR            85%
MCD      NEUTRAL    IRON_CONDOR            75%
META     NEUTRAL    IRON_CONDOR            70%
------------------------------------------------------------

TOP PICK: MSFT
  Direction: NEUTRAL
  Trade: IRON_CONDOR
  Price: $483.47
  20D Return: -1.5%

  Why:
    - Range-bound: 5D -0.8%, 20D -1.5%
    - MAs flat: spread 2.1%
    - RSI 59 (neutral)
```

## Why These Edges Work

From the research discussion this is based on:

1. **These edges are small** - expect 0.3-1% per trade
2. **Requires discipline** - most people abandon before they compound
3. **Execution matters** - use limit orders, respect liquidity
4. **Doesn't scale** - institutions can't do this at size

The edge isn't rare. The ability to stick with it is.

## Risk Management (Apply to ALL Strategies)

- Max 2% of account per trade
- Max 5 concurrent positions  
- Always have predefined exits
- Check earnings dates before EVERY trade
- Paper trade first (at least 20 trades)

## Disclaimer

Educational purposes only. Options trading involves significant risk. Past performance doesn't guarantee future results. Always paper trade first.

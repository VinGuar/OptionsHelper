# Options Edge Scanner

A web app that scans stocks for options trading opportunities using rule-based strategies. Get actionable trade setups with exact strikes, step-by-step execution instructions, and real-time market sentiment. Plus a dedicated News & Flow page with whale activity tracking, unusual options flow, sector performance, Fear & Greed index, and curated market news.

## 🌐 Live Demo

**Frontend:** [https://options-helper.vercel.app/](https://options-helper.vercel.app/)

> **Note:** The live scanning functionality is currently unavailable on the public deployment as the backend hosting trial period has concluded. To experience the full application with all features, please run it locally using the setup instructions below. The frontend interface remains accessible for demonstration purposes.

## Features

### 📊 Scanner Page
- **5 Pre-built Strategies** - Select from trend-following, IV crush, mean reversion, breakout momentum, and iron condor strategies
- **Quick or Full Scan** - Scan 30 popular tickers or the full S&P 100
- **Real-time Progress** - Watch as tickers are scanned with live progress updates
- **Trade Details** - Click any candidate to see exactly how to execute the trade
- **Step-by-Step Instructions** - Expandable explanations for each trade type
- **Export to CSV** - Download your scan results for analysis
- **Cached Results** - Results persist per strategy with timestamps (stored locally in your browser)

### 📰 News & Flow Page
- **Market Indices** - Live S&P 500, DOW, NASDAQ, and VIX levels
- **Fear & Greed Index** - Real-time market sentiment indicator
- **Sector Performance** - See which sectors are hot or cold
- **Upcoming Events** - Economic calendar for macro events
- **Unusual Options Flow** - Aggregated whale activity by ticker showing net bullish/bearish sentiment
- **Market News** - Stock-specific news with sentiment categorization
- **Independent Refresh** - Refresh market data, flow, or news separately

## Quick Start (Local Development)

```bash
# Clone the repository
git clone https://github.com/VinGuar/OptionsHelper.git
cd OptionsHelper

# Install dependencies
pip install -r requirements.txt

# Run the web app
python app.py

# Open in browser
# http://localhost:5000
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

## How to Use

### 1. Select a Strategy
Click on any of the 5 strategy cards on the left panel. Each shows:
- Expected win rate
- Risk level
- Typical holding period

### 2. Run a Scan
- Choose **Quick** (30 tickers) for fast results
- Choose **Full S&P 100** for comprehensive scanning
- Click **RUN SCAN** and watch the progress

### 3. Review Candidates
- Results show ticker, direction, trade type, signal strength, and key metrics
- Click any row to see detailed trade instructions

### 4. Execute the Trade
The details panel shows:
- **Exact strikes** to buy/sell
- **Expiration** timeframe
- **Step-by-step broker instructions**
- **Profit/loss scenarios**
- **Why this trade** for the strategy

### 5. Manage Risk
- Use the exit rules shown (take profit %, stop loss %)
- Never risk more than 2% per trade
- Paper trade first!

## Project Structure

```
Options/
├── app.py                  # Flask web server
├── scanner.py              # Console full scanner
├── quick_scan.py           # Console quick scanner
├── config.py               # Settings and ticker lists
├── STRATEGIES.txt          # Detailed strategy documentation
├── requirements.txt        # Dependencies
├── web/
│   ├── templates/
│   │   ├── index.html      # Scanner page
│   │   └── news.html       # News & Flow page
│   └── static/
│       ├── css/
│       │   ├── style.css   # Main styles
│       │   └── news.css    # News page styles
│       ├── js/
│       │   ├── app.js      # Scanner functionality
│       │   └── news.js     # News page functionality
│       └── favicon.svg     # Site icon
└── src/
    ├── strategies/         # Strategy implementations
    │   ├── base.py
    │   ├── trend_following_debit.py
    │   ├── iv_crush_credit.py
    │   ├── mean_reversion_otm.py
    │   ├── breakout_momentum.py
    │   ├── iron_condor_range.py
    │   └── loader.py
    ├── data/
    │   ├── market_data.py  # Price/options fetcher
    │   ├── news_scraper.py # News from RSS feeds
    │   └── flow_scraper.py # Unusual flow & market data
    └── analysis/
        ├── filters.py      # Edge detection filters
        └── candidates.py   # Spread generator
```

## Data Sources (Free, No API Key Required)

- **Prices & Options**: Yahoo Finance (via yfinance)
- **News**: RSS feeds (Yahoo Finance, Google News, MarketWatch, Finviz)
- **Fear & Greed**: feargreedmeter.com, CNN fallback
- **Market Data**: Yahoo Finance for indices, sectors, and events

## Console Usage (Alternative)

You can also run the scanner from the command line:

```bash
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

## Why These Edges Work

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

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Data**: yfinance, feedparser, BeautifulSoup
- **Hosting**: Vercel

## Disclaimer

Educational purposes only. Options trading involves significant risk. Past performance doesn't guarantee future results. Always paper trade first.

---

Made with ◈ for options traders who want edge, not predictions.

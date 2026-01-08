"""
Options Scanner Web App
A Flask-based web interface for the options edge scanner.

Run: python app.py
Then open: http://localhost:5000
"""
import sys
import os

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import json
from datetime import datetime

from src.data.market_data import MarketDataFetcher
from src.data.news_scraper import NewsScraper
from src.data.flow_scraper import FlowScraper, get_flow_data
from src.strategies.loader import get_strategy, list_strategies, STRATEGIES
from config import SP100_TICKERS

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
CORS(app)

# Global state for scan progress
scan_state = {
    'running': False,
    'progress': 0,
    'current_ticker': '',
    'total': 0,
    'results': None,
    'error': None,
}

# Smaller ticker list for faster scans
QUICK_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "NFLX", "CRM",
    "JPM", "BAC", "GS", "V", "MA", "XOM", "CVX", "JNJ", "UNH", "PFE",
    "WMT", "HD", "MCD", "NKE", "SBUX", "KO", "PEP", "COST", "DIS", "PYPL",
]


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/news')
def news_page():
    """News & Flow page."""
    return render_template('news.html')


@app.route('/api/strategies')
def get_strategies():
    """Get list of available strategies."""
    strategies = []
    for key, strategy_class in STRATEGIES.items():
        s = strategy_class()
        info = s.get_info()
        info['key'] = key
        strategies.append(info)
    return jsonify(strategies)


@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Start a new scan."""
    global scan_state
    
    if scan_state['running']:
        return jsonify({'error': 'Scan already running'}), 400
    
    data = request.json or {}
    strategy_key = data.get('strategy', '1')
    scan_type = data.get('type', 'quick')  # 'quick' or 'full'
    
    try:
        strategy = get_strategy(strategy_key)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    tickers = QUICK_TICKERS if scan_type == 'quick' else SP100_TICKERS
    
    # Reset state
    scan_state = {
        'running': True,
        'progress': 0,
        'current_ticker': '',
        'total': len(tickers),
        'results': None,
        'error': None,
        'strategy_name': strategy.NAME,
        'strategy_info': strategy.get_info(),
    }
    
    # Run scan in background thread
    thread = threading.Thread(target=run_scan, args=(strategy, tickers))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started', 'total': len(tickers)})


def run_scan(strategy, tickers):
    """Background scan function."""
    global scan_state
    
    try:
        # Fetch market data
        fetcher = MarketDataFetcher(tickers)
        
        def progress_callback(ticker, current, total):
            scan_state['progress'] = current
            scan_state['current_ticker'] = ticker
        
        market_data = fetcher.scan_all(progress_callback=progress_callback)
        
        # Apply strategy filters
        results = []
        for ticker, data in market_data.items():
            result = strategy.check_entry(ticker, data)
            
            # Convert to dict for JSON
            result_dict = {
                'ticker': result.ticker,
                'passed': result.passed,
                'direction': result.direction,
                'signal_strength': result.signal_strength,
                'reasons': result.reasons,
                'trade_type': result.trade_type,
                'price': data.get('price'),
                'return_5d': data.get('return_5d'),
                'return_20d': data.get('return_20d'),
                'iv_rank': data.get('iv_rank'),
                'rsi': data.get('rsi'),
                'ma20': data.get('ma20'),
                'ma50': data.get('ma50'),
            }
            results.append(result_dict)
        
        # Sort by passed + signal strength
        results.sort(key=lambda x: (x['passed'], x['signal_strength']), reverse=True)
        
        scan_state['results'] = {
            'candidates': results,
            'passed_count': len([r for r in results if r['passed']]),
            'total_count': len(results),
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy.get_info(),
            'structure': strategy.get_option_structure(),
            'exits': strategy.get_exit_rules(),
        }
        
    except Exception as e:
        scan_state['error'] = str(e)
    
    finally:
        scan_state['running'] = False


@app.route('/api/scan/status')
def scan_status():
    """Get current scan status."""
    return jsonify({
        'running': scan_state['running'],
        'progress': scan_state['progress'],
        'total': scan_state['total'],
        'current_ticker': scan_state['current_ticker'],
        'error': scan_state['error'],
        'has_results': scan_state['results'] is not None,
    })


@app.route('/api/scan/results')
def scan_results():
    """Get scan results."""
    if scan_state['results'] is None:
        return jsonify({'error': 'No results available'}), 404
    return jsonify(scan_state['results'])


@app.route('/api/news/<ticker>')
def get_news(ticker):
    """Get news for a specific ticker."""
    scraper = NewsScraper()
    news = scraper.get_ticker_news(ticker, max_articles=5)
    return jsonify(news)


@app.route('/api/news/market')
def get_market_news():
    """Get stock-specific news with sentiment for options trading."""
    scraper = NewsScraper()
    
    # Get stock-specific news with sentiment analysis
    stock_news = scraper.get_stock_news_with_sentiment(max_per_ticker=2)
    
    # Also get general market news
    market_news = scraper.get_market_news(max_articles=5)
    
    # Combine and deduplicate
    all_news = []
    seen_titles = set()
    
    for item in stock_news + market_news:
        title_key = item['title'].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            
            # Add categories
            item['categories'] = scraper.categorize_news(item)
            
            # Add impact based on sentiment strength and categories
            high_impact_cats = ['earnings', 'fda', 'merger_acquisition', 'macro', 'guidance']
            sentiment = item.get('sentiment', {})
            
            if sentiment.get('strength') == 'strong' or any(cat in high_impact_cats for cat in item['categories']):
                item['impact'] = 'high'
            else:
                item['impact'] = 'normal'
            
            all_news.append(item)
    
    # Sort by sentiment strength (strongest signals first for trading)
    all_news.sort(
        key=lambda x: (
            x.get('impact') == 'high',
            abs(x.get('sentiment', {}).get('score', 0))
        ),
        reverse=True
    )
    
    return jsonify({
        'news': all_news[:30],  # Top 30 articles
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/flow')
def get_flow():
    """Get unusual options flow and whale activity."""
    try:
        data = get_flow_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'error': str(e),
            'unusual_flow': [],
            'most_active': [],
            'movers': {'gainers': [], 'losers': []},
            'sentiment': {'value': 50, 'label': 'Neutral'},
            'timestamp': datetime.now().isoformat(),
        })


if __name__ == '__main__':
    # Create web directories if they don't exist
    os.makedirs('web/templates', exist_ok=True)
    os.makedirs('web/static/css', exist_ok=True)
    os.makedirs('web/static/js', exist_ok=True)
    
    print("\n" + "=" * 50)
    print("  OPTIONS EDGE SCANNER")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 50 + "\n")
    
    app.run(debug=True, port=5000)


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
import time
from datetime import datetime

from src.data.market_data import MarketDataFetcher
from src.data.news_scraper import NewsScraper
from src.data.flow_scraper import FlowScraper, get_flow_data
from src.data.ticker_fetcher import TickerFetcher
from src.strategies.loader import get_strategy, list_strategies, STRATEGIES
from config import SP100_TICKERS

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

# CORS configuration - allow Vercel frontend
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
CORS(app, origins=CORS_ORIGINS, supports_credentials=True)

# Global state for scan progress
scan_state = {
    'running': False,
    'progress': 0,
    'current_ticker': '',
    'total': 0,
    'results': None,
    'error': None,
    'started_at': None,  # Timestamp for timeout detection
}

# Simple in-memory cache for market data and scan results
cache = {
    'price_data': {},  # {ticker: {data, timestamp}}
    'scan_results': {},  # {cache_key: {results, timestamp}}
    'news': {},  # {key: {data, timestamp}}
    'market_data': {},  # {key: {data, timestamp}}
}

# Cache TTLs (in seconds)
CACHE_TTL = {
    'price_data': 900,  # 15 minutes
    'scan_results': 300,  # 5 minutes
    'news': 600,  # 10 minutes
    'market_data': 300,  # 5 minutes
}

# Scan timeout (5 minutes = 300 seconds)
SCAN_TIMEOUT = int(os.getenv('SCAN_TIMEOUT', '300'))

# Ticker fetcher for dynamic universe
ticker_fetcher = TickerFetcher()

# Smaller ticker list for faster scans (quick mode)
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


@app.route('/market')
def market_page():
    """Current Market page."""
    return render_template('market.html')


@app.route('/tools')
def tools_page():
    """Trading Tools page."""
    return render_template('tools.html')


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
    
    # Check for stuck scans (timeout failsafe)
    if scan_state['running'] and scan_state.get('started_at'):
        elapsed = time.time() - scan_state['started_at']
        if elapsed > SCAN_TIMEOUT:
            print(f"WARNING: Scan timeout detected ({elapsed:.0f}s > {SCAN_TIMEOUT}s). Resetting...")
            scan_state['running'] = False
            scan_state['error'] = 'Previous scan timed out. Starting new scan.'
        else:
            return jsonify({'error': 'Scan already running'}), 400
    
    if scan_state['running']:
        return jsonify({'error': 'Scan already running'}), 400
    
    data = request.json or {}
    strategy_key = data.get('strategy', '1')
    scan_type = data.get('type', 'quick')  # 'quick', 'full', or 'extended'
    
    try:
        strategy = get_strategy(strategy_key)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Check cache first
    cache_key = f"{strategy_key}_{scan_type}"
    cached = cache['scan_results'].get(cache_key)
    if cached and (time.time() - cached['timestamp']) < CACHE_TTL['scan_results']:
        print(f"Returning cached scan results for {cache_key}")
        scan_state['results'] = cached['results']
        scan_state['has_results'] = True
        scan_state['running'] = False
        return jsonify({'status': 'cached', 'total': len(cached['results'].get('candidates', []))})
    
    # Get tickers based on scan type
    if scan_type == 'quick':
        tickers = QUICK_TICKERS
    elif scan_type == 'full':
        tickers = SP100_TICKERS
    else:  # 'extended' - Full S&P 500
        try:
            tickers = ticker_fetcher.get_quality_tickers()
            if not tickers or len(tickers) == 0:
                return jsonify({'error': 'Failed to fetch tickers. Please try again.'}), 400
        except Exception as e:
            print(f"Error fetching tickers: {e}")
            return jsonify({'error': f'Error fetching tickers: {str(e)}'}), 400
    
    if not tickers or len(tickers) == 0:
        return jsonify({'error': 'No tickers available for scanning'}), 400
    
    # Reset state with timestamp
    scan_state = {
        'running': True,
        'progress': 0,
        'current_ticker': '',
        'total': len(tickers),
        'results': None,
        'error': None,
        'has_results': False,
        'strategy_name': strategy.NAME,
        'strategy_info': strategy.get_info(),
        'started_at': time.time(),  # Track when scan started
    }
    
    # Run scan in background thread
    thread = threading.Thread(target=run_scan, args=(strategy, tickers, strategy_key, cache_key))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started', 'total': len(tickers)})


def run_scan(strategy, tickers, strategy_key, cache_key):
    """Background scan function with bulletproof state management and timeout protection."""
    global scan_state, cache
    
    # Initialize state
    scan_state['running'] = True
    scan_state['error'] = None
    scan_state['has_results'] = False
    scan_state['results'] = None
    scan_state['started_at'] = time.time()
    
    try:
        # Timeout check at start
        if scan_state.get('started_at') and (time.time() - scan_state['started_at']) > SCAN_TIMEOUT:
            scan_state['error'] = f'Scan timeout exceeded ({SCAN_TIMEOUT}s)'
            scan_state['has_results'] = False
            return
        
        # Fetch market data
        fetcher = MarketDataFetcher(tickers)
        
        def progress_callback(ticker_or_msg, current, total):
            # Check timeout during progress updates
            if scan_state.get('started_at') and (time.time() - scan_state['started_at']) > SCAN_TIMEOUT:
                raise TimeoutError(f'Scan exceeded timeout of {SCAN_TIMEOUT}s')
            scan_state['progress'] = current
            scan_state['current_ticker'] = str(ticker_or_msg) if ticker_or_msg else ''
        
        # Only fetch options if strategy needs them (most don't need full chain)
        needs_options = strategy_key in ['2', '5']  # IV Crush and Iron Condor need options data
        market_data = fetcher.scan_all(progress_callback=progress_callback, fetch_options=needs_options)
        
        if not market_data or len(market_data) == 0:
            scan_state['error'] = 'No market data retrieved. Check internet connection or try again.'
            scan_state['has_results'] = False
            return
        
        # Apply strategy filters
        results = []
        for ticker, data in market_data.items():
            # Check timeout periodically
            if scan_state.get('started_at') and (time.time() - scan_state['started_at']) > SCAN_TIMEOUT:
                raise TimeoutError(f'Scan exceeded timeout of {SCAN_TIMEOUT}s')
            
            try:
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
            except Exception as e:
                # Skip individual ticker errors
                continue
        
        # Sort by passed + signal strength
        results.sort(key=lambda x: (x['passed'], x['signal_strength']), reverse=True)
        
        scan_results = {
            'candidates': results,
            'passed_count': len([r for r in results if r['passed']]),
            'total_count': len(results),
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy.get_info(),
            'structure': strategy.get_option_structure(),
            'exits': strategy.get_exit_rules(),
        }
        
        # Cache results
        cache['scan_results'][cache_key] = {
            'results': scan_results,
            'timestamp': time.time()
        }
        
        scan_state['results'] = scan_results
        scan_state['has_results'] = True
        scan_state['error'] = None
        
    except TimeoutError as e:
        print(f"Scan timeout: {e}")
        scan_state['error'] = str(e)
        scan_state['has_results'] = False
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Scan error: {error_msg}")
        scan_state['error'] = str(e)
        scan_state['has_results'] = False
    finally:
        # Always reset running state, even on error
        scan_state['running'] = False
        scan_state['started_at'] = None


@app.route('/api/scan/reset', methods=['POST'])
def reset_scan():
    """Reset scan state (force clear if stuck)."""
    global scan_state
    scan_state = {
        'running': False,
        'progress': 0,
        'current_ticker': '',
        'total': 0,
        'results': None,
        'error': None,
        'has_results': False,
        'started_at': None,
    }
    return jsonify({'status': 'reset'})


@app.route('/api/scan/status')
def scan_status():
    """Get current scan status."""
    # Check for timeout
    if scan_state.get('running') and scan_state.get('started_at'):
        elapsed = time.time() - scan_state['started_at']
        if elapsed > SCAN_TIMEOUT:
            scan_state['running'] = False
            scan_state['error'] = f'Scan timed out after {SCAN_TIMEOUT}s'
            scan_state['started_at'] = None
    
    return jsonify({
        'running': scan_state.get('running', False),
        'progress': scan_state.get('progress', 0),
        'total': scan_state.get('total', 0),
        'current_ticker': scan_state.get('current_ticker', ''),
        'error': scan_state.get('error'),
        'has_results': scan_state.get('has_results', False) or scan_state.get('results') is not None,
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
    """Get unusual options flow and whale activity only."""
    try:
        scraper = FlowScraper()
        return jsonify({
            'unusual_flow': scraper.get_unusual_flow(),
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'unusual_flow': [],
            'timestamp': datetime.now().isoformat(),
        })


@app.route('/api/market')
def get_market():
    """Get market data: indices, sentiment, sectors, events, movers."""
    try:
        scraper = FlowScraper()
        return jsonify({
            'sentiment': scraper.get_fear_greed_index(),
            'indices': scraper.get_market_indices(),
            'sectors': scraper.get_sector_performance(),
            'events': scraper.get_upcoming_events(),
            'movers': scraper.get_market_movers(),
            'most_active': scraper.get_most_active_options(),
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'sentiment': {'value': 50, 'label': 'Neutral'},
            'indices': {},
            'sectors': [],
            'events': [],
            'movers': {'gainers': [], 'losers': []},
            'most_active': [],
            'timestamp': datetime.now().isoformat(),
        })


@app.route('/api/earnings')
def get_earnings():
    """Get upcoming earnings calendar."""
    filter_type = request.args.get('filter', 'this-week')
    
    try:
        scraper = FlowScraper()
        earnings = scraper.get_earnings_calendar(filter_type)
        return jsonify({
            'earnings': earnings,
            'filter': filter_type,
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'earnings': [],
            'filter': filter_type,
            'timestamp': datetime.now().isoformat(),
        })


@app.route('/api/quote/<ticker>')
def get_quote(ticker):
    """Get quick quote for a ticker."""
    try:
        fetcher = MarketDataFetcher([ticker.upper()])
        data = fetcher.get_ticker_data(ticker.upper())
        
        if data:
            return jsonify({
                'ticker': ticker.upper(),
                'price': data.get('price'),
                'change_pct': data.get('return_1d', 0) * 100 if data.get('return_1d') else None,
                'iv_rank': data.get('iv_rank'),
                'timestamp': datetime.now().isoformat(),
            })
        else:
            return jsonify({'error': 'Could not fetch data'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Create web directories if they don't exist
    os.makedirs('web/templates', exist_ok=True)
    os.makedirs('web/static/css', exist_ok=True)
    os.makedirs('web/static/js', exist_ok=True)
    
    # Get port from environment (Railway sets PORT)
    port = int(os.getenv('PORT', 5000))
    # Enable debug mode by default for local development (unless explicitly disabled)
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("\n" + "=" * 50)
    print("  OPTIONS EDGE SCANNER")
    print(f"  Running on port {port}")
    if debug:
        print("  Debug mode: ON (auto-reload enabled)")
    else:
        print("  Production mode")
    print("=" * 50 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)


"""
Debug script to test strategies with sample data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.strategies.loader import get_strategy
from src.data.market_data import MarketDataFetcher

# Enable debug mode
os.environ['DEBUG_STRATEGY'] = 'true'

# Test with a few tickers
test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMD', 'NFLX', 'META']

print("=" * 70)
print("STRATEGY DEBUG TEST")
print("=" * 70)

# Test each strategy
for strategy_num in ['1', '2', '3', '4', '5']:
    strategy = get_strategy(strategy_num)
    print(f"\n{'='*70}")
    print(f"Testing Strategy {strategy_num}: {strategy.NAME}")
    print(f"{'='*70}")
    
    # Fetch data
    fetcher = MarketDataFetcher(test_tickers)
    market_data = fetcher.scan_all(fetch_options=True)
    
    print(f"\nFetched data for {len(market_data)} tickers")
    
    # Test each ticker
    passed = []
    failed = []
    
    for ticker, data in market_data.items():
        result = strategy.check_entry(ticker, data)
        if result.passed:
            passed.append(ticker)
            print(f"\n[PASS] {ticker}")
            print(f"  Direction: {result.direction}")
            print(f"  Strength: {result.signal_strength}")
            print(f"  Reasons: {', '.join(result.reasons[:3])}")
        else:
            failed.append((ticker, result.reasons[0] if result.reasons else "Unknown"))
    
    print(f"\nSummary:")
    print(f"  Passed: {len(passed)}/{len(market_data)}")
    if passed:
        print(f"  Passed tickers: {', '.join(passed)}")
    else:
        print(f"\n  Top failure reasons:")
        failure_counts = {}
        for ticker, reason in failed:
            if reason not in failure_counts:
                failure_counts[reason] = []
            failure_counts[reason].append(ticker)
        
        sorted_failures = sorted(failure_counts.items(), key=lambda x: len(x[1]), reverse=True)
        for reason, tickers in sorted_failures[:5]:
            print(f"    {reason}: {len(tickers)} tickers ({', '.join(tickers[:5])})")
    
    print()


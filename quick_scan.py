"""
Quick Scanner - Fast scan with fewer tickers for testing.
Supports strategy selection.

Run: python quick_scan.py
     python quick_scan.py --strategy 2
     python quick_scan.py -s trend
"""
import sys
import os
import argparse

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime

from src.data.market_data import MarketDataFetcher
from src.strategies.loader import get_strategy, print_strategy_menu, STRATEGIES, STRATEGY_NAMES
from src.strategies.base import StrategyResult

# Quick scan - diverse set of liquid stocks
QUICK_TICKERS = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "NFLX", "CRM",
    # Finance
    "JPM", "BAC", "GS", "V", "MA",
    # Energy/Healthcare
    "XOM", "CVX", "JNJ", "UNH", "PFE",
    # Consumer
    "WMT", "HD", "MCD", "NKE", "SBUX",
]


def parse_args():
    parser = argparse.ArgumentParser(description='Quick Options Scanner')
    parser.add_argument('-s', '--strategy', type=str, default=None,
                        help='Strategy number (1-5) or name (trend, iv_crush, mean_rev, breakout, condor)')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List available strategies and exit')
    return parser.parse_args()


def select_strategy_interactive():
    """Interactive strategy selection."""
    print_strategy_menu()
    
    while True:
        choice = input("\nSelect strategy [1-5]: ").strip()
        if choice in STRATEGIES:
            return get_strategy(choice)
        print(f"Invalid choice. Please enter 1-5.")


def main():
    args = parse_args()
    
    # List strategies and exit
    if args.list:
        print_strategy_menu()
        return
    
    # Get strategy
    if args.strategy:
        try:
            strategy = get_strategy(args.strategy)
        except ValueError as e:
            print(f"Error: {e}")
            print("Use --list to see available strategies")
            return
    else:
        strategy = select_strategy_interactive()
    
    print("\n" + "=" * 60)
    print(f"QUICK SCANNER - {strategy.NAME}")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tickers: {len(QUICK_TICKERS)}")
    print(f"Win Rate: {strategy.EXPECTED_WIN_RATE*100:.0f}% | Risk: {strategy.RISK_LEVEL.upper()}")
    print()
    
    # Fetch data
    fetcher = MarketDataFetcher(QUICK_TICKERS)
    
    print("Fetching market data...")
    # All strategies need options data to evaluate properly
    market_data = fetcher.scan_all(
        progress_callback=lambda t, i, n: print(f"  [{i}/{n}] {t}        ", end="\r"),
        fetch_options=True
    )
    print(f"\n[OK] Got data for {len(market_data)} tickers\n")
    
    # Apply strategy
    print(f"Applying {strategy.NAME} filters...")
    results = []
    for ticker, data in market_data.items():
        result = strategy.check_entry(ticker, data)
        results.append(result)
    
    results.sort(key=lambda x: (x.passed, x.signal_strength), reverse=True)
    passed = [r for r in results if r.passed]
    
    print(f"[OK] {len(passed)}/{len(results)} passed\n")
    
    # Display results
    if passed:
        print("-" * 60)
        print(f"{'Ticker':<8} {'Direction':<10} {'Type':<15} {'Strength':>10}")
        print("-" * 60)
        
        for r in passed[:10]:
            d = market_data.get(r.ticker, {})
            print(f"{r.ticker:<8} {r.direction or 'NEUTRAL':<10} {r.trade_type:<15} {r.signal_strength:>9.0f}%")
        
        print("-" * 60)
        
        # Top candidate details
        top = passed[0]
        data = market_data.get(top.ticker, {})
        
        print(f"\nTOP PICK: {top.ticker}")
        print(f"  Direction: {top.direction}")
        print(f"  Trade: {top.trade_type}")
        print(f"  Price: ${data.get('price', 0):.2f}")
        print(f"  20D Return: {data.get('return_20d', 0):+.1f}%")
        print(f"  IV Rank: {data.get('iv_rank', 'N/A')}")
        print(f"  RSI: {data.get('rsi', 'N/A')}")
        print("\n  Why:")
        for reason in top.reasons[:4]:
            print(f"    - {reason}")
    else:
        print("[!] No candidates found for this strategy.")
        print("    Try a different strategy or wait for better setups.")
        
        # Show near misses
        near = [r for r in results if r.signal_strength >= 25][:3]
        if near:
            print("\n    Near misses:")
            for r in near:
                print(f"      {r.ticker}: {r.reasons[0] if r.reasons else '?'}")
    
    # Sample failures
    failed = [r for r in results if not r.passed][:5]
    if failed:
        print("\n--- Sample failures ---")
        for r in failed:
            reason = r.reasons[0][:50] + "..." if r.reasons and len(r.reasons[0]) > 50 else (r.reasons[0] if r.reasons else "?")
            print(f"  {r.ticker}: {reason}")
    
    print("\n[DONE]")


if __name__ == "__main__":
    main()

"""
Options Edge Scanner
Scans for stocks matching your selected strategy's criteria.

Run: python scanner.py
"""
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime

from src.data.market_data import MarketDataFetcher
from src.data.news_scraper import NewsScraper
from src.strategies.loader import get_strategy, list_strategies, print_strategy_menu, STRATEGIES
from src.strategies.base import BaseStrategy, StrategyResult
from config import SP100_TICKERS


def print_header(strategy_name: str):
    """Print scanner header."""
    print("\n" + "=" * 70)
    print("         OPTIONS EDGE SCANNER v2.0")
    print(f"         Strategy: {strategy_name}")
    print("=" * 70)
    print(f"  Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Universe: S&P 100 ({len(SP100_TICKERS)} tickers)\n")


def select_strategy() -> BaseStrategy:
    """Interactive strategy selection."""
    print_strategy_menu()
    
    while True:
        choice = input("\nSelect strategy [1-5] or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("Goodbye!")
            sys.exit(0)
        
        if choice in STRATEGIES:
            return get_strategy(choice)
        
        print(f"Invalid choice: {choice}. Please enter 1-5.")


def scan_with_strategy(strategy: BaseStrategy, tickers: list[str]) -> tuple[dict, list[StrategyResult]]:
    """
    Scan tickers using the selected strategy.
    """
    print("[*] Fetching market data...")
    print("    (This may take 5-10 minutes for full S&P 100)\n")
    
    fetcher = MarketDataFetcher(tickers)
    
    def update_progress(ticker, current, total):
        pct = current / total * 100
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        print(f"  [{bar}] {current}/{total} {ticker}        ", end="\r")
    
    market_data = fetcher.scan_all(progress_callback=update_progress)
    
    print(f"\n\n[OK] Fetched data for {len(market_data)} tickers\n")
    
    # Apply strategy filters
    print(f"[*] Applying {strategy.NAME} filters...")
    
    results = []
    for ticker, data in market_data.items():
        result = strategy.check_entry(ticker, data)
        results.append(result)
    
    # Sort by signal strength
    results.sort(key=lambda x: (x.passed, x.signal_strength), reverse=True)
    
    passed = [r for r in results if r.passed]
    print(f"[OK] {len(passed)} tickers passed all filters\n")
    
    return market_data, results


def display_results(results: list[StrategyResult], market_data: dict, strategy: BaseStrategy):
    """Display scan results."""
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    
    # Summary
    print("-" * 70)
    print(f"{'SCAN SUMMARY':^70}")
    print("-" * 70)
    print(f"  Strategy: {strategy.NAME}")
    print(f"  Edge Type: {strategy.EDGE_TYPE.upper()}")
    print(f"  Expected Win Rate: {strategy.EXPECTED_WIN_RATE * 100:.0f}%")
    print(f"  Passed: {len(passed)} / {len(results)}")
    print("-" * 70)
    
    if not passed:
        print("\n[!] No tickers passed all filters for this strategy.")
        print("    This is normal - strict filters mean fewer but better trades.")
        
        # Show near-misses
        near_miss = [r for r in failed if r.signal_strength >= 30][:5]
        if near_miss:
            print("\n    Near misses (almost passed):")
            for r in near_miss:
                print(f"      {r.ticker}: {r.reasons[0] if r.reasons else 'Unknown'}")
        return
    
    # Display passed tickers
    print("\n" + "=" * 70)
    print(f"{'TRADE CANDIDATES':^70}")
    print("=" * 70)
    
    print(f"\n{'#':<3} {'Ticker':<8} {'Direction':<10} {'Type':<15} {'Strength':>8} {'Price':>10}")
    print("-" * 70)
    
    for i, result in enumerate(passed[:15], 1):  # Top 15
        data = market_data.get(result.ticker, {})
        price = f"${data.get('price', 0):.2f}"
        
        dir_display = result.direction or 'NEUTRAL'
        
        print(f"{i:<3} {result.ticker:<8} {dir_display:<10} {result.trade_type:<15} {result.signal_strength:>7.0f}% {price:>10}")
    
    print("-" * 70)
    
    # Detailed view of top 5
    print("\n" + "=" * 70)
    print(f"{'DETAILED VIEW (Top 5)':^70}")
    print("=" * 70)
    
    for i, result in enumerate(passed[:5], 1):
        data = market_data.get(result.ticker, {})
        
        print(f"\n#{i} {result.ticker} - {result.direction or 'NEUTRAL'}")
        print("-" * 50)
        print(f"  Trade Type: {result.trade_type}")
        print(f"  Signal Strength: {result.signal_strength:.0f}%")
        print(f"  Current Price: ${data.get('price', 0):.2f}")
        print(f"  20D Return: {data.get('return_20d', 0):+.1f}%")
        print(f"  IV Rank: {data.get('iv_rank', 'N/A')}")
        print(f"  RSI: {data.get('rsi', 'N/A')}")
        print()
        print("  Reasons:")
        for reason in result.reasons:
            print(f"    - {reason}")
        
        # Show option structure recommendation
        structure = strategy.get_option_structure()
        exits = strategy.get_exit_rules()
        
        print()
        print(f"  Recommended Structure:")
        print(f"    DTE: {structure.get('dte_min', 30)}-{structure.get('dte_max', 45)} days")
        if 'long_delta' in structure:
            print(f"    Long Delta: ~{structure['long_delta']}")
        if 'short_delta' in structure:
            print(f"    Short Delta: ~{structure['short_delta']}")
        
        print()
        print(f"  Exit Rules:")
        print(f"    Take Profit: {exits.get('take_profit_pct', 0.5)*100:.0f}% of max gain")
        print(f"    Stop Loss: {exits.get('stop_loss_pct', 0.5)*100:.0f}% of entry")


def display_failed_sample(results: list[StrategyResult], limit: int = 8):
    """Show sample of why tickers failed."""
    failed = [r for r in results if not r.passed][:limit]
    
    if not failed:
        return
    
    print(f"\n--- Sample Failures (showing {len(failed)}) ---")
    for r in failed:
        reason = r.reasons[0] if r.reasons else 'Unknown'
        # Truncate long reasons
        if len(reason) > 60:
            reason = reason[:57] + "..."
        print(f"  {r.ticker}: {reason}")


def fetch_news_for_results(results: list[StrategyResult]):
    """Fetch news for top results."""
    passed = [r for r in results if r.passed][:3]
    
    if not passed:
        return
    
    print("\n[*] Fetching news for top candidates...")
    
    scraper = NewsScraper()
    
    for result in passed:
        news = scraper.get_ticker_news(result.ticker, max_articles=2)
        
        if news:
            print(f"\n  {result.ticker} News:")
            for item in news:
                title = item['title'][:65] + "..." if len(item['title']) > 65 else item['title']
                print(f"    - {title}")


def main():
    """Main scanner entry point."""
    # Strategy selection
    strategy = select_strategy()
    
    print_header(strategy.NAME)
    
    # Show strategy info
    info = strategy.get_info()
    print(f"  Edge Type: {info['edge_type'].upper()}")
    print(f"  Risk Level: {info['risk_level'].upper()}")
    print(f"  Expected Win Rate: {info['expected_win_rate']*100:.0f}%")
    print(f"  Typical Hold: {info['typical_hold_days']} days")
    print()
    
    try:
        # Scan
        market_data, results = scan_with_strategy(strategy, SP100_TICKERS)
        
        # Display results
        display_results(results, market_data, strategy)
        
        # Show sample failures
        display_failed_sample(results)
        
        # Fetch news
        fetch_news_for_results(results)
        
        print("\n" + "=" * 70)
        print("SCAN COMPLETE")
        print("=" * 70)
        print("\nRemember: Paper trade first. Risk management > prediction accuracy.")
        
    except KeyboardInterrupt:
        print("\n[!] Scan interrupted.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise


if __name__ == "__main__":
    main()

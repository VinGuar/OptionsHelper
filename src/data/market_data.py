"""
Market Data Scraper - Optimized with batch downloads
Fetches real-time stock prices, options chains, and calculates technical indicators.
Uses batch downloads for 10-30x speed improvement.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
warnings.filterwarnings('ignore')


class MarketDataFetcher:
    """Fetches and processes market data for options scanning."""
    
    def __init__(self, tickers: list[str]):
        self.tickers = tickers
        self.price_cache = {}
        self.options_cache = {}
        self.batch_data = None
        
    def scan_all(self, progress_callback=None, fetch_options: bool = False) -> dict:
        """
        Scan all tickers using batch downloads for speed (like local version).
        Two-phase approach:
        1. Phase 1: Batch download prices + calculate indicators (fast)
        2. Phase 2: Enrich top candidates with options data (if needed)
        """
        results = {}
        total = len(self.tickers)
        
        # Phase 1: Batch download all prices at once (10-30x faster - same as local)
        if progress_callback:
            try:
                progress_callback("Batch downloading prices...", 0, total)
            except:
                pass  # Ignore callback errors
        
        try:
            # Download all tickers at once with timeout wrapper (same as local)
            def batch_download_with_timeout():
                return yf.download(
                    self.tickers,
                    period="6mo",  # Use 6mo instead of 1y for speed
                    group_by="ticker",
                    threads=True,
                    progress=False
                )
            
            # Wrap batch download in timeout to prevent hanging
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(batch_download_with_timeout)
                try:
                    batch_data = future.result(timeout=30)  # 30s timeout for batch
                except FutureTimeoutError:
                    print("Batch download timeout, falling back to sequential...")
                    return self._scan_sequential(progress_callback, fetch_options)
            
            if batch_data.empty:
                print("Warning: Batch download returned empty data")
                return self._scan_sequential(progress_callback, fetch_options)
            
            # Count successfully downloaded tickers
            if isinstance(batch_data.columns, pd.MultiIndex):
                downloaded_count = len(batch_data.columns.levels[0])
            else:
                downloaded_count = 1 if len(self.tickers) == 1 else 0
            
            print(f"Downloaded data for {downloaded_count} tickers")
            
        except Exception as e:
            print(f"Batch download error: {e}, falling back to sequential...")
            return self._scan_sequential(progress_callback, fetch_options)
        
        # Process each ticker from batch data (fast - just data processing)
        processed_count = 0
        for i, ticker in enumerate(self.tickers):
            if progress_callback:
                try:
                    progress_callback(ticker, i + 1, total)
                except:
                    pass
            
            try:
                # Extract ticker data from batch
                price_data = None
                
                if isinstance(batch_data.columns, pd.MultiIndex):
                    if ticker in batch_data.columns.levels[0]:
                        price_data = batch_data[ticker].copy()
                elif len(self.tickers) == 1:
                    price_data = batch_data.copy()
                
                if price_data is None or price_data.empty or len(price_data) < 50:
                    continue
                
                # Process ticker data
                ticker_result = self._process_ticker_data(ticker, price_data)
                if ticker_result:
                    results[ticker] = ticker_result
                    processed_count += 1
                    
            except Exception as e:
                continue
        
        print(f"Processed {processed_count} tickers from batch download")
        
        # Phase 2: Enrich top candidates with options data (if needed)
        if fetch_options and results:
            top_candidates = sorted(
                results.items(),
                key=lambda x: abs(x[1].get('return_20d', 0) or 0),
                reverse=True
            )[:20]
            
            for ticker, _ in top_candidates:
                try:
                    options_data = self.get_options_chain(ticker)
                    if options_data:
                        results[ticker]['options'] = options_data
                except Exception as e:
                    continue
        
        return results
    
    def _scan_concurrent(self, progress_callback=None, fetch_options: bool = False) -> dict:
        """Download tickers concurrently with timeouts for speed and reliability."""
        results = {}
        total = len(self.tickers)
        
        def fetch_single_ticker(ticker):
            """Fetch data for a single ticker - optimized for speed."""
            try:
                stock = yf.Ticker(ticker)
                # Use 6mo period instead of 1y - much faster and we only need recent data
                # This is 2-3x faster than 1y downloads
                price_data = stock.history(period="6mo")
                return ticker, price_data
            except Exception as e:
                return ticker, None
        
        # Use more workers for better concurrency (up to 20 for faster scans)
        max_workers = min(20, total)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(fetch_single_ticker_with_timeout, ticker): ticker 
                for ticker in self.tickers
            }
            
            # Process completed tasks with progress updates
            completed = 0
            processed_tickers = set()
            
            try:
                # Use shorter timeout to prevent hanging
                for future in as_completed(future_to_ticker, timeout=45):  # 45s total timeout
                    ticker = future_to_ticker[future]
                    
                    if ticker in processed_tickers:
                        continue
                    processed_tickers.add(ticker)
                    completed += 1
                    
                    # Update progress immediately
                    if progress_callback:
                        try:
                            progress_callback(ticker, completed, total)
                        except:
                            pass
                    
                    try:
                        ticker, price_data = future.result(timeout=1)  # Quick result check
                        
                        if price_data is None or price_data.empty or len(price_data) < 50:
                            continue
                        
                        # Process this ticker's data
                        ticker_result = self._process_ticker_data(ticker, price_data)
                        if ticker_result:
                            results[ticker] = ticker_result
                    except FutureTimeoutError:
                        # Skip this ticker if it times out
                        continue
                    except Exception as e:
                        continue
            except FutureTimeoutError:
                # Overall timeout - mark remaining as processed
                for ticker in self.tickers:
                    if ticker not in processed_tickers:
                        completed += 1
                        processed_tickers.add(ticker)
                        if progress_callback:
                            try:
                                progress_callback(ticker, completed, total)
                            except:
                                pass
                # Return what we have so far
                pass
        
        # Phase 2: Enrich top candidates with options data (if needed)
        if fetch_options and results:
            # Only fetch options for top 20 candidates by price movement
            top_candidates = sorted(
                results.items(),
                key=lambda x: abs(x[1].get('return_20d', 0) or 0),
                reverse=True
            )[:20]
            
            for ticker, _ in top_candidates:
                try:
                    options_data = self.get_options_chain(ticker)
                    if options_data:
                        results[ticker]['options'] = options_data
                except Exception as e:
                    continue
        
        return results
    
    def _process_ticker_data(self, ticker: str, price_data: pd.DataFrame) -> Optional[dict]:
        """Process price data for a single ticker and return market data dict."""
        try:
            # Ensure we have Close column
            if 'Close' not in price_data.columns:
                if 'Adj Close' in price_data.columns:
                    price_data = price_data.copy()
                    price_data['Close'] = price_data['Adj Close']
                else:
                    return None
            
            # Clean and prepare data
            price_data = price_data.dropna(subset=['Close'])
            if len(price_data) < 50:
                return None
            
            # Use last 3 months for calculations (faster)
            price_data_subset = price_data.tail(90) if len(price_data) >= 90 else price_data
            
            # Calculate indicators
            price_data_subset = price_data_subset.copy()
            price_data_subset['MA20'] = price_data_subset['Close'].rolling(window=20).mean()
            price_data_subset['MA50'] = price_data_subset['Close'].rolling(window=50).mean()
            price_data_subset['Return_1D'] = price_data_subset['Close'].pct_change()
            price_data_subset['Return_5D'] = price_data_subset['Close'].pct_change(5)
            price_data_subset['Return_20D'] = price_data_subset['Close'].pct_change(20)
            price_data_subset['RealizedVol_20D'] = price_data_subset['Return_1D'].rolling(window=20).std() * np.sqrt(252)
            
            # RSI
            delta = price_data_subset['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            price_data_subset['RSI'] = 100 - (100 / (1 + rs))
            
            # Get latest values
            latest = price_data_subset.iloc[-1]
            
            # Calculate IV rank using full year data
            iv_rank = self._calculate_iv_rank(price_data)
            
            return {
                'price': round(float(latest['Close']), 2),
                'ma20': round(float(latest['MA20']), 2) if pd.notna(latest['MA20']) else None,
                'ma50': round(float(latest['MA50']), 2) if pd.notna(latest['MA50']) else None,
                'return_1d': round(float(latest['Return_1D'] * 100), 2) if pd.notna(latest['Return_1D']) else None,
                'return_5d': round(float(latest['Return_5D'] * 100), 2) if pd.notna(latest['Return_5D']) else None,
                'return_20d': round(float(latest['Return_20D'] * 100), 2) if pd.notna(latest['Return_20D']) else None,
                'realized_vol': round(float(latest['RealizedVol_20D'] * 100), 2) if pd.notna(latest['RealizedVol_20D']) else None,
                'rsi': round(float(latest['RSI']), 1) if pd.notna(latest['RSI']) else None,
                'iv_rank': iv_rank,
                'earnings_date': None,
                'options': None,  # Will be fetched in phase 2 if needed
            }
        except Exception as e:
            return None
    
    def _scan_sequential(self, progress_callback=None, fetch_options: bool = False) -> dict:
        """Fallback sequential scanning if concurrent download fails."""
        results = {}
        total = len(self.tickers)
        
        for i, ticker in enumerate(self.tickers):
            if progress_callback:
                try:
                    progress_callback(ticker, i + 1, total)
                except:
                    pass
            
            try:
                stock = yf.Ticker(ticker)
                # Fetch with timeout wrapper
                price_data = None
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(stock.history, period="1y")
                    try:
                        price_data = future.result(timeout=15)  # 15s timeout per ticker
                    except FutureTimeoutError:
                        continue
                
                if price_data.empty or len(price_data) < 50:
                    continue
                
                # Process ticker data
                ticker_result = self._process_ticker_data(ticker, price_data)
                if ticker_result:
                    results[ticker] = ticker_result
            except Exception as e:
                continue
        
        # Phase 2: Enrich top candidates with options data (if needed)
        if fetch_options and results:
            # Only fetch options for top 20 candidates by price movement
            top_candidates = sorted(
                results.items(),
                key=lambda x: abs(x[1].get('return_20d', 0) or 0),
                reverse=True
            )[:20]
            
            for ticker, _ in top_candidates:
                try:
                    options_data = self.get_options_chain(ticker)
                    if options_data:
                        results[ticker]['options'] = options_data
                except Exception as e:
                    continue
        
        return results
    
    def _calculate_iv_rank(self, price_data: pd.DataFrame) -> Optional[float]:
        """Calculate IV Rank from price data (using realized vol as proxy)."""
        try:
            # Need at least 100 days to calculate meaningful IV rank
            # (previously required 252, but that's too strict - 100+ days is sufficient)
            if len(price_data) < 100:
                return None
            
            # Ensure we have Close column
            if 'Close' not in price_data.columns:
                if 'Adj Close' in price_data.columns:
                    price_data = price_data.copy()
                    price_data['Close'] = price_data['Adj Close']
                else:
                    return None
            
            returns = price_data['Close'].pct_change().dropna()
            if len(returns) < 50:
                return None
            
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252)
            rolling_vol = rolling_vol.dropna()
            
            # Need at least 30 rolling vol calculations to get meaningful min/max
            if len(rolling_vol) < 30:
                return None
            
            current_vol = rolling_vol.iloc[-1]
            vol_min = rolling_vol.min()
            vol_max = rolling_vol.max()
            
            # Handle edge cases
            if pd.isna(current_vol) or pd.isna(vol_min) or pd.isna(vol_max):
                return None
            
            if vol_max == vol_min:
                # All volatility is the same - return middle value
                return 50.0
            
            iv_rank = ((current_vol - vol_min) / (vol_max - vol_min)) * 100
            # Clamp to 0-100 range (shouldn't happen, but safety check)
            iv_rank = max(0, min(100, iv_rank))
            return round(float(iv_rank), 1)
        except Exception as e:
            # Log error for debugging but don't crash
            print(f"IV Rank calculation error: {e}")
            return None
    
    def get_options_chain(self, ticker: str) -> Optional[dict]:
        """
        Fetch options chain for a ticker.
        Returns dict with calls/puts DataFrames and metadata.
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get available expiration dates
            expirations = stock.options
            if not expirations:
                return None
            
            # Get current price
            current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
            if not current_price:
                hist = stock.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    return None
            
            # Filter expirations to 30-45 DTE window
            today = datetime.now().date()
            valid_expirations = []
            
            for exp in expirations:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                dte = (exp_date - today).days
                if 30 <= dte <= 45:
                    valid_expirations.append((exp, dte))
            
            if not valid_expirations:
                # Fallback: get closest to 30-45 range
                for exp in expirations:
                    exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                    dte = (exp_date - today).days
                    if 20 <= dte <= 60:
                        valid_expirations.append((exp, dte))
                        break
            
            if not valid_expirations:
                return None
            
            # Get chain for best expiration
            best_exp, best_dte = valid_expirations[0]
            chain = stock.option_chain(best_exp)
            
            calls = chain.calls.copy()
            puts = chain.puts.copy()
            
            # Calculate spread percentage
            for df in [calls, puts]:
                df['spread'] = df['ask'] - df['bid']
                df['mid'] = (df['ask'] + df['bid']) / 2
                df['spread_pct'] = df['spread'] / df['mid'].replace(0, np.nan)
                df['moneyness'] = df['strike'] / current_price
            
            result = {
                'ticker': ticker,
                'current_price': current_price,
                'expiration': best_exp,
                'dte': best_dte,
                'calls': calls,
                'puts': puts,
            }
            
            self.options_cache[ticker] = result
            return result
            
        except Exception as e:
            return None


def fetch_market_data(tickers: list[str], progress_callback=None) -> dict:
    """Convenience function to fetch all market data."""
    fetcher = MarketDataFetcher(tickers)
    return fetcher.scan_all(progress_callback=progress_callback)

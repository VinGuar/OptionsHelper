"""
Market Data Scraper
Fetches real-time stock prices, options chains, and calculates technical indicators.
Uses yfinance (free) - no API key required.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import warnings
warnings.filterwarnings('ignore')


class MarketDataFetcher:
    """Fetches and processes market data for options scanning."""
    
    def __init__(self, tickers: list[str]):
        self.tickers = tickers
        self.price_cache = {}
        self.options_cache = {}
        
    def get_stock_data(self, ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for a ticker.
        Returns DataFrame with OHLCV + calculated indicators.
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            
            if df.empty:
                return None
            
            # Calculate moving averages
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            
            # Calculate returns
            df['Return_1D'] = df['Close'].pct_change()
            df['Return_5D'] = df['Close'].pct_change(5)
            df['Return_20D'] = df['Close'].pct_change(20)
            
            # Calculate realized volatility (20-day)
            df['RealizedVol_20D'] = df['Return_1D'].rolling(window=20).std() * np.sqrt(252)
            
            # RSI (14-day)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            self.price_cache[ticker] = df
            return df
            
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
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
                
                # Calculate approximate delta from moneyness (rough estimate)
                # Real delta would need Black-Scholes, but this is a reasonable proxy
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
            print(f"Error fetching options for {ticker}: {e}")
            return None
    
    def get_earnings_date(self, ticker: str) -> Optional[datetime]:
        """Get next earnings date for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            
            if calendar is not None and not calendar.empty:
                if 'Earnings Date' in calendar.index:
                    earnings = calendar.loc['Earnings Date']
                    if isinstance(earnings, pd.Series):
                        return pd.to_datetime(earnings.iloc[0])
                    return pd.to_datetime(earnings)
            return None
        except:
            return None
    
    def get_iv_rank(self, ticker: str) -> Optional[float]:
        """
        Calculate IV Rank (where current IV sits relative to past year).
        Returns value 0-100.
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get historical data for IV calculation
            hist = stock.history(period="1y")
            if len(hist) < 252:
                return None
            
            # Calculate historical volatility as proxy for IV
            returns = hist['Close'].pct_change().dropna()
            
            # Rolling 20-day realized vol
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252)
            rolling_vol = rolling_vol.dropna()
            
            if len(rolling_vol) < 50:
                return None
            
            current_vol = rolling_vol.iloc[-1]
            vol_min = rolling_vol.min()
            vol_max = rolling_vol.max()
            
            if vol_max == vol_min:
                return 50.0
            
            iv_rank = ((current_vol - vol_min) / (vol_max - vol_min)) * 100
            return round(iv_rank, 1)
            
        except Exception as e:
            return None
    
    def scan_all(self, progress_callback=None) -> dict:
        """
        Scan all tickers and return comprehensive data.
        """
        results = {}
        total = len(self.tickers)
        
        for i, ticker in enumerate(self.tickers):
            if progress_callback:
                progress_callback(ticker, i + 1, total)
            
            price_data = self.get_stock_data(ticker)
            if price_data is None or len(price_data) < 50:
                continue
            
            options_data = self.get_options_chain(ticker)
            iv_rank = self.get_iv_rank(ticker)
            earnings = self.get_earnings_date(ticker)
            
            # Get latest values
            latest = price_data.iloc[-1]
            
            results[ticker] = {
                'price': round(latest['Close'], 2),
                'ma20': round(latest['MA20'], 2) if pd.notna(latest['MA20']) else None,
                'ma50': round(latest['MA50'], 2) if pd.notna(latest['MA50']) else None,
                'return_1d': round(latest['Return_1D'] * 100, 2) if pd.notna(latest['Return_1D']) else None,
                'return_5d': round(latest['Return_5D'] * 100, 2) if pd.notna(latest['Return_5D']) else None,
                'return_20d': round(latest['Return_20D'] * 100, 2) if pd.notna(latest['Return_20D']) else None,
                'realized_vol': round(latest['RealizedVol_20D'] * 100, 2) if pd.notna(latest['RealizedVol_20D']) else None,
                'rsi': round(latest['RSI'], 1) if pd.notna(latest['RSI']) else None,
                'iv_rank': iv_rank,
                'earnings_date': earnings.strftime('%Y-%m-%d') if earnings else None,
                'options': options_data,
            }
        
        return results


def fetch_market_data(tickers: list[str], progress_callback=None) -> dict:
    """Convenience function to fetch all market data."""
    fetcher = MarketDataFetcher(tickers)
    return fetcher.scan_all(progress_callback)


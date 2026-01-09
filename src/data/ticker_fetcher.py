"""
Dynamic Ticker Fetcher
Uses cached S&P 500 list with Wikipedia fallback.
"""
import json
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List
import warnings
warnings.filterwarnings('ignore')


class TickerFetcher:
    """Fetches and filters quality tickers for options scanning."""
    
    def __init__(self):
        self.cache = None
        self.cache_date = None
        self.cache_duration = timedelta(days=7)  # Refresh weekly
        self.cache_file = os.path.join(os.path.dirname(__file__), '..', '..', 'sp500.json')
    
    def get_quality_tickers(self) -> List[str]:
        """
        Get quality tickers for scanning.
        Returns full S&P 500 list (all tickers).
        Uses cached file first, then Wikipedia as fallback.
        """
        # Check memory cache
        if self.cache and self.cache_date:
            if datetime.now() - self.cache_date < self.cache_duration:
                return self.cache
        
        # Try to load from cached file
        tickers = self._load_from_file()
        
        if not tickers:
            # Fallback to Wikipedia
            print("Cache file not found, fetching from Wikipedia...")
            tickers = self._get_sp500_tickers_wiki()
            
            # Save to file for next time
            if tickers:
                self._save_to_file(tickers)
        
        # Cache in memory
        self.cache = tickers
        self.cache_date = datetime.now()
        
        return tickers
    
    def _load_from_file(self) -> List[str]:
        """Load tickers from cached JSON file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    tickers = json.load(f)
                if tickers and len(tickers) > 100:  # Sanity check
                    print(f"Loaded {len(tickers)} tickers from cache")
                    return tickers
        except Exception as e:
            print(f"Error loading cache file: {e}")
        return []
    
    def _save_to_file(self, tickers: List[str]):
        """Save tickers to cached JSON file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(tickers, f, indent=2)
            print(f"Saved {len(tickers)} tickers to cache file")
        except Exception as e:
            print(f"Error saving cache file: {e}")
    
    def _get_sp500_tickers_wiki(self) -> List[str]:
        """Get S&P 500 ticker list from Wikipedia (fallback only)."""
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            
            tables = pd.read_html(r.text)
            if not tables or len(tables) == 0:
                raise ValueError("No tables found on Wikipedia page")
            
            df = tables[0]
            if 'Symbol' not in df.columns:
                raise ValueError("Symbol column not found in table")
            
            tickers = df["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist()
            
            # Clean tickers
            cleaned = []
            for ticker in tickers:
                if pd.isna(ticker):
                    continue
                ticker = str(ticker).strip()
                if ticker and len(ticker) <= 5:
                    cleaned.append(ticker)
            
            if len(cleaned) < 100:  # Sanity check
                raise ValueError(f"Only got {len(cleaned)} tickers, expected ~500")
            
            print(f"Successfully fetched {len(cleaned)} S&P 500 tickers from Wikipedia")
            return cleaned
        except Exception as e:
            print(f"Error fetching S&P 500 from Wikipedia: {e}")
            print("Using fallback ticker list...")
            return self._get_fallback_tickers()
    
    def _get_fallback_tickers(self) -> List[str]:
        """Fallback ticker list if all else fails."""
        # Extended S&P 500 subset - high quality, liquid options
        return [
            # Tech
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC",
            "NFLX", "CRM", "ADBE", "ORCL", "CSCO", "AVGO", "QCOM", "TXN", "MU", "AMAT",
            "LRCX", "KLAC", "SNPS", "CDNS", "ANSS", "INTU", "ADSK", "NOW", "TEAM", "ZM",
            # Finance
            "JPM", "BAC", "WFC", "GS", "MS", "C", "SCHW", "COF", "AXP", "V", "MA", "PYPL",
            "BLK", "BK", "USB", "TFC", "PNC", "STT", "MTB", "CFG",
            # Healthcare
            "JNJ", "UNH", "PFE", "ABBV", "TMO", "ABT", "DHR", "BMY", "AMGN", "GILD",
            "BIIB", "REGN", "VRTX", "ILMN", "ALXN", "CELG", "MYL", "ZTS", "HCA", "CI",
            # Consumer
            "WMT", "HD", "LOW", "TGT", "COST", "NKE", "SBUX", "MCD", "YUM", "CMG",
            "TJX", "ROST", "DG", "DLTR", "BBY", "GPS", "LULU", "ULTA", "NKE", "TIF",
            # Energy
            "XOM", "CVX", "SLB", "COP", "EOG", "HAL", "OXY", "MPC", "VLO", "PSX",
            # Industrials
            "BA", "CAT", "GE", "HON", "RTX", "LMT", "NOC", "GD", "TDG", "TXT",
            "DE", "EMR", "ETN", "ITW", "PH", "ROK", "SWK", "AME", "GGG", "DOV",
            # Materials
            "LIN", "APD", "ECL", "SHW", "PPG", "DD", "DOW", "FCX", "NEM", "VALE",
            # Utilities
            "NEE", "DUK", "SO", "AEP", "EXC", "SRE", "XEL", "ES", "PEG", "ED",
            # Real Estate
            "AMT", "PLD", "EQIX", "PSA", "WELL", "SPG", "O", "AVB", "EQR", "UDR",
            # Communication
            "VZ", "T", "TMUS", "CMCSA", "DIS", "NFLX", "FOX", "FOXA", "PARA", "WBD",
            # Consumer Staples
            "PG", "KO", "PEP", "CL", "MDLZ", "MO", "PM", "STZ", "TAP", "BF.B",
            # ETFs (high options volume)
            "SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP",
            "XLY", "XLB", "XLU", "XLRE", "XLC", "XME", "XRT", "XHB", "XOP", "XES",
        ]

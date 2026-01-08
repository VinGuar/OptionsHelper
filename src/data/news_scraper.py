"""
News Scraper
Fetches current news from free sources (RSS feeds, web scraping).
Provides stock-specific news with sentiment analysis for options trading.
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional
import re
import time


class NewsScraper:
    """Scrapes financial news from free sources with sentiment analysis."""
    
    # Free RSS feeds for financial news
    RSS_FEEDS = {
        'yahoo_finance': 'https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US',
        'google_news': 'https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en',
    }
    
    # Keywords for sentiment analysis
    BULLISH_KEYWORDS = [
        'surge', 'soar', 'rally', 'jump', 'gain', 'rise', 'up', 'high', 'record',
        'beat', 'exceed', 'outperform', 'upgrade', 'buy', 'bullish', 'positive',
        'growth', 'strong', 'boost', 'breakthrough', 'approval', 'win', 'success',
        'profit', 'revenue growth', 'expand', 'launch', 'partnership', 'deal'
    ]
    
    BEARISH_KEYWORDS = [
        'fall', 'drop', 'plunge', 'crash', 'sink', 'tumble', 'decline', 'down',
        'miss', 'disappoint', 'downgrade', 'sell', 'bearish', 'negative', 'weak',
        'loss', 'cut', 'layoff', 'warning', 'concern', 'risk', 'lawsuit', 'probe',
        'investigation', 'recall', 'delay', 'fail', 'reject', 'fine', 'penalty'
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.news_cache = {}
    
    def analyze_sentiment(self, text: str) -> dict:
        """
        Analyze sentiment of news text for trading signals.
        Returns sentiment score and signal.
        """
        text_lower = text.lower()
        
        bullish_count = sum(1 for word in self.BULLISH_KEYWORDS if word in text_lower)
        bearish_count = sum(1 for word in self.BEARISH_KEYWORDS if word in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return {'score': 0, 'signal': 'neutral', 'strength': 'weak'}
        
        # Score from -100 (very bearish) to +100 (very bullish)
        score = ((bullish_count - bearish_count) / total) * 100
        
        if score > 50:
            signal = 'bullish'
            strength = 'strong' if score > 75 else 'moderate'
        elif score < -50:
            signal = 'bearish'
            strength = 'strong' if score < -75 else 'moderate'
        elif score > 20:
            signal = 'slightly bullish'
            strength = 'weak'
        elif score < -20:
            signal = 'slightly bearish'
            strength = 'weak'
        else:
            signal = 'neutral'
            strength = 'weak'
        
        return {'score': round(score), 'signal': signal, 'strength': strength}
    
    def get_ticker_news(self, ticker: str, max_articles: int = 5) -> list[dict]:
        """
        Get recent news for a specific ticker with sentiment analysis.
        """
        news_items = []
        
        # Try Yahoo Finance RSS
        try:
            yahoo_url = self.RSS_FEEDS['yahoo_finance'].format(ticker=ticker)
            feed = feedparser.parse(yahoo_url)
            
            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')[:300] if entry.get('summary') else ''
                
                # Analyze sentiment
                sentiment = self.analyze_sentiment(title + ' ' + summary)
                
                news_items.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': 'Yahoo Finance',
                    'ticker': ticker,
                    'sentiment': sentiment,
                })
        except Exception as e:
            pass
        
        # Try Google News RSS
        try:
            google_url = self.RSS_FEEDS['google_news'].format(ticker=ticker)
            feed = feedparser.parse(google_url)
            
            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '')
                if any(self._similar_titles(title, n['title']) for n in news_items):
                    continue
                
                summary = entry.get('summary', '')[:300] if entry.get('summary') else ''
                sentiment = self.analyze_sentiment(title + ' ' + summary)
                    
                news_items.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': 'Google News',
                    'ticker': ticker,
                    'sentiment': sentiment,
                })
        except Exception as e:
            pass
        
        news_items = news_items[:max_articles]
        self.news_cache[ticker] = news_items
        return news_items
    
    def _similar_titles(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar (deduplication)."""
        t1 = set(title1.lower().split())
        t2 = set(title2.lower().split())
        if not t1 or not t2:
            return False
        overlap = len(t1 & t2) / min(len(t1), len(t2))
        return overlap > 0.6
    
    def get_market_news(self, max_articles: int = 10) -> list[dict]:
        """Get general market news."""
        news_items = []
        
        # MarketWatch RSS
        try:
            feed = feedparser.parse('https://feeds.marketwatch.com/marketwatch/topstories/')
            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')[:300] if entry.get('summary') else ''
                sentiment = self.analyze_sentiment(title + ' ' + summary)
                
                news_items.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': 'MarketWatch',
                    'ticker': 'MARKET',
                    'sentiment': sentiment,
                })
        except:
            pass
        
        # CNBC RSS
        try:
            feed = feedparser.parse('https://www.cnbc.com/id/100003114/device/rss/rss.html')
            for entry in feed.entries[:max_articles]:
                title = entry.get('title', '')
                if any(self._similar_titles(title, n['title']) for n in news_items):
                    continue
                    
                summary = entry.get('summary', '')[:300] if entry.get('summary') else ''
                sentiment = self.analyze_sentiment(title + ' ' + summary)
                
                news_items.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': 'CNBC',
                    'ticker': 'MARKET',
                    'sentiment': sentiment,
                })
        except:
            pass
        
        return news_items[:max_articles]
    
    def get_stock_news_with_sentiment(self, max_per_ticker: int = 3) -> list[dict]:
        """
        Get news for major stocks with sentiment analysis.
        Returns news sorted by sentiment strength for trading signals.
        """
        all_news = []
        
        # High-volume optionable stocks
        tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD',
            'NFLX', 'CRM', 'JPM', 'BAC', 'GS', 'V', 'MA', 'XOM', 'CVX',
            'SPY', 'QQQ', 'DIS', 'NKE', 'COIN', 'PLTR', 'BA', 'INTC'
        ]
        
        for ticker in tickers:
            try:
                news = self.get_ticker_news(ticker, max_articles=max_per_ticker)
                all_news.extend(news)
                time.sleep(0.1)  # Rate limiting
            except:
                continue
        
        # Sort by sentiment strength (strongest signals first)
        all_news.sort(
            key=lambda x: abs(x.get('sentiment', {}).get('score', 0)),
            reverse=True
        )
        
        return all_news
    
    def scrape_finviz_news(self, ticker: str) -> list[dict]:
        """Scrape news from Finviz with sentiment."""
        news_items = []
        
        try:
            url = f'https://finviz.com/quote.ashx?t={ticker}'
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return news_items
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_table = soup.find('table', {'id': 'news-table'})
            
            if not news_table:
                return news_items
            
            rows = news_table.find_all('tr')
            current_date = None
            
            for row in rows[:10]:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                date_cell = cells[0].text.strip()
                news_cell = cells[1]
                
                if len(date_cell) > 8:
                    current_date = date_cell.split()[0]
                
                link = news_cell.find('a')
                if link:
                    title = link.text.strip()
                    sentiment = self.analyze_sentiment(title)
                    
                    news_items.append({
                        'title': title,
                        'link': link.get('href', ''),
                        'published': current_date or '',
                        'source': 'Finviz',
                        'ticker': ticker,
                        'summary': '',
                        'sentiment': sentiment,
                    })
            
            time.sleep(0.5)
            
        except Exception as e:
            pass
        
        return news_items
    
    def categorize_news(self, news_item: dict) -> list[str]:
        """Categorize news by type."""
        title = (news_item.get('title', '') + ' ' + news_item.get('summary', '')).lower()
        
        categories = []
        
        patterns = {
            'earnings': r'earnings|quarterly|q[1-4]|revenue|profit|eps|beat|miss|guidance',
            'fda': r'fda|approval|drug|trial|clinical|phase',
            'merger_acquisition': r'merger|acquisition|acquire|buyout|deal|takeover',
            'lawsuit': r'lawsuit|legal|court|settle|sue|litigation',
            'analyst': r'upgrade|downgrade|analyst|rating|price target|pt\s',
            'dividend': r'dividend|payout|yield',
            'macro': r'fed|fomc|rate|inflation|gdp|employment|jobs',
            'guidance': r'guidance|outlook|forecast|expect|raise|lower',
        }
        
        for category, pattern in patterns.items():
            if re.search(pattern, title):
                categories.append(category)
        
        return categories if categories else ['general']


def fetch_news(tickers: list[str], include_market: bool = True) -> dict:
    """Fetch news for multiple tickers."""
    scraper = NewsScraper()
    results = {}
    
    for ticker in tickers:
        results[ticker] = scraper.get_ticker_news(ticker)
        time.sleep(0.2)
    
    if include_market:
        results['MARKET'] = scraper.get_market_news()
    
    return results

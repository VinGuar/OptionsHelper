"""
Options Flow & Whale Activity Scraper
Aggregates unusual options activity by ticker to show net sentiment.
"""
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd


class FlowScraper:
    """Scrapes unusual options flow and aggregates by ticker."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_unusual_flow(self) -> list[dict]:
        """
        Get unusual options flow AGGREGATED BY TICKER.
        Shows net sentiment for each stock, not individual contracts.
        """
        # First collect all unusual activity
        raw_flow = []
        
        tickers = [
            'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN', 'GOOGL', 'MSFT',
            'NFLX', 'BA', 'DIS', 'COIN', 'PLTR', 'SOFI', 'NIO', 'RIVN', 'GME', 'AMC',
            'JPM', 'BAC', 'GS', 'XOM', 'CVX', 'PFE', 'MRNA', 'INTC', 'MU', 'SHOP'
        ]
        
        for ticker in tickers:
            unusual = self._find_unusual_for_ticker(ticker)
            raw_flow.extend(unusual)
        
        # Now AGGREGATE by ticker
        aggregated = self._aggregate_by_ticker(raw_flow)
        
        # Sort by total premium (biggest money first)
        aggregated.sort(key=lambda x: x.get('total_premium', 0), reverse=True)
        
        return aggregated[:20]  # Top 20 tickers with unusual activity
    
    def _aggregate_by_ticker(self, raw_flow: list[dict]) -> list[dict]:
        """
        Aggregate all unusual options for a ticker into one summary.
        Shows: total call premium, total put premium, net sentiment.
        """
        ticker_data = {}
        
        for item in raw_flow:
            ticker = item['ticker']
            
            if ticker not in ticker_data:
                ticker_data[ticker] = {
                    'ticker': ticker,
                    'call_premium': 0,
                    'put_premium': 0,
                    'call_volume': 0,
                    'put_volume': 0,
                    'num_unusual_calls': 0,
                    'num_unusual_puts': 0,
                    'top_strikes': [],
                    'flags': set(),
                    'max_vol_oi': 0,
                }
            
            data = ticker_data[ticker]
            premium = item.get('premium', 0)
            volume = item.get('volume', 0)
            
            if item['type'] == 'CALL':
                data['call_premium'] += premium
                data['call_volume'] += volume
                data['num_unusual_calls'] += 1
            else:
                data['put_premium'] += premium
                data['put_volume'] += volume
                data['num_unusual_puts'] += 1
            
            # Track flags
            for flag in item.get('flags', []):
                data['flags'].add(flag)
            
            # Track max vol/oi ratio
            vol_oi = item.get('vol_oi_ratio', 0)
            if vol_oi > data['max_vol_oi']:
                data['max_vol_oi'] = vol_oi
            
            # Track top strikes
            data['top_strikes'].append({
                'type': item['type'],
                'strike': item['strike'],
                'expiry': item['expiry'],
                'premium': premium,
            })
        
        # Convert to final format
        result = []
        for ticker, data in ticker_data.items():
            total_premium = data['call_premium'] + data['put_premium']
            
            # Calculate net sentiment
            # Positive = more bullish, Negative = more bearish
            if total_premium > 0:
                call_ratio = data['call_premium'] / total_premium
                put_ratio = data['put_premium'] / total_premium
            else:
                call_ratio = 0.5
                put_ratio = 0.5
            
            # Determine sentiment
            if call_ratio > 0.7:
                sentiment = 'very bullish'
                sentiment_score = 2
            elif call_ratio > 0.55:
                sentiment = 'bullish'
                sentiment_score = 1
            elif put_ratio > 0.7:
                sentiment = 'very bearish'
                sentiment_score = -2
            elif put_ratio > 0.55:
                sentiment = 'bearish'
                sentiment_score = -1
            else:
                sentiment = 'mixed'
                sentiment_score = 0
            
            # Get top strike by premium
            top_strikes = sorted(data['top_strikes'], key=lambda x: x['premium'], reverse=True)[:3]
            
            # Build summary flags
            flags = list(data['flags'])[:4]  # Limit flags
            
            result.append({
                'ticker': ticker,
                'total_premium': total_premium,
                'call_premium': data['call_premium'],
                'put_premium': data['put_premium'],
                'call_volume': data['call_volume'],
                'put_volume': data['put_volume'],
                'num_calls': data['num_unusual_calls'],
                'num_puts': data['num_unusual_puts'],
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'call_ratio': round(call_ratio * 100),
                'put_ratio': round(put_ratio * 100),
                'max_vol_oi': round(data['max_vol_oi'], 1),
                'top_strikes': top_strikes,
                'flags': flags,
            })
        
        return result
    
    def _find_unusual_for_ticker(self, ticker: str) -> list[dict]:
        """Find unusual options activity for a single ticker."""
        unusual = []
        
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            if not expirations:
                return unusual
            
            info = stock.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 100)
            
            # Check first 3 expirations
            for exp in expirations[:3]:
                try:
                    chain = stock.option_chain(exp)
                    
                    # Analyze calls
                    if not chain.calls.empty:
                        unusual.extend(self._analyze_chain(
                            chain.calls, ticker, 'CALL', exp, current_price
                        ))
                    
                    # Analyze puts
                    if not chain.puts.empty:
                        unusual.extend(self._analyze_chain(
                            chain.puts, ticker, 'PUT', exp, current_price
                        ))
                        
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        return unusual
    
    def _analyze_chain(self, df: pd.DataFrame, ticker: str, opt_type: str, 
                       expiry: str, current_price: float) -> list[dict]:
        """Analyze options chain for unusual activity."""
        unusual = []
        
        for _, row in df.iterrows():
            try:
                volume = row.get('volume', 0)
                oi = row.get('openInterest', 1)
                last_price = row.get('lastPrice', 0)
                strike = row.get('strike', 0)
                
                if pd.isna(volume) or volume < 1000:
                    continue
                if pd.isna(oi):
                    oi = 1
                
                vol_oi_ratio = volume / max(oi, 1)
                premium = volume * last_price * 100
                
                # Calculate moneyness
                if opt_type == 'CALL':
                    moneyness = (strike - current_price) / current_price * 100
                else:
                    moneyness = (current_price - strike) / current_price * 100
                
                # UNUSUAL SCORE
                unusual_score = 0
                flags = []
                
                if vol_oi_ratio > 5:
                    unusual_score += 40
                    flags.append('VOL>>OI')
                elif vol_oi_ratio > 3:
                    unusual_score += 25
                    flags.append('High Vol/OI')
                elif vol_oi_ratio > 2:
                    unusual_score += 10
                
                if premium > 5000000:
                    unusual_score += 35
                    flags.append('WHALE $5M+')
                elif premium > 1000000:
                    unusual_score += 25
                    flags.append('$1M+')
                elif premium > 500000:
                    unusual_score += 15
                
                if moneyness > 5:
                    unusual_score += 15
                    flags.append('OTM Bet')
                
                exp_date = datetime.strptime(expiry, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
                if dte <= 7:
                    unusual_score += 10
                    flags.append('Weekly')
                
                # Only include if truly unusual
                if unusual_score >= 25 and premium > 100000:
                    unusual.append({
                        'ticker': ticker,
                        'type': opt_type,
                        'strike': f"${strike:.0f}",
                        'expiry': expiry,
                        'dte': dte,
                        'volume': int(volume),
                        'open_interest': int(oi),
                        'vol_oi_ratio': round(vol_oi_ratio, 1),
                        'premium': premium,
                        'unusual_score': unusual_score,
                        'flags': flags,
                        'moneyness': round(moneyness, 1),
                    })
                    
            except Exception:
                continue
        
        return unusual
    
    def get_most_active_options(self) -> list[dict]:
        """Get most active options by volume."""
        active = []
        tickers = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN']
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                expirations = stock.options
                if not expirations:
                    continue
                
                total_volume = 0
                for exp in expirations[:2]:
                    try:
                        chain = stock.option_chain(exp)
                        call_vol = chain.calls['volume'].sum()
                        put_vol = chain.puts['volume'].sum()
                        if not pd.isna(call_vol):
                            total_volume += call_vol
                        if not pd.isna(put_vol):
                            total_volume += put_vol
                    except:
                        pass
                
                active.append({
                    'ticker': ticker,
                    'volume': int(total_volume) if not pd.isna(total_volume) else 0,
                })
            except:
                continue
        
        active.sort(key=lambda x: x['volume'], reverse=True)
        return active[:8]
    
    def get_market_movers(self) -> dict:
        """Get top gainers and losers."""
        gainers = []
        losers = []
        
        tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD',
            'NFLX', 'CRM', 'JPM', 'BAC', 'GS', 'V', 'MA', 'XOM', 'CVX'
        ]
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='2d')
                
                if len(hist) < 2:
                    continue
                
                prev_close = hist['Close'].iloc[-2]
                current = hist['Close'].iloc[-1]
                change_pct = ((current - prev_close) / prev_close) * 100
                
                item = {
                    'ticker': ticker,
                    'price': current,
                    'change_pct': change_pct,
                }
                
                if change_pct > 0:
                    gainers.append(item)
                else:
                    losers.append(item)
                    
            except:
                continue
        
        gainers.sort(key=lambda x: x['change_pct'], reverse=True)
        losers.sort(key=lambda x: x['change_pct'])
        
        return {
            'gainers': gainers[:5],
            'losers': losers[:5],
        }
    
    def get_fear_greed_index(self) -> dict:
        """
        Get the Fear & Greed Index by scraping from feargreedmeter.com
        Falls back to CNN or calculated values if scraping fails.
        """
        
        # Try to scrape from feargreedmeter.com first
        try:
            result = self._scrape_fear_greed_meter()
            if result:
                return result
        except Exception as e:
            print(f"feargreedmeter.com scrape failed: {e}")
        
        # Fallback: try CNN
        try:
            result = self._scrape_cnn_fear_greed()
            if result:
                return result
        except Exception as e:
            print(f"CNN scrape failed: {e}")
        
        # Final fallback: calculate ourselves
        return self._calculate_fear_greed_fallback()
    
    def _scrape_fear_greed_meter(self) -> dict:
        """Scrape Fear & Greed Index from feargreedmeter.com"""
        import re
        
        url = 'https://feargreedmeter.com/'
        response = self.session.get(url, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # The site shows the value prominently - look for it
        # Try to find the main score value
        text = soup.get_text()
        
        # Look for patterns like "47" followed by "Neutral" or similar
        # The page structure shows: value, then label
        patterns = [
            r'(\d{1,2})\s*(?:Neutral|Fear|Greed|Extreme Fear|Extreme Greed)',
            r'Now\s*(\d{1,2})',
        ]
        
        value = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                break
        
        # Also try to find in script tags (often JSON data)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for fear greed value in JSON
                match = re.search(r'"(?:value|score|index)":\s*(\d{1,2})', script.string)
                if match:
                    value = int(match.group(1))
                    break
        
        if value is None:
            return None
        
        # Determine label
        if value >= 75:
            label = 'Extreme Greed'
        elif value >= 55:
            label = 'Greed'
        elif value >= 45:
            label = 'Neutral'
        elif value >= 25:
            label = 'Fear'
        else:
            label = 'Extreme Fear'
        
        # Get VIX for additional info
        try:
            vix = yf.Ticker('^VIX')
            vix_hist = vix.history(period='1d')
            vix_value = round(vix_hist['Close'].iloc[-1], 2) if not vix_hist.empty else None
        except:
            vix_value = None
        
        return {
            'value': value,
            'label': label,
            'vix': vix_value,
            'source': 'feargreedmeter.com',
        }
    
    def _scrape_cnn_fear_greed(self) -> dict:
        """Scrape Fear & Greed Index from CNN"""
        import re
        
        url = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # CNN API returns score directly
                if 'fear_and_greed' in data:
                    fg = data['fear_and_greed']
                    value = round(fg.get('score', 50))
                    
                    if value >= 75:
                        label = 'Extreme Greed'
                    elif value >= 55:
                        label = 'Greed'
                    elif value >= 45:
                        label = 'Neutral'
                    elif value >= 25:
                        label = 'Fear'
                    else:
                        label = 'Extreme Fear'
                    
                    return {
                        'value': value,
                        'label': label,
                        'source': 'CNN',
                    }
        except:
            pass
        
        return None
    
    def _calculate_fear_greed_fallback(self) -> dict:
        """Calculate a simple Fear & Greed estimate as fallback"""
        try:
            # Simple calculation based on VIX and SPY momentum
            vix = yf.Ticker('^VIX')
            spy = yf.Ticker('SPY')
            
            vix_hist = vix.history(period='1mo')
            spy_hist = spy.history(period='6mo')
            
            scores = []
            
            # VIX score
            if not vix_hist.empty:
                current_vix = vix_hist['Close'].iloc[-1]
                if current_vix <= 15:
                    vix_score = 80
                elif current_vix >= 30:
                    vix_score = 20
                else:
                    vix_score = 80 - ((current_vix - 15) / 15 * 60)
                scores.append(vix_score)
            
            # Momentum score
            if len(spy_hist) >= 125:
                current = spy_hist['Close'].iloc[-1]
                ma125 = spy_hist['Close'].rolling(125).mean().iloc[-1]
                momentum = ((current - ma125) / ma125) * 100
                
                if momentum >= 5:
                    mom_score = 80
                elif momentum <= -5:
                    mom_score = 20
                else:
                    mom_score = 50 + (momentum / 5 * 30)
                scores.append(mom_score)
            
            if scores:
                value = round(sum(scores) / len(scores))
            else:
                value = 50
            
            if value >= 75:
                label = 'Extreme Greed'
            elif value >= 55:
                label = 'Greed'
            elif value >= 45:
                label = 'Neutral'
            elif value >= 25:
                label = 'Fear'
            else:
                label = 'Extreme Fear'
            
            return {
                'value': value,
                'label': label,
                'source': 'Calculated (fallback)',
                'vix': round(current_vix, 2) if not vix_hist.empty else None,
            }
            
        except Exception as e:
            return {
                'value': 50,
                'label': 'Neutral',
                'source': 'Default',
                'error': str(e)
            }


    def get_market_indices(self) -> dict:
        """Get major market index data."""
        indices = {}
        
        index_map = {
            'spy': ('SPY', 'S&P 500'),
            'dow': ('^DJI', 'DOW'),
            'nasdaq': ('^IXIC', 'NASDAQ'),
            'vix': ('^VIX', 'VIX'),
        }
        
        for key, (ticker, name) in index_map.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='2d')
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change = current - prev
                    change_pct = (change / prev) * 100
                    
                    indices[key] = {
                        'name': name,
                        'price': round(current, 2),
                        'change': round(change, 2),
                        'change_pct': round(change_pct, 2),
                    }
            except:
                pass
        
        return indices
    
    def get_sector_performance(self) -> list[dict]:
        """Get sector ETF performance."""
        sectors = [
            ('XLK', 'Technology'),
            ('XLF', 'Financials'),
            ('XLE', 'Energy'),
            ('XLV', 'Healthcare'),
            ('XLI', 'Industrials'),
            ('XLY', 'Consumer Disc'),
            ('XLP', 'Consumer Staples'),
            ('XLU', 'Utilities'),
            ('XLRE', 'Real Estate'),
            ('XLB', 'Materials'),
        ]
        
        results = []
        for ticker, name in sectors:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='2d')
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    
                    results.append({
                        'ticker': ticker,
                        'name': name,
                        'change_pct': round(change_pct, 2),
                    })
            except:
                pass
        
        results.sort(key=lambda x: x['change_pct'], reverse=True)
        return results
    
    def get_upcoming_events(self) -> list[dict]:
        """Get upcoming market events (static for now, could be scraped)."""
        from datetime import datetime, timedelta
        
        # Common recurring events
        events = []
        today = datetime.now()
        
        # Find next FOMC meeting (typically every 6 weeks)
        # This is simplified - in production you'd scrape the Fed calendar
        fomc_dates = [
            ('2026-01-28', 'Fed Meeting Day 1'),
            ('2026-01-29', 'Fed Meeting Day 2 + Rate Decision'),
            ('2026-03-17', 'Fed Meeting Day 1'),
            ('2026-03-18', 'Fed Meeting Day 2 + Rate Decision'),
        ]
        
        for date_str, name in fomc_dates:
            event_date = datetime.strptime(date_str, '%Y-%m-%d')
            if event_date >= today:
                events.append({
                    'date': date_str,
                    'name': name,
                    'type': 'fomc',
                })
        
        # Jobs report (first Friday of month)
        events.append({
            'date': '2026-02-07',
            'name': 'Jobs Report',
            'type': 'economic',
        })
        
        # CPI (usually mid-month)
        events.append({
            'date': '2026-01-15',
            'name': 'CPI Report',
            'type': 'economic',
        })
        
        events.sort(key=lambda x: x['date'])
        return events[:6]
    
    def get_earnings_calendar(self, filter_type: str = 'this-week') -> list[dict]:
        """
        Get upcoming earnings calendar.
        Uses Yahoo Finance to get earnings dates for major tickers.
        """
        earnings = []
        today = datetime.now()
        
        # Define date ranges based on filter
        if filter_type == 'this-week':
            start_date = today
            end_date = today + timedelta(days=7)
        elif filter_type == 'next-week':
            start_date = today + timedelta(days=7)
            end_date = today + timedelta(days=14)
        else:
            # Watchlist - would need user's watchlist
            start_date = today
            end_date = today + timedelta(days=14)
        
        # Major tickers to check for earnings
        tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD',
            'NFLX', 'CRM', 'JPM', 'BAC', 'GS', 'V', 'MA', 'XOM', 'CVX',
            'JNJ', 'UNH', 'PFE', 'WMT', 'HD', 'MCD', 'NKE', 'SBUX',
            'KO', 'PEP', 'COST', 'DIS', 'PYPL', 'INTC', 'QCOM', 'AVGO',
            'ADBE', 'NOW', 'SNOW', 'NET', 'DDOG', 'ZS', 'CRWD', 'PANW'
        ]
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                calendar = stock.calendar
                
                if calendar is None or calendar.empty:
                    continue
                
                # Get earnings date
                earnings_date = None
                if 'Earnings Date' in calendar.index:
                    earnings_date = calendar.loc['Earnings Date']
                    if isinstance(earnings_date, pd.Series):
                        earnings_date = earnings_date.iloc[0]
                
                if earnings_date is None:
                    continue
                
                # Convert to datetime if needed
                if hasattr(earnings_date, 'to_pydatetime'):
                    earnings_date = earnings_date.to_pydatetime()
                elif isinstance(earnings_date, str):
                    earnings_date = datetime.strptime(earnings_date[:10], '%Y-%m-%d')
                
                # Check if in range
                if start_date <= earnings_date <= end_date:
                    # Get EPS estimate
                    eps_estimate = None
                    if 'Earnings Average' in calendar.index:
                        eps_estimate = calendar.loc['Earnings Average']
                        if isinstance(eps_estimate, pd.Series):
                            eps_estimate = eps_estimate.iloc[0]
                    
                    # Determine time (BMO = before market open, AMC = after market close)
                    # This is a simplification - actual time would need to be scraped
                    time = 'amc'  # Default to after close
                    
                    earnings.append({
                        'ticker': ticker,
                        'date': earnings_date.strftime('%Y-%m-%d'),
                        'time': time,
                        'estimate': f"{eps_estimate:.2f}" if eps_estimate else None,
                    })
                    
            except Exception:
                continue
        
        # Sort by date
        earnings.sort(key=lambda x: x['date'])
        
        return earnings


def get_flow_data() -> dict:
    """Get all flow data in one call."""
    scraper = FlowScraper()
    
    return {
        'unusual_flow': scraper.get_unusual_flow(),
        'most_active': scraper.get_most_active_options(),
        'movers': scraper.get_market_movers(),
        'sentiment': scraper.get_fear_greed_index(),
        'indices': scraper.get_market_indices(),
        'sectors': scraper.get_sector_performance(),
        'events': scraper.get_upcoming_events(),
        'timestamp': datetime.now().isoformat(),
    }

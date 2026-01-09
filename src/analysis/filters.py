"""
Edge Detection Filters
Implements the trend-following debit spread edge filters.
These are the NON-NEGOTIABLE rules that determine valid trade candidates.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class FilterResult:
    """Result of applying filters to a ticker."""
    ticker: str
    passed: bool
    direction: Optional[str]  # 'BULLISH' or 'BEARISH'
    reasons: list[str]
    scores: dict
    

class EdgeFilters:
    """
    Implements Edge #1: Trend-Following Debit Spread
    
    Core hypothesis: When a liquid large-cap stock is in a strong trend
    and IV is not extreme, a 30-45 DTE debit spread has positive expectancy.
    """
    
    # Filter thresholds (from config, hardcoded for clarity)
    LIQUIDITY = {
        'max_spread_pct': 0.08,      # Bid-ask spread <= 8% of mid
        'min_open_interest': 500,
        'min_daily_volume': 200,
    }
    
    TREND = {
        'ma_short': 20,
        'ma_long': 50,
        'min_return_pct': 0.03,      # 3% move confirms trend
    }
    
    VOLATILITY = {
        'iv_rank_min': 20,
        'iv_rank_max': 60,
    }
    
    EVENTS = {
        'min_days_to_earnings': 10,
    }
    
    def __init__(self):
        pass
    
    def check_trend(self, data: dict) -> tuple[bool, str, list[str]]:
        """
        Check if stock is in a valid trend.
        Returns (passed, direction, reasons).
        
        Rules:
        - Price above/below 20-day MA
        - 20-day MA above/below 50-day MA  
        - 20-day return >= 3% (bullish) or <= -3% (bearish)
        """
        reasons = []
        
        price = data.get('price')
        ma20 = data.get('ma20')
        ma50 = data.get('ma50')
        return_20d = data.get('return_20d')
        
        # Check for missing data
        if any(v is None for v in [price, ma20, ma50, return_20d]):
            return False, None, ['Missing price/MA data']
        
        # Check bullish trend
        bullish_checks = [
            price > ma20,
            ma20 > ma50,
            return_20d >= self.TREND['min_return_pct'] * 100,  # return_20d is in %
        ]
        
        # Check bearish trend
        bearish_checks = [
            price < ma20,
            ma20 < ma50,
            return_20d <= -self.TREND['min_return_pct'] * 100,
        ]
        
        if all(bullish_checks):
            reasons.append(f"BULLISH: Price ${price} > MA20 ${ma20} > MA50 ${ma50}")
            reasons.append(f"20D return: +{return_20d:.1f}%")
            return True, 'BULLISH', reasons
        
        if all(bearish_checks):
            reasons.append(f"BEARISH: Price ${price} < MA20 ${ma20} < MA50 ${ma50}")
            reasons.append(f"20D return: {return_20d:.1f}%")
            return True, 'BEARISH', reasons
        
        # No clear trend
        reasons.append(f"No clear trend: Price ${price}, MA20 ${ma20}, MA50 ${ma50}")
        reasons.append(f"20D return: {return_20d:.1f}% (need ±{self.TREND['min_return_pct']*100}%)")
        return False, None, reasons
    
    def check_volatility(self, data: dict) -> tuple[bool, list[str]]:
        """
        Check if IV rank is in acceptable range.
        
        Rules:
        - IV Rank between 20 and 60
        - Below 20: options too cheap, move may be done
        - Above 60: IV crush risk
        """
        reasons = []
        iv_rank = data.get('iv_rank')
        
        if iv_rank is None:
            reasons.append("IV Rank: Unknown (using realized vol proxy)")
            return True, reasons  # Allow if we can't calculate
        
        if iv_rank < self.VOLATILITY['iv_rank_min']:
            reasons.append(f"IV Rank {iv_rank:.0f} < {self.VOLATILITY['iv_rank_min']} (too low)")
            return False, reasons
        
        if iv_rank > self.VOLATILITY['iv_rank_max']:
            reasons.append(f"IV Rank {iv_rank:.0f} > {self.VOLATILITY['iv_rank_max']} (IV crush risk)")
            return False, reasons
        
        reasons.append(f"IV Rank: {iv_rank:.0f} (acceptable range)")
        return True, reasons
    
    def check_events(self, data: dict) -> tuple[bool, list[str]]:
        """
        Check for upcoming events that could cause binary moves.
        
        Rules:
        - No earnings within 10 days
        """
        reasons = []
        earnings_date = data.get('earnings_date')
        
        if earnings_date is None:
            reasons.append("Earnings: Unknown date")
            return True, reasons  # Allow if unknown
        
        try:
            earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
            days_to_earnings = (earnings_dt - datetime.now()).days
            
            if 0 <= days_to_earnings <= self.EVENTS['min_days_to_earnings']:
                reasons.append(f"Earnings in {days_to_earnings} days - SKIP")
                return False, reasons
            
            if days_to_earnings > 0:
                reasons.append(f"Earnings in {days_to_earnings} days (OK)")
            else:
                reasons.append(f"Earnings passed {-days_to_earnings} days ago")
                
        except:
            reasons.append("Earnings: Could not parse date")
        
        return True, reasons
    
    def check_liquidity(self, data: dict) -> tuple[bool, list[str]]:
        """
        Check options chain liquidity.
        
        Rules:
        - Bid-ask spread <= 8% of mid
        - Open interest >= 500
        - Daily volume >= 200
        """
        reasons = []
        options = data.get('options')
        
        if options is None:
            reasons.append("No options data available")
            return False, reasons
        
        calls = options.get('calls')
        puts = options.get('puts')
        
        if calls is None or puts is None or calls.empty or puts.empty:
            reasons.append("Empty options chain")
            return False, reasons
        
        # Check ATM options (closest to current price)
        current_price = options.get('current_price', 0)
        
        # Find ATM call
        calls_sorted = calls.copy()
        calls_sorted['dist'] = abs(calls_sorted['strike'] - current_price)
        atm_call = calls_sorted.nsmallest(1, 'dist').iloc[0] if not calls_sorted.empty else None
        
        # Find ATM put
        puts_sorted = puts.copy()
        puts_sorted['dist'] = abs(puts_sorted['strike'] - current_price)
        atm_put = puts_sorted.nsmallest(1, 'dist').iloc[0] if not puts_sorted.empty else None
        
        if atm_call is None or atm_put is None:
            reasons.append("Could not find ATM options")
            return False, reasons
        
        # Check spread percentage
        avg_spread_pct = (atm_call.get('spread_pct', 1) + atm_put.get('spread_pct', 1)) / 2
        if pd.isna(avg_spread_pct):
            avg_spread_pct = 1
            
        if avg_spread_pct > self.LIQUIDITY['max_spread_pct']:
            reasons.append(f"Spread {avg_spread_pct*100:.1f}% > {self.LIQUIDITY['max_spread_pct']*100}% (too wide)")
            return False, reasons
        
        # Check open interest
        avg_oi = (atm_call.get('openInterest', 0) + atm_put.get('openInterest', 0)) / 2
        if avg_oi < self.LIQUIDITY['min_open_interest']:
            reasons.append(f"Open Interest {avg_oi:.0f} < {self.LIQUIDITY['min_open_interest']}")
            return False, reasons
        
        # Check volume
        avg_vol = (atm_call.get('volume', 0) + atm_put.get('volume', 0)) / 2
        if pd.isna(avg_vol):
            avg_vol = 0
        if avg_vol < self.LIQUIDITY['min_daily_volume']:
            reasons.append(f"Volume {avg_vol:.0f} < {self.LIQUIDITY['min_daily_volume']} (low liquidity)")
            # This is a soft filter - warn but don't reject
            reasons.append("WARNING: Low volume, may have fill issues")
        
        reasons.append(f"Liquidity OK: Spread {avg_spread_pct*100:.1f}%, OI {avg_oi:.0f}")
        return True, reasons
    
    def apply_all_filters(self, ticker: str, data: dict) -> FilterResult:
        """
        Apply all filters to a ticker and return result.
        """
        all_reasons = []
        scores = {}
        
        # 1. Trend filter (most important)
        trend_passed, direction, trend_reasons = self.check_trend(data)
        all_reasons.extend(trend_reasons)
        scores['trend'] = 1 if trend_passed else 0
        
        if not trend_passed:
            return FilterResult(
                ticker=ticker,
                passed=False,
                direction=None,
                reasons=all_reasons,
                scores=scores
            )
        
        # 2. Volatility filter
        vol_passed, vol_reasons = self.check_volatility(data)
        all_reasons.extend(vol_reasons)
        scores['volatility'] = 1 if vol_passed else 0
        
        if not vol_passed:
            return FilterResult(
                ticker=ticker,
                passed=False,
                direction=direction,
                reasons=all_reasons,
                scores=scores
            )
        
        # 3. Event filter
        event_passed, event_reasons = self.check_events(data)
        all_reasons.extend(event_reasons)
        scores['events'] = 1 if event_passed else 0
        
        if not event_passed:
            return FilterResult(
                ticker=ticker,
                passed=False,
                direction=direction,
                reasons=all_reasons,
                scores=scores
            )
        
        # 4. Liquidity filter
        liq_passed, liq_reasons = self.check_liquidity(data)
        all_reasons.extend(liq_reasons)
        scores['liquidity'] = 1 if liq_passed else 0
        
        # Calculate overall score
        scores['total'] = sum(scores.values())
        
        return FilterResult(
            ticker=ticker,
            passed=liq_passed,  # All must pass
            direction=direction,
            reasons=all_reasons,
            scores=scores
        )


def scan_for_edges(market_data: dict) -> list[FilterResult]:
    """
    Scan all tickers and return those that pass all filters.
    """
    filters = EdgeFilters()
    results = []
    
    for ticker, data in market_data.items():
        result = filters.apply_all_filters(ticker, data)
        results.append(result)
    
    # Sort by total score, then by passed status
    results.sort(key=lambda x: (x.passed, x.scores.get('total', 0)), reverse=True)
    
    return results



"""
Candidate Generator
Generates specific option spread candidates for tickers that pass filters.
Outputs exact strikes, prices, and risk parameters.
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class SpreadCandidate:
    """A specific debit spread trade candidate."""
    ticker: str
    direction: str              # 'BULLISH' or 'BEARISH'
    spread_type: str            # 'CALL_DEBIT' or 'PUT_DEBIT'
    
    # Long leg (buy)
    long_strike: float
    long_bid: float
    long_ask: float
    long_delta: float
    
    # Short leg (sell)
    short_strike: float
    short_bid: float
    short_ask: float
    short_delta: float
    
    # Spread details
    expiration: str
    dte: int
    current_price: float
    
    # Calculated values
    spread_width: float         # Difference between strikes
    max_debit: float            # Worst case entry (long ask - short bid)
    mid_debit: float            # Mid price entry
    max_profit: float           # spread_width - debit
    max_loss: float             # debit paid
    breakeven: float            # Long strike ± debit
    risk_reward: float          # max_profit / max_loss
    
    # Quality metrics
    spread_pct: float           # Bid-ask spread as % of mid
    open_interest: int
    
    def to_dict(self) -> dict:
        return {
            'ticker': self.ticker,
            'direction': self.direction,
            'type': self.spread_type,
            'expiration': self.expiration,
            'dte': self.dte,
            'current_price': self.current_price,
            'long_strike': self.long_strike,
            'short_strike': self.short_strike,
            'spread_width': self.spread_width,
            'mid_debit': round(self.mid_debit, 2),
            'max_debit': round(self.max_debit, 2),
            'max_profit': round(self.max_profit, 2),
            'max_loss': round(self.max_loss, 2),
            'breakeven': round(self.breakeven, 2),
            'risk_reward': round(self.risk_reward, 2),
            'long_delta': round(self.long_delta, 2),
            'short_delta': round(self.short_delta, 2),
        }


class CandidateGenerator:
    """
    Generates debit spread candidates from options chains.
    
    Target structure:
    - Buy option: ~0.35 delta
    - Sell option: ~0.15-0.20 delta
    - DTE: 30-45 days
    - Max debit: 30% of spread width
    """
    
    # Target parameters
    LONG_DELTA_TARGET = 0.35
    SHORT_DELTA_TARGET = 0.175
    DELTA_TOLERANCE = 0.10
    MAX_DEBIT_PCT = 0.30
    
    def __init__(self):
        pass
    
    def _estimate_delta(self, strike: float, current_price: float, 
                        option_type: str, dte: int) -> float:
        """
        Estimate delta from moneyness (simplified).
        Real delta needs Black-Scholes, but this is a reasonable proxy.
        """
        moneyness = strike / current_price
        
        # Time factor (more time = deltas closer to 0.5)
        time_factor = min(dte / 45, 1.0)
        
        if option_type == 'call':
            if moneyness <= 0.95:  # Deep ITM
                return 0.85 + (0.15 * time_factor)
            elif moneyness <= 1.0:  # Slightly ITM
                return 0.55 + (0.15 * (1 - moneyness) / 0.05)
            elif moneyness <= 1.05:  # ATM to slightly OTM
                return 0.50 - (0.20 * (moneyness - 1) / 0.05)
            elif moneyness <= 1.10:  # OTM
                return 0.30 - (0.15 * (moneyness - 1.05) / 0.05)
            else:  # Deep OTM
                return max(0.05, 0.15 - (0.10 * (moneyness - 1.10) / 0.10))
        else:  # put
            if moneyness >= 1.05:  # Deep ITM
                return -0.85 - (0.15 * time_factor)
            elif moneyness >= 1.0:  # Slightly ITM
                return -0.55 - (0.15 * (moneyness - 1) / 0.05)
            elif moneyness >= 0.95:  # ATM to slightly OTM
                return -0.50 + (0.20 * (1 - moneyness) / 0.05)
            elif moneyness >= 0.90:  # OTM
                return -0.30 + (0.15 * (0.95 - moneyness) / 0.05)
            else:  # Deep OTM
                return max(-0.15, -0.15 + (0.10 * (0.90 - moneyness) / 0.10))
    
    def generate_call_spread(self, ticker: str, options_data: dict, 
                              current_price: float) -> Optional[SpreadCandidate]:
        """
        Generate a bullish call debit spread.
        Buy lower strike call, sell higher strike call.
        """
        calls = options_data.get('calls')
        if calls is None or calls.empty:
            return None
        
        expiration = options_data.get('expiration')
        dte = options_data.get('dte', 30)
        
        # Filter to valid options (has bid/ask)
        valid = calls[(calls['bid'] > 0) & (calls['ask'] > 0)].copy()
        if len(valid) < 2:
            return None
        
        # Calculate estimated deltas
        valid['est_delta'] = valid['strike'].apply(
            lambda s: self._estimate_delta(s, current_price, 'call', dte)
        )
        
        # Find long leg (target ~0.35 delta)
        valid['long_dist'] = abs(valid['est_delta'] - self.LONG_DELTA_TARGET)
        long_candidates = valid[valid['long_dist'] <= self.DELTA_TOLERANCE]
        
        if long_candidates.empty:
            # Fallback: get closest
            long_candidates = valid.nsmallest(3, 'long_dist')
        
        # Find short leg (target ~0.175 delta, must be higher strike)
        valid['short_dist'] = abs(valid['est_delta'] - self.SHORT_DELTA_TARGET)
        
        best_spread = None
        best_score = -999
        
        for _, long_row in long_candidates.iterrows():
            # Short leg must be higher strike
            short_candidates = valid[
                (valid['strike'] > long_row['strike']) &
                (valid['short_dist'] <= self.DELTA_TOLERANCE * 1.5)
            ]
            
            if short_candidates.empty:
                continue
            
            for _, short_row in short_candidates.iterrows():
                # Calculate spread metrics
                spread_width = short_row['strike'] - long_row['strike']
                max_debit = long_row['ask'] - short_row['bid']
                mid_debit = ((long_row['ask'] + long_row['bid']) / 2 - 
                            (short_row['ask'] + short_row['bid']) / 2)
                
                if spread_width <= 0 or max_debit <= 0:
                    continue
                
                # Check debit constraint
                debit_pct = max_debit / spread_width
                if debit_pct > self.MAX_DEBIT_PCT:
                    continue
                
                max_profit = spread_width - mid_debit
                risk_reward = max_profit / mid_debit if mid_debit > 0 else 0
                
                # Score: prefer better risk/reward and tighter spreads
                avg_spread_pct = (
                    (long_row['ask'] - long_row['bid']) / long_row['ask'] +
                    (short_row['ask'] - short_row['bid']) / short_row['ask']
                ) / 2
                
                score = risk_reward - (avg_spread_pct * 5)
                
                if score > best_score:
                    best_score = score
                    best_spread = SpreadCandidate(
                        ticker=ticker,
                        direction='BULLISH',
                        spread_type='CALL_DEBIT',
                        long_strike=long_row['strike'],
                        long_bid=long_row['bid'],
                        long_ask=long_row['ask'],
                        long_delta=long_row['est_delta'],
                        short_strike=short_row['strike'],
                        short_bid=short_row['bid'],
                        short_ask=short_row['ask'],
                        short_delta=short_row['est_delta'],
                        expiration=expiration,
                        dte=dte,
                        current_price=current_price,
                        spread_width=spread_width,
                        max_debit=max_debit,
                        mid_debit=mid_debit,
                        max_profit=max_profit,
                        max_loss=mid_debit,
                        breakeven=long_row['strike'] + mid_debit,
                        risk_reward=risk_reward,
                        spread_pct=avg_spread_pct,
                        open_interest=int(long_row.get('openInterest', 0) + 
                                         short_row.get('openInterest', 0)),
                    )
        
        return best_spread
    
    def generate_put_spread(self, ticker: str, options_data: dict,
                            current_price: float) -> Optional[SpreadCandidate]:
        """
        Generate a bearish put debit spread.
        Buy higher strike put, sell lower strike put.
        """
        puts = options_data.get('puts')
        if puts is None or puts.empty:
            return None
        
        expiration = options_data.get('expiration')
        dte = options_data.get('dte', 30)
        
        # Filter to valid options
        valid = puts[(puts['bid'] > 0) & (puts['ask'] > 0)].copy()
        if len(valid) < 2:
            return None
        
        # Calculate estimated deltas (negative for puts)
        valid['est_delta'] = valid['strike'].apply(
            lambda s: self._estimate_delta(s, current_price, 'put', dte)
        )
        
        # For puts, we want |delta| close to targets
        valid['long_dist'] = abs(abs(valid['est_delta']) - self.LONG_DELTA_TARGET)
        valid['short_dist'] = abs(abs(valid['est_delta']) - self.SHORT_DELTA_TARGET)
        
        long_candidates = valid[valid['long_dist'] <= self.DELTA_TOLERANCE]
        if long_candidates.empty:
            long_candidates = valid.nsmallest(3, 'long_dist')
        
        best_spread = None
        best_score = -999
        
        for _, long_row in long_candidates.iterrows():
            # Short leg must be lower strike for put spread
            short_candidates = valid[
                (valid['strike'] < long_row['strike']) &
                (valid['short_dist'] <= self.DELTA_TOLERANCE * 1.5)
            ]
            
            if short_candidates.empty:
                continue
            
            for _, short_row in short_candidates.iterrows():
                spread_width = long_row['strike'] - short_row['strike']
                max_debit = long_row['ask'] - short_row['bid']
                mid_debit = ((long_row['ask'] + long_row['bid']) / 2 -
                            (short_row['ask'] + short_row['bid']) / 2)
                
                if spread_width <= 0 or max_debit <= 0:
                    continue
                
                debit_pct = max_debit / spread_width
                if debit_pct > self.MAX_DEBIT_PCT:
                    continue
                
                max_profit = spread_width - mid_debit
                risk_reward = max_profit / mid_debit if mid_debit > 0 else 0
                
                avg_spread_pct = (
                    (long_row['ask'] - long_row['bid']) / long_row['ask'] +
                    (short_row['ask'] - short_row['bid']) / short_row['ask']
                ) / 2
                
                score = risk_reward - (avg_spread_pct * 5)
                
                if score > best_score:
                    best_score = score
                    best_spread = SpreadCandidate(
                        ticker=ticker,
                        direction='BEARISH',
                        spread_type='PUT_DEBIT',
                        long_strike=long_row['strike'],
                        long_bid=long_row['bid'],
                        long_ask=long_row['ask'],
                        long_delta=long_row['est_delta'],
                        short_strike=short_row['strike'],
                        short_bid=short_row['bid'],
                        short_ask=short_row['ask'],
                        short_delta=short_row['est_delta'],
                        expiration=expiration,
                        dte=dte,
                        current_price=current_price,
                        spread_width=spread_width,
                        max_debit=max_debit,
                        mid_debit=mid_debit,
                        max_profit=max_profit,
                        max_loss=mid_debit,
                        breakeven=long_row['strike'] - mid_debit,
                        risk_reward=risk_reward,
                        spread_pct=avg_spread_pct,
                        open_interest=int(long_row.get('openInterest', 0) +
                                         short_row.get('openInterest', 0)),
                    )
        
        return best_spread
    
    def generate_candidates(self, ticker: str, direction: str, 
                           options_data: dict) -> list[SpreadCandidate]:
        """
        Generate spread candidates for a ticker based on direction.
        """
        if options_data is None:
            return []
        
        current_price = options_data.get('current_price', 0)
        if current_price <= 0:
            return []
        
        candidates = []
        
        if direction == 'BULLISH':
            spread = self.generate_call_spread(ticker, options_data, current_price)
            if spread:
                candidates.append(spread)
        elif direction == 'BEARISH':
            spread = self.generate_put_spread(ticker, options_data, current_price)
            if spread:
                candidates.append(spread)
        
        return candidates


def generate_all_candidates(filter_results: list, market_data: dict) -> list[SpreadCandidate]:
    """
    Generate spread candidates for all tickers that passed filters.
    """
    generator = CandidateGenerator()
    all_candidates = []
    
    for result in filter_results:
        if not result.passed:
            continue
        
        ticker = result.ticker
        direction = result.direction
        options_data = market_data.get(ticker, {}).get('options')
        
        if options_data:
            candidates = generator.generate_candidates(ticker, direction, options_data)
            all_candidates.extend(candidates)
    
    # Sort by risk/reward ratio
    all_candidates.sort(key=lambda x: x.risk_reward, reverse=True)
    
    return all_candidates


"""
STRATEGY 5: Iron Condor (Range-Bound)

THE EDGE:
Most stocks, most of the time, don't make huge moves. An iron condor profits when
a stock stays within a range. You sell both a call spread AND a put spread,
collecting premium from both sides. If the stock stays between your short strikes,
you keep all the premium.

WHY IT WORKS:
- Stocks are range-bound ~70% of the time
- You collect premium from both directions
- Theta decay works for you on both sides
- Defined risk on both ends

HISTORICAL EDGE:
- Win rate can be 70-80% with proper strike selection
- Consistent small profits
- Works especially well in low-volatility environments

WHEN IT FAILS:
- Strong trending markets
- Unexpected news/events
- Earnings (never hold through earnings)
- Flash crashes or gap moves

BEST CONDITIONS:
- IV Rank 30-50 (not too low, not too high)
- Stock has been range-bound for weeks
- No upcoming catalysts
- Low RSI volatility (RSI staying 40-60)
"""

from .base import BaseStrategy, StrategyResult
from typing import Optional


class IronCondorRange(BaseStrategy):
    
    NAME = "Iron Condor Range"
    DESCRIPTION = "Sell iron condors on range-bound stocks to collect premium"
    EDGE_TYPE = "volatility"
    RISK_LEVEL = "medium"
    EXPECTED_WIN_RATE = 0.72
    TYPICAL_HOLD_DAYS = 21
    
    # Filter thresholds
    FILTERS = {
        # Range-bound confirmation (KEY)
        'max_return_20d': 5.0,       # Stock hasn't moved much
        'max_return_5d': 3.0,        # Recent stability
        
        # RSI in middle range
        'rsi_min': 35,
        'rsi_max': 65,
        
        # IV not extreme
        'iv_rank_min': 25,           # Some premium to collect
        'iv_rank_max': 55,           # Not expecting big move
        
        # Events - CRITICAL
        'min_days_to_earnings': 25,  # Stay far from earnings
        
        # MA alignment - prefer flat
        'max_ma_spread_pct': 3.0,    # MA20 and MA50 close together
        
        # Liquidity
        'max_spread_pct': 0.08,
        'min_open_interest': 500,
    }
    
    # Option structure
    STRUCTURE = {
        'type': 'iron_condor',
        'dte_min': 30,
        'dte_max': 45,
        'call_short_delta': 0.20,    # Sell 20 delta call
        'call_long_delta': 0.10,     # Buy 10 delta call (wing)
        'put_short_delta': 0.20,     # Sell 20 delta put
        'put_long_delta': 0.10,      # Buy 10 delta put (wing)
        'min_credit_pct': 0.30,      # Min 30% of wing width as credit
    }
    
    # Exit rules
    EXITS = {
        'take_profit_pct': 0.50,     # Close at 50% profit
        'stop_loss_pct': 1.00,       # Close if loss = credit received
        'time_stop_dte': 14,         # Close at 14 DTE (avoid gamma)
        'breakout_exit': True,       # Exit if stock breaks range
    }
    
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        """Check if ticker is good for iron condor."""
        reasons = []
        
        price = data.get('price')
        ma20 = data.get('ma20')
        ma50 = data.get('ma50')
        return_5d = data.get('return_5d', 0)
        return_20d = data.get('return_20d', 0)
        iv_rank = data.get('iv_rank')
        rsi = data.get('rsi', 50)
        earnings = data.get('earnings_date')
        
        if any(v is None for v in [price, ma20, ma50]):
            return StrategyResult(ticker, False, None, 0, ['Missing price data'], '')
        
        # RANGE-BOUND CHECK (most important)
        if abs(return_20d) > self.FILTERS['max_return_20d']:
            reasons.append(f"20D return {return_20d:+.1f}% too large (max ±{self.FILTERS['max_return_20d']}%)")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        if abs(return_5d) > self.FILTERS['max_return_5d']:
            reasons.append(f"5D return {return_5d:+.1f}% too large (max ±{self.FILTERS['max_return_5d']}%)")
            return StrategyResult(ticker, False, None, 10, reasons, '')
        
        reasons.append(f"Range-bound: 5D {return_5d:+.1f}%, 20D {return_20d:+.1f}%")
        
        # MA SPREAD CHECK - MAs should be close (flat trend)
        ma_spread_pct = abs(ma20 - ma50) / ma50 * 100
        if ma_spread_pct > self.FILTERS['max_ma_spread_pct']:
            reasons.append(f"MAs diverging {ma_spread_pct:.1f}% (trending, not ranging)")
            return StrategyResult(ticker, False, None, 20, reasons, '')
        
        reasons.append(f"MAs flat: spread {ma_spread_pct:.1f}%")
        
        # RSI CHECK - should be in middle
        if not (self.FILTERS['rsi_min'] <= rsi <= self.FILTERS['rsi_max']):
            reasons.append(f"RSI {rsi:.0f} outside range ({self.FILTERS['rsi_min']}-{self.FILTERS['rsi_max']})")
            return StrategyResult(ticker, False, None, 25, reasons, '')
        
        reasons.append(f"RSI {rsi:.0f} (neutral)")
        
        # IV RANK CHECK
        if iv_rank is not None:
            if iv_rank < self.FILTERS['iv_rank_min']:
                reasons.append(f"IV Rank {iv_rank:.0f} too low (not enough premium)")
                return StrategyResult(ticker, False, None, 30, reasons, '')
            if iv_rank > self.FILTERS['iv_rank_max']:
                reasons.append(f"IV Rank {iv_rank:.0f} too high (expecting move)")
                return StrategyResult(ticker, False, None, 30, reasons, '')
            reasons.append(f"IV Rank {iv_rank:.0f} (good for premium)")
        
        # EARNINGS CHECK - CRITICAL for iron condors
        if earnings:
            from datetime import datetime
            try:
                earn_dt = datetime.strptime(earnings, '%Y-%m-%d')
                days_to = (earn_dt - datetime.now()).days
                if 0 <= days_to < self.FILTERS['min_days_to_earnings']:
                    reasons.append(f"Earnings in {days_to} days - NEVER hold IC through earnings")
                    return StrategyResult(ticker, False, None, 0, reasons, '')
                reasons.append(f"Earnings in {days_to} days (safe)")
            except:
                pass
        
        # Check options
        if data.get('options') is None:
            reasons.append("No options data")
            return StrategyResult(ticker, False, 'NEUTRAL', 50, reasons, '')
        
        # Signal strength
        strength = 60
        if abs(return_20d) < 2:
            strength += 15  # Very range-bound
        if 40 <= rsi <= 60:
            strength += 10  # Perfect RSI
        if iv_rank and 35 <= iv_rank <= 45:
            strength += 10  # Ideal IV
        
        return StrategyResult(
            ticker=ticker,
            passed=True,
            direction='NEUTRAL',
            signal_strength=min(strength, 100),
            reasons=reasons,
            trade_type='IRON_CONDOR'
        )
    
    def get_option_structure(self) -> dict:
        return self.STRUCTURE
    
    def get_exit_rules(self) -> dict:
        return self.EXITS


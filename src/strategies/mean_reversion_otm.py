"""
STRATEGY 3: Mean Reversion OTM Put/Call

THE EDGE:
When a stock makes an extreme short-term move (oversold/overbought), it has a
statistical tendency to revert toward the mean. Buying cheap OTM options in the
reversal direction can capture this snap-back with asymmetric risk/reward.

WHY IT WORKS:
- Markets overreact to news in the short term
- RSI extremes (<25 or >75) historically precede reversals
- OTM options are cheap, so small moves = big % gains
- Defined risk (can only lose premium paid)

HISTORICAL EDGE:
- RSI mean reversion has ~55-60% hit rate on 5-10 day horizon
- Winners can be 2-5x, losers are -100% (but small $)
- Works best in liquid large-caps that don't go to zero

WHEN IT FAILS:
- Fundamental changes (stock deserves new price)
- Momentum continuation (trend > mean reversion)
- Time decay kills you if reversal is slow
- Need to be RIGHT on timing

BEST CONDITIONS:
- RSI < 25 (oversold) or RSI > 75 (overbought)
- High volume on the extreme move (capitulation)
- No fundamental reason for the move
- Stock has history of mean-reverting
"""

from .base import BaseStrategy, StrategyResult
from typing import Optional


class MeanReversionOTM(BaseStrategy):
    
    NAME = "Mean Reversion OTM"
    DESCRIPTION = "Buy cheap OTM options betting on snap-back from extreme moves"
    EDGE_TYPE = "mean_reversion"
    RISK_LEVEL = "high"
    EXPECTED_WIN_RATE = 0.45  # Lower win rate, but bigger winners
    TYPICAL_HOLD_DAYS = 7
    
    # Filter thresholds
    FILTERS = {
        # RSI extremes (KEY signal)
        'rsi_oversold': 25,          # Below this = oversold
        'rsi_overbought': 75,        # Above this = overbought
        
        # Short-term move magnitude
        'min_return_5d': 5.0,        # At least 5% move in 5 days
        
        # Don't fight strong trends
        'max_return_20d': 15.0,      # If 20D move is huge, trend may continue
        
        # IV check - want cheap options
        'iv_rank_max': 50,           # Don't overpay for options
        
        # Safety
        'min_days_to_earnings': 7,
        
        # Liquidity
        'max_spread_pct': 0.12,      # Can accept wider spreads for OTM
        'min_open_interest': 200,
    }
    
    # Option structure
    STRUCTURE = {
        'type': 'long_otm',
        'dte_min': 14,
        'dte_max': 30,               # Shorter DTE for faster theta
        'target_delta': 0.25,        # OTM but not lottery ticket
        'max_cost_pct': 0.02,        # Max 2% of stock price
    }
    
    # Exit rules
    EXITS = {
        'take_profit_pct': 1.00,     # Take profit at 100% gain (double)
        'stop_loss_pct': 0.50,       # Cut at 50% loss
        'time_stop_dte': 5,          # Exit if < 5 DTE
        'rsi_normalization_exit': True,  # Exit when RSI returns to 40-60
    }
    
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        """Check if ticker shows mean reversion setup."""
        reasons = []
        
        price = data.get('price')
        ma20 = data.get('ma20')
        return_5d = data.get('return_5d', 0)
        return_20d = data.get('return_20d', 0)
        iv_rank = data.get('iv_rank')
        rsi = data.get('rsi')
        earnings = data.get('earnings_date')
        
        # RSI is the KEY signal
        if rsi is None:
            reasons.append("RSI unavailable")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        direction = None
        
        # OVERSOLD - bullish reversal
        if rsi < self.FILTERS['rsi_oversold']:
            direction = 'BULLISH'
            reasons.append(f"RSI {rsi:.0f} OVERSOLD (< {self.FILTERS['rsi_oversold']}) - reversal setup")
            
            # Confirm with price action
            if return_5d and return_5d < -self.FILTERS['min_return_5d']:
                reasons.append(f"5D return: {return_5d:.1f}% (sharp drop)")
            else:
                reasons.append(f"5D return {return_5d:.1f}% not extreme enough")
                return StrategyResult(ticker, False, None, 20, reasons, '')
        
        # OVERBOUGHT - bearish reversal
        elif rsi > self.FILTERS['rsi_overbought']:
            direction = 'BEARISH'
            reasons.append(f"RSI {rsi:.0f} OVERBOUGHT (> {self.FILTERS['rsi_overbought']}) - reversal setup")
            
            if return_5d and return_5d > self.FILTERS['min_return_5d']:
                reasons.append(f"5D return: +{return_5d:.1f}% (sharp rally)")
            else:
                reasons.append(f"5D return +{return_5d:.1f}% not extreme enough")
                return StrategyResult(ticker, False, None, 20, reasons, '')
        
        else:
            reasons.append(f"RSI {rsi:.0f} not extreme (need <{self.FILTERS['rsi_oversold']} or >{self.FILTERS['rsi_overbought']})")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        # Check 20D move isn't too extreme (fighting a mega-trend)
        if abs(return_20d) > self.FILTERS['max_return_20d']:
            reasons.append(f"20D return {return_20d:.1f}% too extreme - may be trend, not reversal")
            return StrategyResult(ticker, False, direction, 30, reasons, '')
        
        # IV CHECK - want cheap options
        if iv_rank is not None and iv_rank > self.FILTERS['iv_rank_max']:
            reasons.append(f"IV Rank {iv_rank:.0f} > {self.FILTERS['iv_rank_max']} (options expensive)")
            return StrategyResult(ticker, False, direction, 40, reasons, '')
        
        if iv_rank:
            reasons.append(f"IV Rank: {iv_rank:.0f} (options reasonably priced)")
        
        # EARNINGS CHECK
        if earnings:
            from datetime import datetime
            try:
                earn_dt = datetime.strptime(earnings, '%Y-%m-%d')
                days_to = (earn_dt - datetime.now()).days
                if 0 <= days_to < self.FILTERS['min_days_to_earnings']:
                    reasons.append(f"Earnings in {days_to} days - reversal may not happen")
                    return StrategyResult(ticker, False, direction, 35, reasons, '')
            except:
                pass
        
        # Check options available
        if data.get('options') is None:
            reasons.append("No options data")
            return StrategyResult(ticker, False, direction, 50, reasons, '')
        
        # Calculate signal strength
        strength = 50
        if rsi < 20 or rsi > 80:
            strength += 20  # Very extreme RSI
        if abs(return_5d) > 8:
            strength += 15  # Big short-term move
        if iv_rank and iv_rank < 30:
            strength += 10  # Cheap options
        
        trade_type = 'CALL_LONG' if direction == 'BULLISH' else 'PUT_LONG'
        
        return StrategyResult(
            ticker=ticker,
            passed=True,
            direction=direction,
            signal_strength=min(strength, 100),
            reasons=reasons,
            trade_type=trade_type
        )
    
    def get_option_structure(self) -> dict:
        return self.STRUCTURE
    
    def get_exit_rules(self) -> dict:
        return self.EXITS


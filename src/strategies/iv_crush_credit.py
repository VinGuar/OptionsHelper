"""
STRATEGY 2: IV Crush Credit Spread (Post-Earnings / High IV)

THE EDGE:
Implied volatility tends to be OVERPRICED relative to realized volatility, especially
after events or during fear spikes. By selling credit spreads when IV is elevated,
you collect premium that decays as IV normalizes. This is "selling insurance."

WHY IT WORKS:
- IV consistently overestimates actual moves (volatility risk premium)
- Post-earnings, IV collapses rapidly (IV crush)
- Credit spreads have defined risk while capturing theta + vega decay
- Time is on your side - you profit if nothing happens

HISTORICAL EDGE:
- Volatility risk premium averages 2-4% annually
- Win rate typically 65-75% (most options expire worthless)
- Smaller wins, but more frequent

WHEN IT FAILS:
- Unexpected large moves (black swans)
- Sustained trending markets (wrong direction)
- When you sell too close to the money
- Gap risk overnight

BEST CONDITIONS:
- IV Rank > 60 (elevated fear)
- After earnings (IV crush imminent)
- Range-bound stocks
- No upcoming catalysts
"""

from .base import BaseStrategy, StrategyResult
from typing import Optional
from datetime import datetime


class IVCrushCredit(BaseStrategy):
    
    NAME = "IV Crush Credit Spread"
    DESCRIPTION = "Sell credit spreads when IV is elevated to capture premium decay"
    EDGE_TYPE = "volatility"
    RISK_LEVEL = "medium"
    EXPECTED_WIN_RATE = 0.68
    TYPICAL_HOLD_DAYS = 14
    
    # Filter thresholds
    FILTERS = {
        # Volatility (KEY for this strategy)
        'iv_rank_min': 55,           # IV must be elevated
        'iv_rank_ideal': 70,         # Sweet spot
        
        # Trend - prefer range-bound or slight counter-trend
        'max_return_20d': 8.0,       # Not too trendy
        'prefer_mean_reversion': True,
        
        # Post-earnings bonus
        'days_after_earnings_min': 1,
        'days_after_earnings_max': 5,
        
        # Safety
        'min_days_to_next_earnings': 20,  # No upcoming earnings
        
        # Liquidity
        'max_spread_pct': 0.10,
        'min_open_interest': 300,
    }
    
    # Option structure
    STRUCTURE = {
        'type': 'credit_spread',
        'dte_min': 20,
        'dte_max': 35,
        'short_delta': 0.25,         # Sell ~25 delta (OTM)
        'long_delta': 0.10,          # Buy ~10 delta (further OTM)
        'min_credit_pct': 0.25,      # Min 25% of spread width as credit
    }
    
    # Exit rules
    EXITS = {
        'take_profit_pct': 0.50,     # Close at 50% profit (don't be greedy)
        'stop_loss_pct': 1.50,       # Cut at 150% of credit received
        'time_stop_dte': 7,          # Close if < 7 DTE (gamma risk)
        'iv_target_exit': True,      # Exit when IV normalizes
    }
    
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        """Check if ticker is good for IV crush credit spread."""
        reasons = []
        
        price = data.get('price')
        ma20 = data.get('ma20')
        return_20d = data.get('return_20d', 0)
        iv_rank = data.get('iv_rank')
        rsi = data.get('rsi', 50)
        earnings = data.get('earnings_date')
        
        # IV RANK is the KEY filter
        if iv_rank is None:
            reasons.append("IV Rank unknown - cannot evaluate")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        if iv_rank < self.FILTERS['iv_rank_min']:
            reasons.append(f"IV Rank {iv_rank:.0f} < {self.FILTERS['iv_rank_min']} (need elevated IV)")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        reasons.append(f"IV Rank: {iv_rank:.0f} (elevated - good for premium selling)")
        
        # Check if post-earnings (bonus signal)
        post_earnings = False
        if earnings:
            try:
                earn_dt = datetime.strptime(earnings, '%Y-%m-%d')
                days_since = (datetime.now() - earn_dt).days
                if self.FILTERS['days_after_earnings_min'] <= days_since <= self.FILTERS['days_after_earnings_max']:
                    post_earnings = True
                    reasons.append(f"Post-earnings ({days_since} days ago) - IV crush opportunity")
                
                # Check no upcoming earnings
                days_to = (earn_dt - datetime.now()).days
                if 0 < days_to < self.FILTERS['min_days_to_next_earnings']:
                    reasons.append(f"Earnings in {days_to} days - SKIP (event risk)")
                    return StrategyResult(ticker, False, None, 30, reasons, '')
            except:
                pass
        
        # TREND CHECK - prefer non-trending or slight mean reversion
        if abs(return_20d) > self.FILTERS['max_return_20d']:
            reasons.append(f"20D return {return_20d:.1f}% too extreme (prefer range-bound)")
            return StrategyResult(ticker, False, None, 20, reasons, '')
        
        # Determine direction (sell against recent move for mean reversion)
        if return_20d > 2:
            direction = 'BEARISH'  # Stock went up, sell call credit spread
            trade_type = 'CALL_CREDIT'
            reasons.append(f"Stock up {return_20d:.1f}% - sell call spread (mean reversion)")
        elif return_20d < -2:
            direction = 'BULLISH'  # Stock went down, sell put credit spread
            trade_type = 'PUT_CREDIT'
            reasons.append(f"Stock down {return_20d:.1f}% - sell put spread (mean reversion)")
        else:
            # Neutral - sell the weaker side based on RSI
            if rsi > 55:
                direction = 'BEARISH'
                trade_type = 'CALL_CREDIT'
                reasons.append(f"RSI {rsi:.0f} slightly elevated - sell call spread")
            else:
                direction = 'BULLISH'
                trade_type = 'PUT_CREDIT'
                reasons.append(f"RSI {rsi:.0f} neutral/low - sell put spread")
        
        # Check options available
        if data.get('options') is None:
            reasons.append("No options data")
            return StrategyResult(ticker, False, direction, 40, reasons, '')
        
        # Calculate signal strength
        strength = 50
        strength += (iv_rank - 55) * 0.5  # Higher IV = stronger signal
        if post_earnings:
            strength += 15
        if 30 <= rsi <= 70:  # Not extreme RSI
            strength += 10
        
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


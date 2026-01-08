"""
STRATEGY 1: Trend Following Debit Spread

THE EDGE:
When a stock is in a strong, confirmed trend (price > MA20 > MA50 with momentum),
the probability of continuation over 30-45 days is higher than random. Debit spreads
let you profit from this continuation while limiting risk and reducing IV exposure.

WHY IT WORKS:
- Institutions and algorithms trend-follow, creating momentum persistence
- Debit spreads have defined risk (can't lose more than you pay)
- Selling the OTM leg reduces cost and theta decay
- 30-45 DTE gives time for the move without excessive theta burn

HISTORICAL EDGE:
- Academic research shows momentum factor has ~0.5% monthly alpha
- Win rate typically 55-60% with proper filters
- Risk/reward of 1:1.5 to 1:2 on winners

WHEN IT FAILS:
- Choppy/ranging markets (no trend)
- Sudden reversals (news, macro shocks)
- IV crush if you enter when IV is elevated
"""

from .base import BaseStrategy, StrategyResult
from typing import Optional


class TrendFollowingDebit(BaseStrategy):
    
    NAME = "Trend Following Debit Spread"
    DESCRIPTION = "Buy debit spreads in the direction of strong trends"
    EDGE_TYPE = "trend"
    RISK_LEVEL = "medium"
    EXPECTED_WIN_RATE = 0.58
    TYPICAL_HOLD_DAYS = 21
    
    # Filter thresholds
    FILTERS = {
        # Trend confirmation
        'min_return_20d': 3.0,       # Minimum 3% move in 20 days
        'require_ma_alignment': True, # Price > MA20 > MA50 (or inverse for bearish)
        
        # Volatility
        'iv_rank_min': 15,           # Not too cheap (move may be done)
        'iv_rank_max': 55,           # Not too expensive (IV crush risk)
        
        # Momentum confirmation
        'rsi_bull_min': 50,          # RSI > 50 for bullish
        'rsi_bull_max': 75,          # Not overbought
        'rsi_bear_min': 25,          # Not oversold
        'rsi_bear_max': 50,          # RSI < 50 for bearish
        
        # Events
        'min_days_to_earnings': 10,
        
        # Liquidity
        'max_spread_pct': 0.08,
        'min_open_interest': 500,
    }
    
    # Option structure
    STRUCTURE = {
        'type': 'debit_spread',
        'dte_min': 30,
        'dte_max': 45,
        'long_delta': 0.40,          # Buy ~40 delta
        'short_delta': 0.20,         # Sell ~20 delta
        'max_debit_pct': 0.35,       # Max 35% of spread width
    }
    
    # Exit rules
    EXITS = {
        'take_profit_pct': 0.50,     # Take profit at 50% of max gain
        'stop_loss_pct': 0.50,       # Cut at 50% loss
        'time_stop_dte': 10,         # Exit if < 10 DTE remaining
        'trend_break_exit': True,    # Exit if price crosses MA20
    }
    
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        """Check if ticker meets trend-following criteria."""
        reasons = []
        
        price = data.get('price')
        ma20 = data.get('ma20')
        ma50 = data.get('ma50')
        return_20d = data.get('return_20d', 0)
        iv_rank = data.get('iv_rank')
        rsi = data.get('rsi', 50)
        earnings = data.get('earnings_date')
        
        # Check data availability
        if any(v is None for v in [price, ma20, ma50]):
            return StrategyResult(ticker, False, None, 0, ['Missing price data'], '')
        
        # Determine direction
        direction = None
        
        # BULLISH CHECK
        if (price > ma20 > ma50 and 
            return_20d >= self.FILTERS['min_return_20d']):
            
            if self.FILTERS['rsi_bull_min'] <= rsi <= self.FILTERS['rsi_bull_max']:
                direction = 'BULLISH'
                reasons.append(f"Uptrend: ${price:.2f} > MA20 ${ma20:.2f} > MA50 ${ma50:.2f}")
                reasons.append(f"Momentum: +{return_20d:.1f}% in 20 days")
                reasons.append(f"RSI: {rsi:.0f} (bullish range)")
            else:
                reasons.append(f"RSI {rsi:.0f} outside bullish range ({self.FILTERS['rsi_bull_min']}-{self.FILTERS['rsi_bull_max']})")
        
        # BEARISH CHECK
        elif (price < ma20 < ma50 and 
              return_20d <= -self.FILTERS['min_return_20d']):
            
            if self.FILTERS['rsi_bear_min'] <= rsi <= self.FILTERS['rsi_bear_max']:
                direction = 'BEARISH'
                reasons.append(f"Downtrend: ${price:.2f} < MA20 ${ma20:.2f} < MA50 ${ma50:.2f}")
                reasons.append(f"Momentum: {return_20d:.1f}% in 20 days")
                reasons.append(f"RSI: {rsi:.0f} (bearish range)")
            else:
                reasons.append(f"RSI {rsi:.0f} outside bearish range ({self.FILTERS['rsi_bear_min']}-{self.FILTERS['rsi_bear_max']})")
        else:
            reasons.append(f"No clear trend: Price ${price:.2f}, MA20 ${ma20:.2f}, MA50 ${ma50:.2f}")
            reasons.append(f"20D return: {return_20d:.1f}% (need ±{self.FILTERS['min_return_20d']}%)")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        if direction is None:
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        # IV RANK CHECK
        if iv_rank is not None:
            if iv_rank < self.FILTERS['iv_rank_min']:
                reasons.append(f"IV Rank {iv_rank:.0f} too low (min {self.FILTERS['iv_rank_min']})")
                return StrategyResult(ticker, False, direction, 30, reasons, '')
            if iv_rank > self.FILTERS['iv_rank_max']:
                reasons.append(f"IV Rank {iv_rank:.0f} too high (max {self.FILTERS['iv_rank_max']})")
                return StrategyResult(ticker, False, direction, 30, reasons, '')
            reasons.append(f"IV Rank: {iv_rank:.0f} (good range)")
        
        # EARNINGS CHECK
        if earnings:
            from datetime import datetime
            try:
                earn_dt = datetime.strptime(earnings, '%Y-%m-%d')
                days_to = (earn_dt - datetime.now()).days
                if 0 <= days_to <= self.FILTERS['min_days_to_earnings']:
                    reasons.append(f"Earnings in {days_to} days - SKIP")
                    return StrategyResult(ticker, False, direction, 40, reasons, '')
            except:
                pass
        
        # LIQUIDITY CHECK (done in main scanner, but note it)
        options = data.get('options')
        if options is None:
            reasons.append("No options data")
            return StrategyResult(ticker, False, direction, 50, reasons, '')
        
        # Calculate signal strength (0-100)
        strength = 60
        strength += min(abs(return_20d) - 3, 10) * 2  # Bonus for stronger moves
        if iv_rank and 25 <= iv_rank <= 45:
            strength += 10  # Ideal IV range
        
        trade_type = 'CALL_DEBIT' if direction == 'BULLISH' else 'PUT_DEBIT'
        
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


"""
STRATEGY 4: Breakout Momentum

THE EDGE:
When a stock breaks above a significant resistance level (like 52-week high) with
volume confirmation, it often continues higher due to:
1. Short covering (shorts panic buy)
2. Breakout traders piling in
3. Media attention bringing new buyers

Buying calls or call spreads on confirmed breakouts captures this momentum.

WHY IT WORKS:
- New highs attract attention and buying
- Short squeezes create explosive moves
- Psychological resistance becomes support
- "Stocks making new highs tend to keep making new highs"

HISTORICAL EDGE:
- 52-week high breakouts have ~60% continuation rate over 1 month
- Average winner is larger than average loser
- Works best in bull markets

WHEN IT FAILS:
- False breakouts (fakeouts)
- Bear markets / risk-off environments
- Low volume breakouts (no conviction)
- Buying the exact top

BEST CONDITIONS:
- Price breaks 52-week high
- Volume > 1.5x average on breakout day
- RSI not extremely overbought (< 80)
- Broad market in uptrend
"""

from .base import BaseStrategy, StrategyResult
from typing import Optional


class BreakoutMomentum(BaseStrategy):
    
    NAME = "Breakout Momentum"
    DESCRIPTION = "Buy calls on stocks breaking to new highs with volume"
    EDGE_TYPE = "trend"
    RISK_LEVEL = "medium-high"
    EXPECTED_WIN_RATE = 0.55
    TYPICAL_HOLD_DAYS = 14
    
    # Filter thresholds
    FILTERS = {
        # Breakout confirmation
        'near_high_pct': 0.98,       # Within 2% of 52-week high
        'min_return_5d': 3.0,        # Recent momentum
        
        # Trend alignment
        'require_above_ma20': True,
        'require_above_ma50': True,
        
        # Not too extended
        'max_above_ma20_pct': 10.0,  # Not more than 10% above MA20
        'rsi_max': 80,               # Not extremely overbought
        
        # Volatility
        'iv_rank_min': 20,
        'iv_rank_max': 60,
        
        # Events
        'min_days_to_earnings': 7,
        
        # Liquidity
        'max_spread_pct': 0.08,
        'min_open_interest': 500,
    }
    
    # Option structure
    STRUCTURE = {
        'type': 'debit_spread',      # Or long call for more leverage
        'dte_min': 21,
        'dte_max': 45,
        'long_delta': 0.50,          # ATM or slightly ITM
        'short_delta': 0.25,
        'max_debit_pct': 0.40,
    }
    
    # Exit rules
    EXITS = {
        'take_profit_pct': 0.75,     # Take profit at 75% of max
        'stop_loss_pct': 0.40,       # Tighter stop (breakouts should work fast)
        'time_stop_dte': 10,
        'breakdown_exit': True,      # Exit if price falls back below breakout level
    }
    
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        """Check if ticker shows breakout setup."""
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
        
        # TREND ALIGNMENT CHECK
        if not (price > ma20 > ma50):
            reasons.append(f"Not in uptrend: ${price:.2f}, MA20 ${ma20:.2f}, MA50 ${ma50:.2f}")
            return StrategyResult(ticker, False, None, 0, reasons, '')
        
        reasons.append(f"Uptrend confirmed: ${price:.2f} > MA20 > MA50")
        
        # MOMENTUM CHECK
        if return_5d < self.FILTERS['min_return_5d']:
            reasons.append(f"5D return +{return_5d:.1f}% < {self.FILTERS['min_return_5d']}% (weak momentum)")
            return StrategyResult(ticker, False, None, 20, reasons, '')
        
        reasons.append(f"Strong 5D momentum: +{return_5d:.1f}%")
        
        # Check if near highs (proxy for breakout)
        # We use 20D return as proxy - strong 20D move suggests breakout
        if return_20d < 5:
            reasons.append(f"20D return +{return_20d:.1f}% - not a strong breakout")
            return StrategyResult(ticker, False, None, 30, reasons, '')
        
        reasons.append(f"20D momentum: +{return_20d:.1f}% (breakout territory)")
        
        # NOT TOO EXTENDED
        pct_above_ma20 = ((price - ma20) / ma20) * 100
        if pct_above_ma20 > self.FILTERS['max_above_ma20_pct']:
            reasons.append(f"Extended {pct_above_ma20:.1f}% above MA20 (> {self.FILTERS['max_above_ma20_pct']}%)")
            return StrategyResult(ticker, False, 'BULLISH', 35, reasons, '')
        
        # RSI CHECK
        if rsi > self.FILTERS['rsi_max']:
            reasons.append(f"RSI {rsi:.0f} > {self.FILTERS['rsi_max']} (overbought)")
            return StrategyResult(ticker, False, 'BULLISH', 40, reasons, '')
        
        reasons.append(f"RSI {rsi:.0f} (not overbought)")
        
        # IV CHECK
        if iv_rank is not None:
            if iv_rank < self.FILTERS['iv_rank_min']:
                reasons.append(f"IV Rank {iv_rank:.0f} low - options cheap but move may be done")
            elif iv_rank > self.FILTERS['iv_rank_max']:
                reasons.append(f"IV Rank {iv_rank:.0f} high - IV crush risk")
                return StrategyResult(ticker, False, 'BULLISH', 45, reasons, '')
            else:
                reasons.append(f"IV Rank {iv_rank:.0f} (acceptable)")
        
        # EARNINGS CHECK
        if earnings:
            from datetime import datetime
            try:
                earn_dt = datetime.strptime(earnings, '%Y-%m-%d')
                days_to = (earn_dt - datetime.now()).days
                if 0 <= days_to < self.FILTERS['min_days_to_earnings']:
                    reasons.append(f"Earnings in {days_to} days - breakout may be earnings anticipation")
                    return StrategyResult(ticker, False, 'BULLISH', 40, reasons, '')
            except:
                pass
        
        # Check options
        if data.get('options') is None:
            reasons.append("No options data")
            return StrategyResult(ticker, False, 'BULLISH', 50, reasons, '')
        
        # Signal strength
        strength = 55
        strength += min(return_5d - 3, 10) * 2
        strength += min(return_20d - 5, 15)
        if iv_rank and 30 <= iv_rank <= 50:
            strength += 10
        
        return StrategyResult(
            ticker=ticker,
            passed=True,
            direction='BULLISH',
            signal_strength=min(strength, 100),
            reasons=reasons,
            trade_type='CALL_DEBIT'
        )
    
    def get_option_structure(self) -> dict:
        return self.STRUCTURE
    
    def get_exit_rules(self) -> dict:
        return self.EXITS


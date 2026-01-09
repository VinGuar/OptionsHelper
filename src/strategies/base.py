"""
Base Strategy Class
All edge strategies inherit from this.
"""
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod


@dataclass
class StrategyResult:
    """Result of applying a strategy to a ticker."""
    ticker: str
    passed: bool
    direction: Optional[str]  # 'BULLISH', 'BEARISH', or 'NEUTRAL'
    signal_strength: float    # 0-100 score
    reasons: list[str]
    trade_type: str           # e.g., 'CALL_DEBIT', 'PUT_CREDIT', etc.
    

class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    Each strategy must implement these methods.
    """
    
    # Strategy metadata (override in subclass)
    NAME = "Base Strategy"
    DESCRIPTION = "Base strategy class"
    EDGE_TYPE = "unknown"  # 'trend', 'volatility', 'mean_reversion', 'event'
    RISK_LEVEL = "medium"  # 'low', 'medium', 'high'
    EXPECTED_WIN_RATE = 0.50
    TYPICAL_HOLD_DAYS = 30
    
    @abstractmethod
    def check_entry(self, ticker: str, data: dict) -> StrategyResult:
        """
        Check if a ticker meets entry criteria.
        Returns StrategyResult with pass/fail and details.
        """
        pass
    
    @abstractmethod
    def get_option_structure(self) -> dict:
        """
        Return the option structure parameters for this strategy.
        e.g., {'type': 'debit_spread', 'dte_min': 30, 'dte_max': 45, ...}
        """
        pass
    
    @abstractmethod
    def get_exit_rules(self) -> dict:
        """
        Return exit rules for this strategy.
        e.g., {'take_profit_pct': 0.50, 'stop_loss_pct': 0.50, ...}
        """
        pass
    
    def get_info(self) -> dict:
        """Return strategy info for display."""
        return {
            'name': self.NAME,
            'description': self.DESCRIPTION,
            'edge_type': self.EDGE_TYPE,
            'risk_level': self.RISK_LEVEL,
            'expected_win_rate': self.EXPECTED_WIN_RATE,
            'typical_hold_days': self.TYPICAL_HOLD_DAYS,
        }



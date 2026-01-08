"""
Strategy Loader
Dynamically loads all available strategies from the strategies folder.
"""
from typing import Dict, Type
from .base import BaseStrategy

# Import all strategies
from .trend_following_debit import TrendFollowingDebit
from .iv_crush_credit import IVCrushCredit
from .mean_reversion_otm import MeanReversionOTM
from .breakout_momentum import BreakoutMomentum
from .iron_condor_range import IronCondorRange


# Registry of all available strategies
STRATEGIES: Dict[str, Type[BaseStrategy]] = {
    '1': TrendFollowingDebit,
    '2': IVCrushCredit,
    '3': MeanReversionOTM,
    '4': BreakoutMomentum,
    '5': IronCondorRange,
}

# Short names for CLI
STRATEGY_NAMES = {
    '1': 'trend',
    '2': 'iv_crush',
    '3': 'mean_rev',
    '4': 'breakout',
    '5': 'condor',
}


def get_strategy(key: str) -> BaseStrategy:
    """Get a strategy instance by key (number or name)."""
    # Check if it's a number
    if key in STRATEGIES:
        return STRATEGIES[key]()
    
    # Check if it's a name
    for k, name in STRATEGY_NAMES.items():
        if name == key.lower():
            return STRATEGIES[k]()
    
    raise ValueError(f"Unknown strategy: {key}")


def list_strategies() -> list[dict]:
    """Return list of all available strategies with their info."""
    result = []
    for key, strategy_class in STRATEGIES.items():
        strategy = strategy_class()
        info = strategy.get_info()
        info['key'] = key
        info['short_name'] = STRATEGY_NAMES[key]
        result.append(info)
    return result


def print_strategy_menu():
    """Print a formatted menu of available strategies."""
    print("\n" + "=" * 70)
    print("AVAILABLE STRATEGIES")
    print("=" * 70)
    
    for key, strategy_class in STRATEGIES.items():
        strategy = strategy_class()
        info = strategy.get_info()
        
        risk_display = {
            'low': '[LOW]',
            'medium': '[MED]',
            'medium-high': '[MED+]',
            'high': '[HIGH]',
        }.get(info['risk_level'], '[???]')
        
        print(f"\n  [{key}] {info['name']}")
        print(f"      {info['description']}")
        print(f"      Type: {info['edge_type'].upper()} | Risk: {risk_display} | Win Rate: {info['expected_win_rate']*100:.0f}%")
    
    print("\n" + "=" * 70)


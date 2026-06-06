"""
Strategy Manager for Pine Script strategies
Integrates with TradingView and Sapphire
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib
import re
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Backtest/forward test result"""
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_profit: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    avg_trade: float = 0.0
    winning_trades: int = 0
    losing_trades: int = 0
    notes: str = ""


@dataclass
class Strategy:
    """Trading Strategy"""
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12])
    name: str = ""
    description: str = ""
    pine_code: str = ""
    version: str = "v5"
    category: str = "strategy"  # strategy, indicator
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = False
    is_validated: bool = False
    test_results: List[StrategyResult] = field(default_factory=list)
    default_params: Dict[str, Any] = field(default_factory=dict)
    preferred_symbols: List[str] = field(default_factory=list)
    preferred_timeframes: List[str] = field(default_factory=list)
    venues: List[str] = field(default_factory=list)  # ASTER, LIGHTER
    
    def validate_pine(self) -> tuple[bool, List[str]]:
        """Validate Pine Script syntax"""
        errors = []
        
        # Check version
        if f'//@version={self.version}' not in self.pine_code:
            errors.append(f"Missing or incorrect //@version={self.version}")
        
        # Check for strategy or indicator declaration
        if self.category == 'strategy':
            if not re.search(r'strategy\s*\(', self.pine_code, re.IGNORECASE):
                errors.append("Missing strategy() declaration")
        elif self.category == 'indicator':
            if not re.search(r'indicator\s*\(', self.pine_code, re.IGNORECASE):
                errors.append("Missing indicator() declaration")
        
        # Check for common syntax errors
        if self.pine_code.count('(') != self.pine_code.count(')'):
            errors.append("Unbalanced parentheses")
        
        if self.pine_code.count('[') != self.pine_code.count(']'):
            errors.append("Unbalanced brackets")
        
        # Check for required elements in strategies
        if self.category == 'strategy':
            if 'strategy.entry' not in self.pine_code and 'strategy.close' not in self.pine_code:
                errors.append("Strategy should have strategy.entry or strategy.close calls")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        return asdict(self)


class StrategyManager:
    """Manages Pine Script strategies"""
    
    def __init__(self, storage_path: str = "strategies"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.strategies: Dict[str, Strategy] = {}
        self._load_strategies()
    
    def _load_strategies(self):
        """Load strategies from storage"""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    strategy = Strategy(**data)
                    # Convert datetime strings back to datetime
                    if isinstance(strategy.created_at, str):
                        strategy.created_at = datetime.fromisoformat(strategy.created_at)
                    if isinstance(strategy.updated_at, str):
                        strategy.updated_at = datetime.fromisoformat(strategy.updated_at)
                    self.strategies[strategy.id] = strategy
            except Exception as e:
                logger.error(f"Error loading strategy {file_path}: {e}")
        
        logger.info(f"Loaded {len(self.strategies)} strategies")
    
    def _save_strategy(self, strategy: Strategy):
        """Save strategy to disk"""
        file_path = self.storage_path / f"{strategy.id}.json"
        with open(file_path, 'w') as f:
            json.dump(strategy.to_dict(), f, indent=2, default=str)
    
    def create_strategy(self, name: str, pine_code: str, **kwargs) -> Strategy:
        """Create a new strategy"""
        strategy = Strategy(
            name=name,
            pine_code=pine_code,
            description=kwargs.get('description', ''),
            author=kwargs.get('author', ''),
            category=kwargs.get('category', 'strategy'),
            version=kwargs.get('version', 'v5'),
            default_params=kwargs.get('default_params', {}),
            preferred_symbols=kwargs.get('preferred_symbols', []),
            preferred_timeframes=kwargs.get('preferred_timeframes', []),
            venues=kwargs.get('venues', ['ASTER', 'LIGHTER'])
        )
        
        # Validate
        is_valid, errors = strategy.validate_pine()
        strategy.is_validated = is_valid
        
        if not is_valid:
            logger.warning(f"Strategy validation failed: {errors}")
        
        self.strategies[strategy.id] = strategy
        self._save_strategy(strategy)
        
        logger.info(f"Created strategy: {name} ({strategy.id})")
        return strategy
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID"""
        return self.strategies.get(strategy_id)
    
    def get_strategy_by_name(self, name: str) -> Optional[Strategy]:
        """Get strategy by name"""
        for strategy in self.strategies.values():
            if strategy.name.lower() == name.lower():
                return strategy
        return None
    
    def list_strategies(self, category: str = None, active_only: bool = False) -> List[Strategy]:
        """List all strategies"""
        strategies = list(self.strategies.values())
        
        if category:
            strategies = [s for s in strategies if s.category == category]
        
        if active_only:
            strategies = [s for s in strategies if s.is_active]
        
        return sorted(strategies, key=lambda s: s.updated_at, reverse=True)
    
    def update_strategy(self, strategy_id: str, **kwargs) -> Optional[Strategy]:
        """Update strategy"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return None
        
        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        
        strategy.updated_at = datetime.now()
        
        # Re-validate if pine_code changed
        if 'pine_code' in kwargs:
            is_valid, errors = strategy.validate_pine()
            strategy.is_validated = is_valid
        
        self._save_strategy(strategy)
        return strategy
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete strategy"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            file_path = self.storage_path / f"{strategy_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """Activate strategy"""
        strategy = self.strategies.get(strategy_id)
        if strategy and strategy.is_validated:
            strategy.is_active = True
            strategy.updated_at = datetime.now()
            self._save_strategy(strategy)
            return True
        return False
    
    def deactivate_strategy(self, strategy_id: str) -> bool:
        """Deactivate strategy"""
        strategy = self.strategies.get(strategy_id)
        if strategy:
            strategy.is_active = False
            strategy.updated_at = datetime.now()
            self._save_strategy(strategy)
            return True
        return False
    
    def add_test_result(self, strategy_id: str, result: StrategyResult) -> bool:
        """Add test result to strategy"""
        strategy = self.strategies.get(strategy_id)
        if strategy:
            strategy.test_results.append(result)
            strategy.updated_at = datetime.now()
            self._save_strategy(strategy)
            return True
        return False
    
    def generate_strategy_template(self, name: str, category: str = "strategy") -> str:
        """Generate a Pine Script template"""
        if category == "strategy":
            return f'''//@version=5
strategy("{name}", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=10)

// Inputs
length = input.int(14, "Length", minval=1)

// Indicators
rsi = ta.rsi(close, length)

// Strategy Logic
longCondition = ta.crossover(rsi, 30)
shortCondition = ta.crossunder(rsi, 70)

// Entries
if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.close("Long")

// Plots
plot(rsi, "RSI", color=color.blue)
hline(70, "Overbought", color=color.red)
hline(30, "Oversold", color=color.green)
'''
        else:  # indicator
            return f'''//@version=5
indicator("{name}", overlay=true)

// Inputs
length = input.int(14, "Length", minval=1)

// Calculation
sma = ta.sma(close, length)

// Plot
plot(sma, "SMA", color=color.orange)
'''
    
    def analyze_strategy(self, pine_code: str) -> Dict[str, Any]:
        """Analyze Pine Script for indicators used, complexity, etc."""
        analysis = {
            'indicators_used': [],
            'complexity_score': 0,
            'has_entry_exit': False,
            'has_stop_loss': False,
            'has_take_profit': False,
            'risk_management': False,
            'lines_of_code': len(pine_code.split('\n')),
        }
        
        # Detect common indicators
        indicator_patterns = {
            'RSI': r'\brsi\b|ta\.rsi',
            'MACD': r'\bmacd\b|ta\.macd',
            'EMA': r'\bema\b|ta\.ema',
            'SMA': r'\bsma\b|ta\.sma',
            'Bollinger Bands': r'\bbb\b|ta\.bb|bollinger',
            'ATR': r'\batr\b|ta\.atr',
            'VWAP': r'\bvwap\b|ta\.vwap',
            'Volume': r'\bvolume\b',
            'Stochastic': r'\bstoch\b|ta\.stoch',
        }
        
        for indicator, pattern in indicator_patterns.items():
            if re.search(pattern, pine_code, re.IGNORECASE):
                analysis['indicators_used'].append(indicator)
        
        # Check for entry/exit logic
        if re.search(r'strategy\.(entry|long|short)', pine_code, re.IGNORECASE):
            analysis['has_entry_exit'] = True
        
        # Check for risk management
        if re.search(r'strategy\.(close|exit)', pine_code, re.IGNORECASE):
            analysis['has_stop_loss'] = True
        
        if 'takeprofit' in pine_code.lower() or 'take_profit' in pine_code.lower():
            analysis['has_take_profit'] = True
        
        # Calculate complexity score
        analysis['complexity_score'] = min(100, analysis['lines_of_code'] * 2 + len(analysis['indicators_used']) * 10)
        
        analysis['risk_management'] = analysis['has_stop_loss'] or analysis['has_take_profit']
        
        return analysis


# Singleton
_manager: Optional[StrategyManager] = None


def get_strategy_manager(storage_path: str = "strategies") -> StrategyManager:
    """Get singleton strategy manager"""
    global _manager
    if _manager is None:
        _manager = StrategyManager(storage_path)
    return _manager

"""
Risk Management Module
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from loguru import logger

class RiskManager:
    """Manages risk for trading operations"""
    
    def __init__(self, config: Dict):
        """Initialize risk manager"""
        self.config = config
        self.risk_config = config.get('risk_management', {})
        
        self.max_portfolio_risk = self.risk_config.get('max_portfolio_risk', 0.2)
        self.max_position_risk = self.risk_config.get('max_position_risk', 0.02)
        self.max_leverage = self.risk_config.get('max_leverage', 3)
        self.min_risk_reward_ratio = self.risk_config.get('min_risk_reward_ratio', 2.0)
        self.trailing_stop = self.risk_config.get('trailing_stop', True)
        self.trailing_stop_percentage = self.risk_config.get('trailing_stop_percentage', 0.05)
        
        # Position sizing config
        self.position_config = config.get('position_sizing', {})
        self.sizing_method = self.position_config.get('method', 'kelly_criterion')
        self.kelly_fraction = self.position_config.get('kelly_fraction', 0.25)
        self.min_position_size_usdt = self.position_config.get('min_position_size_usdt', 10)
        self.max_position_size_usdt = self.position_config.get('max_position_size_usdt', 1000)
        
        # Leverage config
        self.leverage_config = config.get('leverage', {})
        self.auto_leverage = self.leverage_config.get('auto_select', True)
        self.leverage_method = self.leverage_config.get('selection_method', 'volatility_based')
        self.volatility_leverage_map = self.leverage_config.get('volatility_leverage_map', {
            'low': 3,
            'medium': 2,
            'high': 1
        })
    
    def calculate_position_size(
        self, 
        capital: float, 
        entry_price: float, 
        stop_loss: float,
        win_rate: float = 0.5,
        avg_win: float = 0.02,
        avg_loss: float = 0.01
    ) -> float:
        """Calculate position size based on configured method"""
        
        if self.sizing_method == 'fixed':
            # Fixed percentage of capital
            position_value = capital * self.max_position_risk
            position_size = position_value / entry_price
        
        elif self.sizing_method == 'kelly_criterion':
            # Kelly Criterion: f = (p * b - q) / b
            # where p = win probability, q = loss probability, b = win/loss ratio
            b = avg_win / avg_loss if avg_loss > 0 else 1
            q = 1 - win_rate
            kelly_percentage = (win_rate * b - q) / b
            
            # Apply Kelly fraction (conservative)
            kelly_percentage = max(0, min(kelly_percentage * self.kelly_fraction, self.max_position_risk))
            
            position_value = capital * kelly_percentage
            position_size = position_value / entry_price
        
        elif self.sizing_method == 'volatility_based':
            # Position size inversely proportional to volatility
            risk_amount = capital * self.max_position_risk
            price_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / price_distance if price_distance > 0 else 0
        
        else:
            # Default to fixed
            position_value = capital * self.max_position_risk
            position_size = position_value / entry_price
        
        # Apply position size limits
        position_value_usdt = position_size * entry_price
        
        if position_value_usdt < self.min_position_size_usdt:
            position_size = self.min_position_size_usdt / entry_price
        elif position_value_usdt > self.max_position_size_usdt:
            position_size = self.max_position_size_usdt / entry_price
        
        return position_size
    
    def select_leverage(self, df: pd.DataFrame, volatility: Optional[float] = None) -> int:
        """Select optimal leverage based on volatility"""
        
        if not self.auto_leverage:
            return self.max_leverage
        
        if self.leverage_method == 'volatility_based':
            # Calculate volatility if not provided
            if volatility is None:
                from src.indicators import TechnicalIndicators
                volatility = TechnicalIndicators.calculate_volatility(df)
            
            # Map volatility to leverage
            if volatility < 0.03:  # Low volatility < 3%
                leverage = self.volatility_leverage_map.get('low', 3)
            elif volatility < 0.07:  # Medium volatility 3-7%
                leverage = self.volatility_leverage_map.get('medium', 2)
            else:  # High volatility > 7%
                leverage = self.volatility_leverage_map.get('high', 1)
            
            # Ensure leverage doesn't exceed maximum
            leverage = min(leverage, self.max_leverage)
            
            logger.info(f"Selected leverage: {leverage}x (volatility: {volatility:.2%})")
            return leverage
        
        else:
            # Default to max leverage
            return self.max_leverage
    
    def validate_trade(
        self, 
        signal: Dict, 
        current_positions: int, 
        portfolio_value: float,
        current_risk: float
    ) -> Dict:
        """Validate if trade meets risk criteria"""
        
        result = {
            'approved': False,
            'reason': '',
            'adjustments': {}
        }
        
        # Check if action is valid
        if signal.get('action') not in ['buy', 'sell']:
            result['reason'] = 'No valid trading action'
            return result
        
        # Check confidence threshold
        min_confidence = 0.5
        if signal.get('confidence', 0) < min_confidence:
            result['reason'] = f"Confidence too low: {signal.get('confidence', 0):.2f}"
            return result
        
        # Check risk-reward ratio
        entry = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit = signal.get('take_profit', 0)
        
        if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
            result['reason'] = 'Invalid price levels'
            return result
        
        risk = abs(entry - stop_loss) / entry
        reward = abs(take_profit - entry) / entry
        risk_reward = reward / risk if risk > 0 else 0
        
        if risk_reward < self.min_risk_reward_ratio:
            result['reason'] = f'Risk-reward ratio too low: {risk_reward:.2f}'
            return result
        
        # Check portfolio risk
        position_risk = risk * self.max_position_risk
        total_risk = current_risk + position_risk
        
        if total_risk > self.max_portfolio_risk:
            result['reason'] = f'Portfolio risk limit exceeded: {total_risk:.2%}'
            return result
        
        # Check max concurrent positions
        max_positions = self.config.get('general', {}).get('max_concurrent_positions', 5)
        if current_positions >= max_positions:
            result['reason'] = f'Max positions reached: {current_positions}'
            return result
        
        # All checks passed
        result['approved'] = True
        result['reason'] = 'Trade approved'
        result['risk_reward'] = risk_reward
        result['position_risk'] = position_risk
        
        return result
    
    def calculate_stop_loss_adjustment(
        self, 
        entry_price: float, 
        current_price: float, 
        initial_stop: float,
        side: str
    ) -> float:
        """Calculate trailing stop loss"""
        
        if not self.trailing_stop:
            return initial_stop
        
        if side == 'buy':
            # For long positions, adjust stop up as price increases
            profit_pct = (current_price - entry_price) / entry_price
            
            if profit_pct > self.trailing_stop_percentage:
                # Move stop to break-even + some profit
                new_stop = entry_price + (current_price - entry_price) * 0.5
                return max(new_stop, initial_stop)
            
            return initial_stop
        
        else:
            # For short positions, adjust stop down as price decreases
            profit_pct = (entry_price - current_price) / entry_price
            
            if profit_pct > self.trailing_stop_percentage:
                # Move stop to break-even + some profit
                new_stop = entry_price - (entry_price - current_price) * 0.5
                return min(new_stop, initial_stop)
            
            return initial_stop
    
    def check_stop_loss(self, position: Dict, current_price: float) -> bool:
        """Check if stop loss is hit"""
        stop_loss = position.get('stop_loss', 0)
        side = position.get('side', '')
        
        if side == 'buy':
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss
    
    def check_take_profit(self, position: Dict, current_price: float) -> bool:
        """Check if take profit is hit"""
        take_profit = position.get('take_profit', 0)
        side = position.get('side', '')
        
        if side == 'buy':
            return current_price >= take_profit
        else:
            return current_price <= take_profit
    
    def calculate_position_pnl(self, position: Dict, current_price: float) -> Dict:
        """Calculate position P&L"""
        entry_price = position.get('entry_price', 0)
        size = position.get('size', 0)
        side = position.get('side', '')
        leverage = position.get('leverage', 1)
        
        if side == 'buy':
            pnl = (current_price - entry_price) * size * leverage
            pnl_pct = ((current_price - entry_price) / entry_price) * leverage
        else:
            pnl = (entry_price - current_price) * size * leverage
            pnl_pct = ((entry_price - current_price) / entry_price) * leverage
        
        return {
            'pnl': pnl,
            'pnl_percentage': pnl_pct,
            'current_value': size * current_price
        }
    
    def get_portfolio_metrics(self, positions: list, current_prices: Dict) -> Dict:
        """Calculate portfolio-level metrics"""
        total_pnl = 0
        total_value = 0
        total_risk = 0
        
        for position in positions:
            symbol = position.get('symbol', '')
            current_price = current_prices.get(symbol, position.get('entry_price', 0))
            
            pnl_info = self.calculate_position_pnl(position, current_price)
            total_pnl += pnl_info['pnl']
            total_value += pnl_info['current_value']
            
            # Calculate risk per position
            entry = position.get('entry_price', 0)
            stop_loss = position.get('stop_loss', 0)
            if entry > 0:
                position_risk = abs(entry - stop_loss) / entry
                total_risk += position_risk
        
        return {
            'total_positions': len(positions),
            'total_pnl': total_pnl,
            'total_value': total_value,
            'total_risk': total_risk,
            'avg_pnl_per_position': total_pnl / len(positions) if positions else 0
        }

"""
Tests for Risk Manager
"""
import pytest
import pandas as pd
import numpy as np
from src.risk_manager import RiskManager
from src.indicators import TechnicalIndicators


@pytest.fixture
def config():
    """Sample configuration"""
    return {
        'risk_management': {
            'max_portfolio_risk': 0.2,
            'max_position_risk': 0.02,
            'max_leverage': 3,
            'min_risk_reward_ratio': 2.0,
            'trailing_stop': True,
            'trailing_stop_percentage': 0.05
        },
        'position_sizing': {
            'method': 'kelly_criterion',
            'kelly_fraction': 0.25,
            'min_position_size_usdt': 10,
            'max_position_size_usdt': 1000
        },
        'leverage': {
            'auto_select': True,
            'selection_method': 'volatility_based',
            'volatility_leverage_map': {
                'low': 3,
                'medium': 2,
                'high': 1
            },
            'max_leverage': 3
        },
        'general': {
            'max_concurrent_positions': 5
        }
    }


@pytest.fixture
def sample_df():
    """Generate sample dataframe"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    high = close + np.random.uniform(0, 2, 100)
    low = close - np.random.uniform(0, 2, 100)
    volume = np.random.uniform(1000, 10000, 100)
    
    df = pd.DataFrame({
        'open': close + np.random.uniform(-1, 1, 100),
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)
    
    return TechnicalIndicators.add_all_indicators(df)


def test_risk_manager_initialization(config):
    """Test risk manager initialization"""
    rm = RiskManager(config)
    
    assert rm.max_portfolio_risk == 0.2
    assert rm.max_position_risk == 0.02
    assert rm.max_leverage == 3
    assert rm.min_risk_reward_ratio == 2.0


def test_calculate_position_size_fixed(config):
    """Test fixed position sizing"""
    config['position_sizing']['method'] = 'fixed'
    rm = RiskManager(config)
    
    capital = 1000
    entry_price = 100
    stop_loss = 95
    
    size = rm.calculate_position_size(capital, entry_price, stop_loss)
    
    assert size > 0
    # For fixed method, position value should respect max position risk
    position_value = size * entry_price
    assert position_value <= capital * rm.max_position_risk or position_value <= rm.max_position_size_usdt


def test_calculate_position_size_kelly(config):
    """Test Kelly Criterion position sizing"""
    config['position_sizing']['method'] = 'kelly_criterion'
    rm = RiskManager(config)
    
    capital = 1000
    entry_price = 100
    stop_loss = 95
    win_rate = 0.6
    avg_win = 0.03
    avg_loss = 0.015
    
    size = rm.calculate_position_size(capital, entry_price, stop_loss, win_rate, avg_win, avg_loss)
    
    assert size > 0
    assert size * entry_price >= rm.min_position_size_usdt


def test_select_leverage_low_volatility(config, sample_df):
    """Test leverage selection with low volatility"""
    rm = RiskManager(config)
    
    leverage = rm.select_leverage(sample_df, volatility=0.02)
    
    assert leverage == 3  # Low volatility should use max leverage


def test_select_leverage_high_volatility(config, sample_df):
    """Test leverage selection with high volatility"""
    rm = RiskManager(config)
    
    leverage = rm.select_leverage(sample_df, volatility=0.10)
    
    assert leverage == 1  # High volatility should use min leverage


def test_validate_trade_success(config):
    """Test successful trade validation"""
    rm = RiskManager(config)
    
    signal = {
        'action': 'buy',
        'confidence': 0.8,
        'entry_price': 100,
        'stop_loss': 95,
        'take_profit': 110
    }
    
    result = rm.validate_trade(signal, current_positions=2, portfolio_value=1000, current_risk=0.05)
    
    assert result['approved'] is True
    assert result['risk_reward'] >= rm.min_risk_reward_ratio


def test_validate_trade_low_confidence(config):
    """Test trade rejection due to low confidence"""
    rm = RiskManager(config)
    
    signal = {
        'action': 'buy',
        'confidence': 0.3,
        'entry_price': 100,
        'stop_loss': 95,
        'take_profit': 110
    }
    
    result = rm.validate_trade(signal, current_positions=2, portfolio_value=1000, current_risk=0.05)
    
    assert result['approved'] is False


def test_validate_trade_poor_risk_reward(config):
    """Test trade rejection due to poor risk/reward"""
    rm = RiskManager(config)
    
    signal = {
        'action': 'buy',
        'confidence': 0.8,
        'entry_price': 100,
        'stop_loss': 95,
        'take_profit': 102,  # Only 0.4:1 reward:risk ratio
        'side': 'buy'
    }
    
    result = rm.validate_trade(signal, current_positions=2, portfolio_value=1000, current_risk=0.05)
    
    assert result['approved'] is False


def test_check_stop_loss_buy(config):
    """Test stop loss check for buy position"""
    rm = RiskManager(config)
    
    position = {
        'side': 'buy',
        'entry_price': 100,
        'stop_loss': 95
    }
    
    assert rm.check_stop_loss(position, 94) is True
    assert rm.check_stop_loss(position, 96) is False


def test_check_take_profit_buy(config):
    """Test take profit check for buy position"""
    rm = RiskManager(config)
    
    position = {
        'side': 'buy',
        'entry_price': 100,
        'take_profit': 110
    }
    
    assert rm.check_take_profit(position, 111) is True
    assert rm.check_take_profit(position, 109) is False


def test_calculate_position_pnl(config):
    """Test position P&L calculation"""
    rm = RiskManager(config)
    
    position = {
        'side': 'buy',
        'entry_price': 100,
        'size': 1.0,
        'leverage': 2
    }
    
    pnl_info = rm.calculate_position_pnl(position, 105)
    
    assert pnl_info['pnl'] == 10  # (105-100) * 1 * 2
    assert pnl_info['pnl_percentage'] == 0.1  # 5% * 2 leverage

"""
Tests for Technical Indicators
"""
import pytest
import pandas as pd
import numpy as np
from src.indicators import TechnicalIndicators


@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV data"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    high = close + np.random.uniform(0, 2, 100)
    low = close - np.random.uniform(0, 2, 100)
    open_price = close + np.random.uniform(-1, 1, 100)
    volume = np.random.uniform(1000, 10000, 100)
    
    data = []
    for i in range(100):
        data.append([
            int(dates[i].timestamp() * 1000),
            open_price[i],
            high[i],
            low[i],
            close[i],
            volume[i]
        ])
    
    return data


def test_prepare_dataframe(sample_ohlcv):
    """Test OHLCV data conversion to DataFrame"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100
    assert 'open' in df.columns
    assert 'high' in df.columns
    assert 'low' in df.columns
    assert 'close' in df.columns
    assert 'volume' in df.columns


def test_add_ema(sample_ohlcv):
    """Test EMA indicator"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_ema(df, period=20)
    
    assert 'ema_20' in df.columns
    assert not df['ema_20'].isna().all()


def test_add_rsi(sample_ohlcv):
    """Test RSI indicator"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_rsi(df)
    
    assert 'rsi' in df.columns
    # RSI has NaN values for the first few rows, exclude them
    valid_rsi = df['rsi'].dropna()
    assert (valid_rsi >= 0).all()
    assert (valid_rsi <= 100).all()


def test_add_macd(sample_ohlcv):
    """Test MACD indicator"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_macd(df)
    
    assert 'macd' in df.columns
    assert 'macd_signal' in df.columns
    assert 'macd_diff' in df.columns


def test_add_bollinger_bands(sample_ohlcv):
    """Test Bollinger Bands"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_bollinger_bands(df)
    
    assert 'bb_upper' in df.columns
    assert 'bb_middle' in df.columns
    assert 'bb_lower' in df.columns
    # Use small epsilon for floating point comparison, and exclude NaN values
    eps = 1e-8
    valid_mask = ~df['bb_upper'].isna() & ~df['bb_middle'].isna() & ~df['bb_lower'].isna()
    assert (df.loc[valid_mask, 'bb_upper'] >= df.loc[valid_mask, 'bb_middle'] - eps).all()
    assert (df.loc[valid_mask, 'bb_middle'] >= df.loc[valid_mask, 'bb_lower'] - eps).all()


def test_add_atr(sample_ohlcv):
    """Test ATR indicator"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_atr(df)
    
    assert 'atr' in df.columns
    assert (df['atr'] >= 0).all()


def test_add_all_indicators(sample_ohlcv):
    """Test adding all indicators"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_all_indicators(df)
    
    # Check that multiple indicators are present
    indicators = ['ema_12', 'ema_26', 'rsi', 'macd', 'bb_upper', 'atr', 'adx']
    for indicator in indicators:
        assert indicator in df.columns


def test_calculate_volatility(sample_ohlcv):
    """Test volatility calculation"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    volatility = TechnicalIndicators.calculate_volatility(df)
    
    assert isinstance(volatility, (float, np.floating))
    assert volatility >= 0


def test_calculate_trend_strength(sample_ohlcv):
    """Test trend strength calculation"""
    df = TechnicalIndicators.prepare_dataframe(sample_ohlcv)
    df = TechnicalIndicators.add_all_indicators(df)
    trend_strength = TechnicalIndicators.calculate_trend_strength(df)
    
    assert isinstance(trend_strength, (float, np.floating))
    assert 0 <= trend_strength <= 1

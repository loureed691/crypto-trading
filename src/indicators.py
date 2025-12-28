"""
Technical Indicators Module
"""
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
from typing import Dict, List

class TechnicalIndicators:
    """Calculate technical indicators for trading strategies"""
    
    @staticmethod
    def prepare_dataframe(ohlcv_data: List) -> pd.DataFrame:
        """Convert OHLCV data to pandas DataFrame"""
        df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    @staticmethod
    def add_ema(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.DataFrame:
        """Add Exponential Moving Average"""
        ema = EMAIndicator(close=df[column], window=period)
        df[f'ema_{period}'] = ema.ema_indicator()
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Relative Strength Index"""
        rsi = RSIIndicator(close=df['close'], window=period)
        df['rsi'] = rsi.rsi()
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Add MACD indicator"""
        macd = MACD(close=df['close'], window_fast=fast, window_slow=slow, window_sign=signal)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: int = 2) -> pd.DataFrame:
        """Add Bollinger Bands"""
        bb = BollingerBands(close=df['close'], window=period, window_dev=std)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average True Range"""
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period)
        df['atr'] = atr.average_true_range()
        return df
    
    @staticmethod
    def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average Directional Index"""
        adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=period)
        df['adx'] = adx.adx()
        df['adx_pos'] = adx.adx_pos()
        df['adx_neg'] = adx.adx_neg()
        return df
    
    @staticmethod
    def add_stochastic(df: pd.DataFrame, period: int = 14, smooth: int = 3) -> pd.DataFrame:
        """Add Stochastic Oscillator"""
        stoch = StochasticOscillator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=period,
            smooth_window=smooth
        )
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        return df
    
    @staticmethod
    def add_obv(df: pd.DataFrame) -> pd.DataFrame:
        """Add On-Balance Volume"""
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
        df['obv'] = obv.on_balance_volume()
        return df
    
    @staticmethod
    def calculate_volatility(df: pd.DataFrame, period: int = 20) -> float:
        """Calculate historical volatility"""
        log_returns = np.log(df['close'] / df['close'].shift(1))
        volatility = log_returns.rolling(window=period).std() * np.sqrt(365)
        return volatility.iloc[-1] if len(volatility) > 0 else 0.0
    
    @staticmethod
    def calculate_trend_strength(df: pd.DataFrame) -> float:
        """Calculate trend strength using ADX"""
        if 'adx' not in df.columns:
            df = TechnicalIndicators.add_adx(df)
        
        adx_value = df['adx'].iloc[-1] if len(df) > 0 else 0
        # Normalize ADX to 0-1 scale (ADX ranges from 0-100)
        return min(adx_value / 100, 1.0)
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
        """Add all technical indicators"""
        if config is None:
            config = {}
        
        # Trend indicators
        df = TechnicalIndicators.add_ema(df, 12)
        df = TechnicalIndicators.add_ema(df, 26)
        df = TechnicalIndicators.add_ema(df, 50)
        df = TechnicalIndicators.add_ema(df, 200)
        df = TechnicalIndicators.add_macd(df)
        df = TechnicalIndicators.add_adx(df)
        
        # Momentum indicators
        df = TechnicalIndicators.add_rsi(df)
        df = TechnicalIndicators.add_stochastic(df)
        
        # Volatility indicators
        df = TechnicalIndicators.add_bollinger_bands(df)
        df = TechnicalIndicators.add_atr(df)
        
        # Volume indicators
        df = TechnicalIndicators.add_obv(df)
        
        return df
    
    @staticmethod
    def detect_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict:
        """Detect support and resistance levels"""
        highs = df['high'].rolling(window=window, center=True).max()
        lows = df['low'].rolling(window=window, center=True).min()
        
        resistance_levels = []
        support_levels = []
        
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == highs.iloc[i]:
                resistance_levels.append(df['high'].iloc[i])
            if df['low'].iloc[i] == lows.iloc[i]:
                support_levels.append(df['low'].iloc[i])
        
        return {
            'resistance': sorted(set(resistance_levels), reverse=True)[:3],
            'support': sorted(set(support_levels))[:3]
        }

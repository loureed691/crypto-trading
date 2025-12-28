"""
Trading Strategies Module
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict
from loguru import logger
from src.indicators import TechnicalIndicators

class Strategy(ABC):
    """Base class for trading strategies"""
    
    def __init__(self, config: Dict):
        """Initialize strategy"""
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate trading signal"""
        pass
    
    def calculate_stop_loss(self, df: pd.DataFrame, side: str, entry_price: float) -> float:
        """Calculate stop loss price"""
        if 'atr' not in df.columns:
            df = TechnicalIndicators.add_atr(df)
        
        atr = df['atr'].iloc[-1]
        multiplier = 1.5  # ATR multiplier for stop loss
        
        if side == 'buy':
            return entry_price - (atr * multiplier)
        else:
            return entry_price + (atr * multiplier)
    
    def calculate_take_profit(self, df: pd.DataFrame, side: str, entry_price: float, risk_reward: float = 2.0) -> float:
        """Calculate take profit price"""
        stop_loss = self.calculate_stop_loss(df, side, entry_price)
        risk = abs(entry_price - stop_loss)
        
        if side == 'buy':
            return entry_price + (risk * risk_reward)
        else:
            return entry_price - (risk * risk_reward)


class TrendFollowingStrategy(Strategy):
    """Trend following strategy using EMA and ADX"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ema_fast = config.get('ema_fast', 12)
        self.ema_slow = config.get('ema_slow', 26)
        self.atr_period = config.get('atr_period', 14)
        self.min_trend_strength = config.get('min_trend_strength', 0.6)
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate trend following signal"""
        try:
            # Add indicators if not present
            if f'ema_{self.ema_fast}' not in df.columns:
                df = TechnicalIndicators.add_ema(df, self.ema_fast)
            if f'ema_{self.ema_slow}' not in df.columns:
                df = TechnicalIndicators.add_ema(df, self.ema_slow)
            if 'adx' not in df.columns:
                df = TechnicalIndicators.add_adx(df)
            if 'atr' not in df.columns:
                df = TechnicalIndicators.add_atr(df)
            
            # Get latest values
            ema_fast = df[f'ema_{self.ema_fast}'].iloc[-1]
            ema_slow = df[f'ema_{self.ema_slow}'].iloc[-1]
            ema_fast_prev = df[f'ema_{self.ema_fast}'].iloc[-2]
            ema_slow_prev = df[f'ema_{self.ema_slow}'].iloc[-2]
            adx = df['adx'].iloc[-1]
            close = df['close'].iloc[-1]
            
            # Calculate trend strength
            trend_strength = TechnicalIndicators.calculate_trend_strength(df)
            
            signal = {
                'action': 'hold',
                'side': None,
                'confidence': 0.0,
                'entry_price': close,
                'stop_loss': None,
                'take_profit': None,
                'reason': ''
            }
            
            # Check for strong trend
            if trend_strength < self.min_trend_strength:
                signal['reason'] = f'Weak trend (ADX: {adx:.2f})'
                return signal
            
            # Bullish crossover
            if ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev:
                signal['action'] = 'buy'
                signal['side'] = 'buy'
                signal['confidence'] = trend_strength
                signal['stop_loss'] = self.calculate_stop_loss(df, 'buy', close)
                signal['take_profit'] = self.calculate_take_profit(df, 'buy', close)
                signal['reason'] = f'Bullish EMA crossover (ADX: {adx:.2f})'
            
            # Bearish crossover
            elif ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev:
                signal['action'] = 'sell'
                signal['side'] = 'sell'
                signal['confidence'] = trend_strength
                signal['stop_loss'] = self.calculate_stop_loss(df, 'sell', close)
                signal['take_profit'] = self.calculate_take_profit(df, 'sell', close)
                signal['reason'] = f'Bearish EMA crossover (ADX: {adx:.2f})'
            
            # Continue trend
            elif ema_fast > ema_slow and adx > 25:
                signal['reason'] = f'Strong uptrend continuing (ADX: {adx:.2f})'
            elif ema_fast < ema_slow and adx > 25:
                signal['reason'] = f'Strong downtrend continuing (ADX: {adx:.2f})'
            
            return signal
        except Exception as e:
            logger.error(f"Error in trend following strategy: {e}")
            return {'action': 'hold', 'side': None, 'confidence': 0.0, 'reason': f'Error: {e}'}


class MeanReversionStrategy(Strategy):
    """Mean reversion strategy using Bollinger Bands and RSI"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate mean reversion signal"""
        try:
            # Add indicators
            if 'bb_upper' not in df.columns:
                df = TechnicalIndicators.add_bollinger_bands(df, self.bb_period, self.bb_std)
            if 'rsi' not in df.columns:
                df = TechnicalIndicators.add_rsi(df, self.rsi_period)
            
            # Get latest values
            close = df['close'].iloc[-1]
            bb_upper = df['bb_upper'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            bb_middle = df['bb_middle'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            
            signal = {
                'action': 'hold',
                'side': None,
                'confidence': 0.0,
                'entry_price': close,
                'stop_loss': None,
                'take_profit': None,
                'reason': ''
            }
            
            # Oversold condition (buy signal)
            if close <= bb_lower and rsi <= self.rsi_oversold:
                confidence = 1.0 - (rsi / 100)  # Lower RSI = higher confidence
                signal['action'] = 'buy'
                signal['side'] = 'buy'
                signal['confidence'] = confidence
                signal['stop_loss'] = self.calculate_stop_loss(df, 'buy', close)
                signal['take_profit'] = bb_middle  # Target mean
                signal['reason'] = f'Oversold (RSI: {rsi:.2f}, at lower BB)'
            
            # Overbought condition (sell signal)
            elif close >= bb_upper and rsi >= self.rsi_overbought:
                confidence = rsi / 100  # Higher RSI = higher confidence
                signal['action'] = 'sell'
                signal['side'] = 'sell'
                signal['confidence'] = confidence
                signal['stop_loss'] = self.calculate_stop_loss(df, 'sell', close)
                signal['take_profit'] = bb_middle  # Target mean
                signal['reason'] = f'Overbought (RSI: {rsi:.2f}, at upper BB)'
            
            return signal
        except Exception as e:
            logger.error(f"Error in mean reversion strategy: {e}")
            return {'action': 'hold', 'side': None, 'confidence': 0.0, 'reason': f'Error: {e}'}


class BreakoutStrategy(Strategy):
    """Breakout strategy using volume and price action"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.lookback_period = config.get('lookback_period', 20)
        self.volume_surge_threshold = config.get('volume_surge_threshold', 2.0)
        self.consolidation_period = config.get('consolidation_period', 10)
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate breakout signal"""
        try:
            # Calculate price range
            high_max = df['high'].rolling(window=self.lookback_period).max()
            low_min = df['low'].rolling(window=self.lookback_period).min()
            avg_volume = df['volume'].rolling(window=self.lookback_period).mean()
            
            # Get latest values
            close = df['close'].iloc[-1]
            volume = df['volume'].iloc[-1]
            resistance = high_max.iloc[-2]  # Previous period high
            support = low_min.iloc[-2]  # Previous period low
            avg_vol = avg_volume.iloc[-1]
            
            signal = {
                'action': 'hold',
                'side': None,
                'confidence': 0.0,
                'entry_price': close,
                'stop_loss': None,
                'take_profit': None,
                'reason': ''
            }
            
            # Check for volume surge
            volume_surge = volume / avg_vol if avg_vol > 0 else 0
            
            # Bullish breakout
            if close > resistance and volume_surge >= self.volume_surge_threshold:
                confidence = min(volume_surge / (self.volume_surge_threshold * 2), 1.0)
                signal['action'] = 'buy'
                signal['side'] = 'buy'
                signal['confidence'] = confidence
                signal['stop_loss'] = resistance  # Previous resistance becomes support
                signal['take_profit'] = close + (close - resistance) * 2  # 2x range
                signal['reason'] = f'Bullish breakout (Vol surge: {volume_surge:.2f}x)'
            
            # Bearish breakdown
            elif close < support and volume_surge >= self.volume_surge_threshold:
                confidence = min(volume_surge / (self.volume_surge_threshold * 2), 1.0)
                signal['action'] = 'sell'
                signal['side'] = 'sell'
                signal['confidence'] = confidence
                signal['stop_loss'] = support  # Previous support becomes resistance
                signal['take_profit'] = close - (support - close) * 2  # 2x range
                signal['reason'] = f'Bearish breakdown (Vol surge: {volume_surge:.2f}x)'
            
            return signal
        except Exception as e:
            logger.error(f"Error in breakout strategy: {e}")
            return {'action': 'hold', 'side': None, 'confidence': 0.0, 'reason': f'Error: {e}'}


class MomentumStrategy(Strategy):
    """Momentum strategy using MACD and trend strength"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.macd_fast = config.get('macd_fast', 12)
        self.macd_slow = config.get('macd_slow', 26)
        self.macd_signal = config.get('macd_signal', 9)
        self.momentum_threshold = config.get('momentum_threshold', 0.5)
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate momentum signal"""
        try:
            # Add indicators
            if 'macd' not in df.columns:
                df = TechnicalIndicators.add_macd(df, self.macd_fast, self.macd_slow, self.macd_signal)
            
            # Get latest values
            macd = df['macd'].iloc[-1]
            macd_diff = df['macd_diff'].iloc[-1]
            macd_diff_prev = df['macd_diff'].iloc[-2]
            close = df['close'].iloc[-1]
            
            signal = {
                'action': 'hold',
                'side': None,
                'confidence': 0.0,
                'entry_price': close,
                'stop_loss': None,
                'take_profit': None,
                'reason': ''
            }
            
            # Bullish MACD crossover
            if macd_diff > 0 and macd_diff_prev <= 0 and macd > 0:
                confidence = min(abs(macd_diff) / (close * 0.01), 1.0)  # Normalize by price
                signal['action'] = 'buy'
                signal['side'] = 'buy'
                signal['confidence'] = confidence
                signal['stop_loss'] = self.calculate_stop_loss(df, 'buy', close)
                signal['take_profit'] = self.calculate_take_profit(df, 'buy', close, 2.5)
                signal['reason'] = f'Bullish MACD crossover (MACD: {macd:.4f})'
            
            # Bearish MACD crossover
            elif macd_diff < 0 and macd_diff_prev >= 0 and macd < 0:
                confidence = min(abs(macd_diff) / (close * 0.01), 1.0)
                signal['action'] = 'sell'
                signal['side'] = 'sell'
                signal['confidence'] = confidence
                signal['stop_loss'] = self.calculate_stop_loss(df, 'sell', close)
                signal['take_profit'] = self.calculate_take_profit(df, 'sell', close, 2.5)
                signal['reason'] = f'Bearish MACD crossover (MACD: {macd:.4f})'
            
            return signal
        except Exception as e:
            logger.error(f"Error in momentum strategy: {e}")
            return {'action': 'hold', 'side': None, 'confidence': 0.0, 'reason': f'Error: {e}'}


class StrategySelector:
    """Selects the best strategy based on market conditions"""
    
    def __init__(self, config: Dict):
        """Initialize strategy selector"""
        self.config = config
        self.strategies = {}
        
        # Initialize enabled strategies
        enabled_strategies = config.get('strategies', {}).get('enabled', [])
        
        if 'trend_following' in enabled_strategies:
            self.strategies['trend_following'] = TrendFollowingStrategy(
                config.get('strategies', {}).get('trend_following', {})
            )
        
        if 'mean_reversion' in enabled_strategies:
            self.strategies['mean_reversion'] = MeanReversionStrategy(
                config.get('strategies', {}).get('mean_reversion', {})
            )
        
        if 'breakout' in enabled_strategies:
            self.strategies['breakout'] = BreakoutStrategy(
                config.get('strategies', {}).get('breakout', {})
            )
        
        if 'momentum' in enabled_strategies:
            self.strategies['momentum'] = MomentumStrategy(
                config.get('strategies', {}).get('momentum', {})
            )
        
        logger.info(f"Initialized {len(self.strategies)} strategies: {list(self.strategies.keys())}")
    
    def analyze_market_condition(self, df: pd.DataFrame) -> str:
        """Analyze current market condition"""
        try:
            # Add necessary indicators
            if 'adx' not in df.columns:
                df = TechnicalIndicators.add_adx(df)
            if 'bb_width' not in df.columns:
                df = TechnicalIndicators.add_bollinger_bands(df)
            
            adx = df['adx'].iloc[-1]
            bb_width = df['bb_width'].iloc[-1]
            volatility = TechnicalIndicators.calculate_volatility(df)
            
            # Determine market condition
            if adx > 25 and bb_width > 0.05:
                return 'trending'
            elif bb_width < 0.02 and volatility < 0.03:
                return 'ranging'
            elif volatility > 0.08:
                return 'volatile'
            else:
                return 'neutral'
        except Exception as e:
            logger.error(f"Error analyzing market condition: {e}")
            return 'neutral'
    
    def select_strategy(self, df: pd.DataFrame) -> str:
        """Select best strategy based on market conditions"""
        market_condition = self.analyze_market_condition(df)
        
        # Map market conditions to strategies
        strategy_map = {
            'trending': 'trend_following',
            'ranging': 'mean_reversion',
            'volatile': 'breakout',
            'neutral': 'momentum'
        }
        
        selected = strategy_map.get(market_condition, 'momentum')
        
        # Fallback if selected strategy not available
        if selected not in self.strategies and len(self.strategies) > 0:
            selected = list(self.strategies.keys())[0]
        
        logger.info(f"Market condition: {market_condition}, Selected strategy: {selected}")
        return selected
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Generate trading signal using best strategy"""
        try:
            # Add all indicators to dataframe
            df = TechnicalIndicators.add_all_indicators(df)
            
            # Select best strategy
            strategy_name = self.select_strategy(df)
            
            if strategy_name not in self.strategies:
                logger.warning(f"Strategy {strategy_name} not available")
                return {'action': 'hold', 'side': None, 'confidence': 0.0, 'reason': 'No strategy available'}
            
            # Generate signal
            strategy = self.strategies[strategy_name]
            signal = strategy.generate_signal(df)
            signal['strategy'] = strategy_name
            signal['symbol'] = symbol
            
            logger.info(f"{symbol} - {strategy_name}: {signal['action']} ({signal['reason']})")
            
            return signal
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return {'action': 'hold', 'side': None, 'confidence': 0.0, 'reason': f'Error: {e}'}

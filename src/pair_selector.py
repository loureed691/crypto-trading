"""
Automated Pair Selection Module
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from loguru import logger
from src.indicators import TechnicalIndicators

class PairSelector:
    """Selects optimal trading pairs based on multiple criteria"""
    
    def __init__(self, exchange, config: Dict):
        """Initialize pair selector"""
        self.exchange = exchange
        self.config = config
        self.pair_config = config.get('pair_selection', {})
        
    def calculate_liquidity_score(self, order_book: Dict) -> float:
        """Calculate liquidity score from order book depth"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            # Calculate bid-ask spread
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else 0
            
            if best_bid == 0 or best_ask == 0:
                return 0.0
            
            spread = (best_ask - best_bid) / best_bid
            
            # Calculate depth (volume in top 5 levels)
            bid_depth = sum([bid[1] for bid in bids[:5]]) if len(bids) >= 5 else 0
            ask_depth = sum([ask[1] for ask in asks[:5]]) if len(asks) >= 5 else 0
            total_depth = bid_depth + ask_depth
            
            # Liquidity score (inverse of spread, weighted by depth)
            # Lower spread and higher depth = better liquidity
            if spread > 0:
                liquidity_score = (1 / spread) * (total_depth / 1000)
                return min(liquidity_score / 100, 1.0)  # Normalize to 0-1
            
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating liquidity score: {e}")
            return 0.0
    
    def calculate_volatility_score(self, df: pd.DataFrame) -> float:
        """Calculate volatility score"""
        try:
            # Calculate daily returns
            returns = df['close'].pct_change()
            daily_volatility = returns.std()
            
            # Check if volatility is within acceptable range
            min_vol = self.pair_config.get('volatility_range', {}).get('min', 0.02)
            max_vol = self.pair_config.get('volatility_range', {}).get('max', 0.15)
            
            if min_vol <= daily_volatility <= max_vol:
                # Optimal volatility, return high score
                return 1.0
            elif daily_volatility < min_vol:
                # Too low volatility
                return daily_volatility / min_vol
            else:
                # Too high volatility
                return max_vol / daily_volatility
        except Exception as e:
            logger.error(f"Error calculating volatility score: {e}")
            return 0.0
    
    def calculate_volume_score(self, ticker: Dict) -> float:
        """Calculate volume score"""
        try:
            volume_usdt = ticker.get('quoteVolume', 0)
            min_volume = self.pair_config.get('min_24h_volume_usdt', 1000000)
            
            if volume_usdt >= min_volume:
                # Normalize: volume above minimum gets higher score
                return min(volume_usdt / (min_volume * 10), 1.0)
            else:
                return volume_usdt / min_volume
        except Exception as e:
            logger.error(f"Error calculating volume score: {e}")
            return 0.0
    
    def calculate_trend_score(self, df: pd.DataFrame) -> float:
        """Calculate trend score"""
        try:
            # Add technical indicators if not present
            if 'adx' not in df.columns:
                df = TechnicalIndicators.add_adx(df)
            if 'ema_12' not in df.columns:
                df = TechnicalIndicators.add_ema(df, 12)
            if 'ema_26' not in df.columns:
                df = TechnicalIndicators.add_ema(df, 26)
            
            # Strong trend indicated by ADX > 25
            adx = df['adx'].iloc[-1]
            adx_score = min(adx / 50, 1.0)  # Normalize
            
            # Trend direction from EMA crossover
            ema_12 = df['ema_12'].iloc[-1]
            ema_26 = df['ema_26'].iloc[-1]
            trend_direction = 1.0 if ema_12 > ema_26 else 0.5
            
            return adx_score * trend_direction
        except Exception as e:
            logger.error(f"Error calculating trend score: {e}")
            return 0.0
    
    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """Calculate momentum score"""
        try:
            if 'rsi' not in df.columns:
                df = TechnicalIndicators.add_rsi(df)
            
            rsi = df['rsi'].iloc[-1]
            
            # RSI between 40-60 is neutral (best for entries)
            # RSI > 70 is overbought, < 30 is oversold
            if 40 <= rsi <= 60:
                return 1.0
            elif rsi > 60:
                return 1.0 - (rsi - 60) / 40
            else:
                return 1.0 - (40 - rsi) / 40
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return 0.0
    
    def score_pair(self, symbol: str, ticker: Dict, ohlcv: List, order_book: Dict) -> float:
        """Calculate overall score for a trading pair"""
        try:
            # Convert OHLCV to DataFrame
            df = TechnicalIndicators.prepare_dataframe(ohlcv)
            
            if len(df) < 30:  # Need enough data
                return 0.0
            
            # Calculate individual scores
            volume_score = self.calculate_volume_score(ticker)
            volatility_score = self.calculate_volatility_score(df)
            liquidity_score = self.calculate_liquidity_score(order_book)
            trend_score = self.calculate_trend_score(df)
            momentum_score = self.calculate_momentum_score(df)
            
            # Weighted average (customize weights as needed)
            weights = {
                'volume': 0.25,
                'volatility': 0.20,
                'liquidity': 0.20,
                'trend': 0.20,
                'momentum': 0.15
            }
            
            overall_score = (
                weights['volume'] * volume_score +
                weights['volatility'] * volatility_score +
                weights['liquidity'] * liquidity_score +
                weights['trend'] * trend_score +
                weights['momentum'] * momentum_score
            )
            
            logger.debug(f"{symbol} - Volume: {volume_score:.2f}, Vol: {volatility_score:.2f}, "
                        f"Liq: {liquidity_score:.2f}, Trend: {trend_score:.2f}, "
                        f"Mom: {momentum_score:.2f}, Overall: {overall_score:.2f}")
            
            return overall_score
        except Exception as e:
            logger.error(f"Error scoring pair {symbol}: {e}")
            return 0.0
    
    def filter_pairs(self, tickers: Dict) -> List[str]:
        """Filter pairs based on basic criteria"""
        filtered = []
        
        preferred_quotes = self.pair_config.get('preferred_quote_currencies', ['USDT'])
        blacklist = self.pair_config.get('blacklist', [])
        min_volume = self.pair_config.get('min_24h_volume_usdt', 1000000)
        
        for symbol, ticker in tickers.items():
            # Check if symbol is blacklisted
            if symbol in blacklist:
                continue
            
            # Check quote currency
            quote = symbol.split('/')[-1] if '/' in symbol else ''
            if quote not in preferred_quotes:
                continue
            
            # Check minimum volume
            volume_usdt = ticker.get('quoteVolume', 0)
            if volume_usdt < min_volume:
                continue
            
            filtered.append(symbol)
        
        logger.info(f"Filtered {len(filtered)} pairs from {len(tickers)} total")
        return filtered
    
    async def select_best_pairs(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """Select top N best trading pairs"""
        try:
            logger.info("Starting pair selection process...")
            
            # Fetch all tickers
            tickers = self.exchange.fetch_tickers()
            
            # Filter pairs
            candidate_pairs = self.filter_pairs(tickers)
            
            if not candidate_pairs:
                logger.warning("No candidate pairs found")
                return []
            
            # Score each pair
            pair_scores = []
            
            for symbol in candidate_pairs[:50]:  # Limit to top 50 by volume for efficiency
                try:
                    ticker = tickers[symbol]
                    ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=100)
                    order_book = self.exchange.fetch_order_book(symbol, limit=20)
                    
                    score = self.score_pair(symbol, ticker, ohlcv, order_book)
                    
                    if score > 0:
                        pair_scores.append((symbol, score))
                except Exception as e:
                    logger.debug(f"Error processing {symbol}: {e}")
                    continue
            
            # Sort by score and return top N
            pair_scores.sort(key=lambda x: x[1], reverse=True)
            selected = pair_scores[:top_n]
            
            logger.info(f"Selected top {len(selected)} pairs:")
            for symbol, score in selected:
                logger.info(f"  {symbol}: {score:.3f}")
            
            return selected
        except Exception as e:
            logger.error(f"Error in pair selection: {e}")
            return []

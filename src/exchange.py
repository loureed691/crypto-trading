"""
KuCoin Exchange API Integration
"""
import ccxt
import asyncio
from typing import Dict, List, Optional, Tuple
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

class KuCoinAPI:
    """Wrapper for KuCoin API operations"""
    
    def __init__(self, api_key: str, api_secret: str, api_passphrase: str, testnet: bool = False):
        """Initialize KuCoin exchange connection"""
        self.exchange = ccxt.kucoin({
            'apiKey': api_key,
            'secret': api_secret,
            'password': api_passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if testnet else 'spot',
            }
        })
        
        if testnet:
            self.exchange.set_sandbox_mode(True)
        
        self.markets = None
        self.balance = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def load_markets(self):
        """Load market information"""
        try:
            self.markets = self.exchange.load_markets()
            logger.info(f"Loaded {len(self.markets)} markets from KuCoin")
            return self.markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_balance(self) -> Dict:
        """Fetch account balance"""
        try:
            self.balance = self.exchange.fetch_balance()
            return self.balance
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch ticker data for a symbol"""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_tickers(self) -> Dict:
        """Fetch all tickers"""
        try:
            return self.exchange.fetch_tickers()
        except Exception as e:
            logger.error(f"Failed to fetch tickers: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ohlcv(self, symbol: str, timeframe: str = '15m', limit: int = 100) -> List:
        """Fetch OHLCV data"""
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """Fetch order book"""
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to fetch order book for {symbol}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def create_order(
        self, 
        symbol: str, 
        order_type: str, 
        side: str, 
        amount: float, 
        price: Optional[float] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Create an order"""
        try:
            logger.info(f"Creating {side} {order_type} order for {symbol}: {amount} @ {price}")
            return self.exchange.create_order(symbol, order_type, side, amount, price, params or {})
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def create_market_order(self, symbol: str, side: str, amount: float, params: Optional[Dict] = None) -> Dict:
        """Create a market order"""
        return self.create_order(symbol, 'market', side, amount, None, params)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def create_limit_order(self, symbol: str, side: str, amount: float, price: float, params: Optional[Dict] = None) -> Dict:
        """Create a limit order"""
        return self.create_order(symbol, 'limit', side, amount, price, params)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order"""
        try:
            logger.info(f"Cancelling order {order_id} for {symbol}")
            return self.exchange.cancel_order(order_id, symbol)
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_open_orders(self, symbol: Optional[str] = None) -> List:
        """Fetch open orders"""
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_order(self, order_id: str, symbol: str) -> Dict:
        """Fetch order details"""
        try:
            return self.exchange.fetch_order(order_id, symbol)
        except Exception as e:
            logger.error(f"Failed to fetch order: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def set_leverage(self, leverage: int, symbol: str) -> Dict:
        """Set leverage for a symbol"""
        try:
            logger.info(f"Setting leverage to {leverage}x for {symbol}")
            return self.exchange.set_leverage(leverage, symbol)
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            raise
    
    def calculate_position_size(self, capital: float, risk: float, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk"""
        risk_amount = capital * risk
        price_distance = abs(entry_price - stop_loss)
        position_size = risk_amount / price_distance
        return position_size
    
    def get_trading_fee(self) -> float:
        """Get trading fee"""
        # KuCoin typically charges 0.1% for spot trading
        return 0.001
    
    def get_min_order_size(self, symbol: str) -> float:
        """Get minimum order size for a symbol"""
        if self.markets and symbol in self.markets:
            limits = self.markets[symbol].get('limits', {})
            amount_min = limits.get('amount', {}).get('min', 0.0)
            return amount_min
        return 0.0
    
    def close(self):
        """Close the exchange connection"""
        if hasattr(self.exchange, 'close'):
            self.exchange.close()

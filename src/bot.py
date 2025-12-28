"""
Main Trading Bot Module
"""
import asyncio
import time
from typing import Dict, List, Optional
from loguru import logger
import sys

from src.config import Config
from src.exchange import KuCoinAPI
from src.pair_selector import PairSelector
from src.strategies import StrategySelector
from src.risk_manager import RiskManager
from src.database import Database
from src.indicators import TechnicalIndicators

class TradingBot:
    """Automated cryptocurrency trading bot"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize trading bot"""
        logger.info("Initializing Trading Bot...")
        
        # Load configuration
        self.config = Config(config_path)
        self.config.validate()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.exchange = KuCoinAPI(
            self.config.api_key,
            self.config.api_secret,
            self.config.api_passphrase,
            testnet=self.config.is_testnet()
        )
        
        self.pair_selector = PairSelector(self.exchange, self.config.config)
        self.strategy_selector = StrategySelector(self.config.config)
        self.risk_manager = RiskManager(self.config.config)
        self.database = Database(self.config.database_url)
        
        # Bot state
        self.running = False
        self.positions = {}  # symbol -> position dict
        self.capital = self.config.initial_capital
        self.portfolio_value = self.capital
        
        logger.info(f"Trading Bot initialized in {self.config.trading_mode} mode")
        logger.info(f"Initial capital: ${self.capital:.2f}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logger.remove()
        logger.add(
            sys.stderr,
            level=self.config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
        logger.add(
            "logs/trading_bot_{time}.log",
            rotation="1 day",
            retention="30 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
        )
    
    async def initialize(self):
        """Initialize bot resources"""
        try:
            logger.info("Loading markets...")
            self.exchange.load_markets()
            
            logger.info("Fetching initial balance...")
            balance = self.exchange.fetch_balance()
            
            # Update capital based on actual balance
            if 'USDT' in balance['total']:
                actual_balance = balance['total']['USDT']
                if actual_balance > 0:
                    self.capital = actual_balance
                    self.portfolio_value = actual_balance
                    logger.info(f"Updated capital from balance: ${self.capital:.2f}")
            
            logger.info("Bot initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def select_trading_pairs(self) -> List[str]:
        """Select best trading pairs"""
        try:
            max_positions = self.config.get('general.max_concurrent_positions', 5)
            pairs = await self.pair_selector.select_best_pairs(top_n=max_positions)
            return [symbol for symbol, score in pairs]
        except Exception as e:
            logger.error(f"Error selecting pairs: {e}")
            return []
    
    def analyze_pair(self, symbol: str) -> Optional[Dict]:
        """Analyze a trading pair and generate signal"""
        try:
            # Fetch market data
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=200)
            
            if len(ohlcv) < 50:
                logger.debug(f"Insufficient data for {symbol}")
                return None
            
            # Prepare dataframe
            df = TechnicalIndicators.prepare_dataframe(ohlcv)
            
            # Generate signal
            signal = self.strategy_selector.generate_signal(df, symbol)
            
            # Add volatility and leverage
            volatility = TechnicalIndicators.calculate_volatility(df)
            leverage = self.risk_manager.select_leverage(df, volatility)
            
            signal['volatility'] = volatility
            signal['leverage'] = leverage
            
            return signal
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def execute_signal(self, signal: Dict) -> bool:
        """Execute trading signal"""
        try:
            symbol = signal.get('symbol')
            action = signal.get('action')
            
            if action not in ['buy', 'sell']:
                return False
            
            # Get current positions and risk
            open_positions = len(self.positions)
            current_risk = sum([abs(p['entry_price'] - p['stop_loss']) / p['entry_price'] 
                               for p in self.positions.values()])
            
            # Validate trade with risk manager
            validation = self.risk_manager.validate_trade(
                signal, 
                open_positions, 
                self.portfolio_value, 
                current_risk
            )
            
            if not validation['approved']:
                logger.info(f"Trade rejected: {validation['reason']}")
                return False
            
            # Calculate position size
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            leverage = signal.get('leverage', 1)
            
            position_size = self.risk_manager.calculate_position_size(
                self.capital,
                entry_price,
                stop_loss
            )
            
            # Check minimum order size
            min_size = self.exchange.get_min_order_size(symbol)
            if position_size < min_size:
                logger.warning(f"Position size {position_size} below minimum {min_size}")
                position_size = min_size
            
            # Set leverage if applicable
            if leverage > 1:
                try:
                    self.exchange.set_leverage(leverage, symbol)
                except Exception as e:
                    logger.warning(f"Failed to set leverage: {e}")
                    leverage = 1
            
            # Execute order
            side = signal['side']
            order = self.exchange.create_market_order(symbol, side, position_size)
            
            if order:
                # Get actual fill price from order
                actual_entry_price = order.get('average') or order.get('price') or entry_price
                
                # Record trade in database
                trade_data = {
                    'symbol': symbol,
                    'strategy': signal.get('strategy', 'unknown'),
                    'side': side,
                    'entry_price': actual_entry_price,
                    'size': position_size,
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': signal.get('take_profit'),
                    'order_id': order.get('id'),
                    'status': 'open'
                }
                
                trade = self.database.add_trade(trade_data)
                
                # Add to positions
                self.positions[symbol] = {
                    'trade_id': trade.id,
                    'symbol': symbol,
                    'side': side,
                    'entry_price': actual_entry_price,
                    'size': position_size,
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': signal.get('take_profit'),
                    'entry_time': time.time()
                }
                
                logger.info(f"✓ Opened {side} position: {symbol} @ ${entry_price:.4f} "
                           f"(Size: {position_size:.4f}, Leverage: {leverage}x)")
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False
    
    def monitor_positions(self):
        """Monitor and manage open positions"""
        try:
            if not self.positions:
                return
            
            symbols_to_close = []
            
            for symbol, position in self.positions.items():
                try:
                    # Get current price
                    ticker = self.exchange.fetch_ticker(symbol)
                    current_price = ticker['last']
                    
                    # Update trailing stop
                    new_stop = self.risk_manager.calculate_stop_loss_adjustment(
                        position['entry_price'],
                        current_price,
                        position['stop_loss'],
                        position['side']
                    )
                    
                    if new_stop != position['stop_loss']:
                        position['stop_loss'] = new_stop
                        logger.info(f"Updated trailing stop for {symbol}: ${new_stop:.4f}")
                    
                    # Check stop loss
                    if self.risk_manager.check_stop_loss(position, current_price):
                        logger.warning(f"Stop loss hit for {symbol}")
                        self.close_position(symbol, current_price, 'stop_loss')
                        symbols_to_close.append(symbol)
                    
                    # Check take profit
                    elif self.risk_manager.check_take_profit(position, current_price):
                        logger.info(f"Take profit hit for {symbol}")
                        self.close_position(symbol, current_price, 'take_profit')
                        symbols_to_close.append(symbol)
                    
                    else:
                        # Log current P&L
                        pnl_info = self.risk_manager.calculate_position_pnl(position, current_price)
                        logger.debug(f"{symbol}: P&L = ${pnl_info['pnl']:.2f} ({pnl_info['pnl_percentage']:.2%})")
                
                except Exception as e:
                    logger.error(f"Error monitoring position {symbol}: {e}")
            
            # Remove closed positions
            for symbol in symbols_to_close:
                del self.positions[symbol]
        
        except Exception as e:
            logger.error(f"Error in position monitoring: {e}")
    
    def close_position(self, symbol: str, exit_price: float, reason: str = 'manual'):
        """Close a position"""
        try:
            position = self.positions.get(symbol)
            if not position:
                logger.warning(f"Position {symbol} not found")
                return
            
            # Execute closing order
            close_side = 'sell' if position['side'] == 'buy' else 'buy'
            order = self.exchange.create_market_order(symbol, close_side, position['size'])
            
            if order:
                # Update trade in database
                trade_id = position['trade_id']
                self.database.close_trade(trade_id, exit_price, reason)
                
                # Calculate P&L
                pnl_info = self.risk_manager.calculate_position_pnl(position, exit_price)
                
                # Update capital
                self.capital += pnl_info['pnl']
                self.portfolio_value = self.capital
                
                logger.info(f"✓ Closed {position['side']} position: {symbol} @ ${exit_price:.4f} "
                           f"(P&L: ${pnl_info['pnl']:.2f} / {pnl_info['pnl_percentage']:.2%}) - {reason}")
        
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
    
    def report_performance(self):
        """Report trading performance"""
        try:
            # Calculate performance metrics
            metrics = self.database.calculate_performance()
            
            # Add current portfolio value
            metrics['portfolio_value'] = self.portfolio_value
            
            # Save to database
            self.database.save_performance(metrics)
            
            # Log summary
            logger.info("=== Performance Report ===")
            logger.info(f"Portfolio Value: ${self.portfolio_value:.2f}")
            logger.info(f"Total Trades: {metrics['total_trades']}")
            logger.info(f"Win Rate: {metrics['win_rate']:.2%}")
            logger.info(f"Total P&L: ${metrics['total_pnl']:.2f}")
            logger.info(f"Avg Win: ${metrics['avg_win']:.2f}")
            logger.info(f"Avg Loss: ${metrics['avg_loss']:.2f}")
            logger.info(f"Profit Factor: {metrics['profit_factor']:.2f}")
            logger.info(f"Open Positions: {len(self.positions)}")
            logger.info("========================")
        
        except Exception as e:
            logger.error(f"Error reporting performance: {e}")
    
    async def run(self):
        """Main trading loop"""
        try:
            logger.info("Starting trading bot...")
            self.running = True
            
            # Initialize
            await self.initialize()
            
            # Get check interval
            check_interval = self.config.get('general.check_interval', 60)
            report_interval = self.config.get('monitoring.performance_report_interval', 3600)
            
            last_report_time = time.time()
            iteration = 0
            
            while self.running:
                try:
                    iteration += 1
                    logger.info(f"=== Trading Cycle {iteration} ===")
                    
                    # Monitor existing positions
                    self.monitor_positions()
                    
                    # Check if we can open new positions
                    max_positions = self.config.get('general.max_concurrent_positions', 5)
                    
                    if len(self.positions) < max_positions:
                        # Select trading pairs
                        logger.info("Selecting trading pairs...")
                        pairs = await self.select_trading_pairs()
                        
                        # Analyze pairs and look for signals
                        for symbol in pairs:
                            if symbol in self.positions:
                                continue  # Already have position
                            
                            signal = self.analyze_pair(symbol)
                            
                            if signal and signal['action'] in ['buy', 'sell']:
                                logger.info(f"Signal: {signal['action']} {symbol} - {signal['reason']}")
                                self.execute_signal(signal)
                            
                            # Limit new positions per cycle
                            if len(self.positions) >= max_positions:
                                break
                    
                    # Report performance periodically
                    if time.time() - last_report_time >= report_interval:
                        self.report_performance()
                        last_report_time = time.time()
                    
                    # Wait before next cycle
                    logger.info(f"Waiting {check_interval} seconds...")
                    await asyncio.sleep(check_interval)
                
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in trading bot: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown bot gracefully"""
        logger.info("Shutting down trading bot...")
        self.running = False
        
        # Close all positions
        for symbol in list(self.positions.keys()):
            ticker = self.exchange.fetch_ticker(symbol)
            self.close_position(symbol, ticker['last'], 'shutdown')
        
        # Final performance report
        self.report_performance()
        
        # Close connections
        self.database.close()
        self.exchange.close()
        
        logger.info("Trading bot shutdown complete")


async def main():
    """Main entry point"""
    bot = TradingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())

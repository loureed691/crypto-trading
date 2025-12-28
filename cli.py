"""
Command Line Interface for Trading Bot
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import TradingBot
from src.config import Config
from src.database import Database
from loguru import logger


def show_performance(args):
    """Show performance statistics"""
    try:
        config = Config()
        db = Database(config.database_url)
        
        print("\n=== Trading Bot Performance ===\n")
        
        # Get latest performance
        latest = db.get_latest_performance()
        if latest:
            print(f"Timestamp: {latest.timestamp}")
            print(f"Portfolio Value: ${latest.portfolio_value:.2f}")
            print(f"\nTrade Statistics:")
            print(f"  Total Trades: {latest.total_trades}")
            print(f"  Winning Trades: {latest.winning_trades}")
            print(f"  Losing Trades: {latest.losing_trades}")
            print(f"  Win Rate: {latest.win_rate:.2%}")
            print(f"\nP&L Metrics:")
            print(f"  Total P&L: ${latest.total_pnl:.2f}")
            print(f"  Avg Win: ${latest.avg_win:.2f}")
            print(f"  Avg Loss: ${latest.avg_loss:.2f}")
            print(f"  Profit Factor: {latest.profit_factor:.2f}")
            
            if latest.sharpe_ratio:
                print(f"\nRisk Metrics:")
                print(f"  Sharpe Ratio: {latest.sharpe_ratio:.2f}")
                print(f"  Max Drawdown: {latest.max_drawdown:.2%}")
        else:
            print("No performance data available yet.")
        
        # Show recent trades
        print("\n=== Recent Trades ===\n")
        recent_trades = db.get_closed_trades(limit=10)
        
        if recent_trades:
            for trade in recent_trades:
                status_symbol = "✓" if trade.pnl and trade.pnl > 0 else "✗"
                print(f"{status_symbol} {trade.symbol} {trade.side.upper()} "
                      f"@ ${trade.entry_price:.4f} -> ${trade.exit_price:.4f} "
                      f"| P&L: ${trade.pnl:.2f} ({trade.pnl_percentage:.2%}) "
                      f"| {trade.exit_reason}")
        else:
            print("No closed trades yet.")
        
        # Show open positions
        print("\n=== Open Positions ===\n")
        open_trades = db.get_open_trades()
        
        if open_trades:
            for trade in open_trades:
                print(f"• {trade.symbol} {trade.side.upper()} "
                      f"@ ${trade.entry_price:.4f} "
                      f"| Size: {trade.size:.4f} "
                      f"| Leverage: {trade.leverage}x "
                      f"| SL: ${trade.stop_loss:.4f} TP: ${trade.take_profit:.4f}")
        else:
            print("No open positions.")
        
        print("\n" + "="*50 + "\n")
        
        db.close()
    except Exception as e:
        logger.error(f"Error showing performance: {e}")
        sys.exit(1)


def validate_config(args):
    """Validate configuration"""
    try:
        print("\n=== Validating Configuration ===\n")
        
        config = Config(args.config)
        
        print("✓ Configuration file loaded successfully")
        print(f"  Trading Mode: {config.trading_mode}")
        print(f"  Initial Capital: ${config.initial_capital:.2f}")
        print(f"  Max Leverage: {config.max_leverage}x")
        print(f"  Risk per Trade: {config.risk_per_trade:.2%}")
        
        # Validate
        config.validate()
        print("\n✓ All configuration checks passed!")
        
        # Show enabled strategies
        strategies = config.get_enabled_strategies()
        print(f"\nEnabled Strategies: {', '.join(strategies)}")
        
        print("\n" + "="*50 + "\n")
    except Exception as e:
        print(f"\n✗ Configuration validation failed: {e}\n")
        sys.exit(1)


async def run_bot(args):
    """Run the trading bot"""
    try:
        print("\n=== Starting Trading Bot ===\n")
        
        bot = TradingBot(args.config)
        await bot.run()
    except KeyboardInterrupt:
        print("\n\nBot stopped by user.")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Automated Crypto Trading Bot for KuCoin",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the trading bot')
    run_parser.add_argument('--config', type=str, help='Path to config file')
    
    # Performance command
    subparsers.add_parser('performance', help='Show performance statistics')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--config', type=str, help='Path to config file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Execute command
    if args.command == 'run':
        asyncio.run(run_bot(args))
    elif args.command == 'performance':
        show_performance(args)
    elif args.command == 'validate':
        validate_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
Configuration Manager for the Trading Bot
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

class Config:
    """Manages configuration loading and access"""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration"""
        # Load environment variables
        load_dotenv()
        
        # Load YAML config
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # API credentials from environment
        self.api_key = os.getenv('KUCOIN_API_KEY')
        self.api_secret = os.getenv('KUCOIN_API_SECRET')
        self.api_passphrase = os.getenv('KUCOIN_API_PASSPHRASE')
        
        # Trading settings
        self.trading_mode = os.getenv('TRADING_MODE', self.config['general']['trading_mode'])
        self.initial_capital = float(os.getenv('INITIAL_CAPITAL', 1000))
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', 0.1))
        self.max_leverage = int(os.getenv('MAX_LEVERAGE', self.config['risk_management']['max_leverage']))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', self.config['risk_management']['max_position_risk']))
        
        # Database
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
        
        # Notifications
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enable_notifications = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy"""
        return self.config['strategies'].get(strategy_name, {})
    
    def get_enabled_strategies(self) -> list:
        """Get list of enabled strategies"""
        return self.config['strategies'].get('enabled', [])
    
    def is_testnet(self) -> bool:
        """Check if running in testnet mode"""
        return self.trading_mode == 'testnet'
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not all([self.api_key, self.api_secret, self.api_passphrase]):
            raise ValueError("API credentials not set in environment variables")
        
        if self.risk_per_trade > 0.1:
            raise ValueError("Risk per trade cannot exceed 10%")
        
        if self.max_leverage > 10:
            raise ValueError("Maximum leverage cannot exceed 10x")
        
        return True

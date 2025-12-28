# Automated Crypto Trading Bot for KuCoin

A fully automated, production-grade cryptocurrency trading bot for KuCoin exchange with sophisticated features including automated pair selection, multiple trading strategies, dynamic leverage selection, and comprehensive risk management.

## 🚀 Features

### Core Capabilities
- **Automated Pair Selection**: Intelligently selects trading pairs based on:
  - 24h trading volume and liquidity analysis
  - Volatility metrics and trend strength
  - Order book depth and spread analysis
  - Multi-factor scoring system

- **Multiple Trading Strategies**:
  - **Trend Following**: EMA crossover with ADX confirmation
  - **Mean Reversion**: Bollinger Bands with RSI indicators
  - **Breakout**: Volume surge detection with support/resistance
  - **Momentum**: MACD-based signals with trend confirmation
  - **Automatic Strategy Selection**: Adapts to market conditions

- **Advanced Risk Management**:
  - Position sizing using Kelly Criterion or volatility-based methods
  - Dynamic stop-loss and take-profit levels
  - Trailing stops for profit protection
  - Portfolio-level risk controls
  - Maximum drawdown protection

- **Intelligent Leverage Selection**:
  - Volatility-based automatic leverage adjustment
  - Conservative leverage mapping (1x-3x based on market conditions)
  - Risk-aware position scaling

- **Production-Grade Features**:
  - Comprehensive logging and monitoring
  - SQLite database for trade history
  - Performance analytics and reporting
  - Retry mechanisms with exponential backoff
  - Health monitoring and error handling

## 📋 Prerequisites

- Python 3.9 or higher
- KuCoin account with API credentials
- Minimum capital: $100 (recommended: $1000+)

## 🛠️ Installation

### Option 1: Local Installation

1. **Clone the repository**:
```bash
git clone https://github.com/loureed691/crypto-trading.git
cd crypto-trading
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your KuCoin API credentials
```

### Option 2: Docker Installation

1. **Clone and configure**:
```bash
git clone https://github.com/loureed691/crypto-trading.git
cd crypto-trading
cp .env.example .env
# Edit .env with your credentials
```

2. **Build and run**:
```bash
docker-compose up -d
```

3. **View logs**:
```bash
docker-compose logs -f
```

## ⚙️ Configuration

### 1. API Credentials (.env file)

```env
# KuCoin API Credentials
KUCOIN_API_KEY=your_api_key_here
KUCOIN_API_SECRET=your_api_secret_here
KUCOIN_API_PASSPHRASE=your_api_passphrase_here

# Trading Configuration
TRADING_MODE=testnet  # or 'live' for production
INITIAL_CAPITAL=1000
MAX_POSITION_SIZE=0.1  # 10% of capital per trade
MAX_LEVERAGE=3
RISK_PER_TRADE=0.02  # 2% risk per trade
```

### 2. Trading Strategy (config.yaml)

The `config.yaml` file contains detailed configuration for:
- Risk management parameters
- Pair selection criteria
- Strategy configurations
- Position sizing methods
- Leverage selection rules
- Performance monitoring settings

Key parameters to adjust:
```yaml
risk_management:
  max_portfolio_risk: 0.2  # 20% total portfolio risk
  max_position_risk: 0.02  # 2% per trade
  max_leverage: 3
  min_risk_reward_ratio: 2.0

pair_selection:
  min_24h_volume_usdt: 1000000  # $1M minimum
  volatility_range:
    min: 0.02  # 2% daily volatility
    max: 0.15  # 15% daily volatility
```

## 🚦 Usage

### Start the Bot

**Local:**
```bash
python -m src.bot
```

**Docker:**
```bash
docker-compose up -d
```

### Monitor Performance

**View logs:**
```bash
tail -f logs/trading_bot_*.log
```

**Check database:**
```bash
sqlite3 trading_bot.db
SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;
SELECT * FROM performance ORDER BY timestamp DESC LIMIT 5;
```

### Stop the Bot

**Local:**
Press `Ctrl+C` (the bot will close all positions gracefully)

**Docker:**
```bash
docker-compose down
```

## 📊 Performance Metrics

The bot tracks and reports:
- Total trades and win rate
- Total P&L and percentage returns
- Average win/loss ratios
- Profit factor
- Sharpe ratio (when available)
- Maximum drawdown
- Current portfolio value

Performance reports are:
- Logged every hour (configurable)
- Saved to database for historical analysis
- Displayed in console with formatted output

## 🏗️ Architecture

```
crypto-trading/
├── src/
│   ├── bot.py              # Main trading bot orchestration
│   ├── config.py           # Configuration management
│   ├── exchange.py         # KuCoin API wrapper
│   ├── pair_selector.py    # Automated pair selection
│   ├── strategies.py       # Trading strategies
│   ├── indicators.py       # Technical indicators
│   ├── risk_manager.py     # Risk and position management
│   └── database.py         # Trade history database
├── config.yaml             # Strategy configuration
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker container config
└── docker-compose.yml     # Docker compose config
```

## 🔒 Security Best Practices

1. **API Permissions**: Create API keys with only trading permissions (no withdrawal)
2. **IP Whitelist**: Enable IP whitelisting on KuCoin
3. **Environment Variables**: Never commit `.env` file to version control
4. **Testnet First**: Always test with testnet before using real funds
5. **Start Small**: Begin with minimum capital to validate strategy
6. **Monitor Regularly**: Check bot performance and logs frequently

## 📈 Trading Strategies Explained

### Trend Following
- Uses EMA (12/26) crossovers for entry signals
- Confirms trend strength with ADX indicator
- Best for: Strong trending markets
- Risk/Reward: 1:2 ratio

### Mean Reversion
- Identifies overbought/oversold conditions with Bollinger Bands
- Confirms with RSI indicator
- Best for: Range-bound markets
- Risk/Reward: 1:1.5 ratio

### Breakout
- Detects price breakouts from consolidation
- Requires volume surge confirmation
- Best for: Volatile, low-volume periods
- Risk/Reward: 1:2 ratio

### Momentum
- MACD crossovers with histogram confirmation
- Rides strong momentum moves
- Best for: Trending markets with momentum
- Risk/Reward: 1:2.5 ratio

## ⚠️ Risk Disclaimer

**IMPORTANT**: Trading cryptocurrencies involves substantial risk of loss. This bot is provided for educational purposes only. 

- Never invest more than you can afford to lose
- Past performance does not guarantee future results
- The bot's profitability depends on market conditions
- Always start with testnet/paper trading
- Monitor the bot regularly and adjust parameters as needed
- The authors assume no liability for financial losses

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

**1. API Connection Errors**
- Verify API credentials in `.env`
- Check KuCoin API status
- Ensure IP is whitelisted (if enabled)

**2. Insufficient Balance**
- Minimum $10 per trade required
- Check `INITIAL_CAPITAL` setting
- Verify exchange balance

**3. No Trading Signals**
- Market conditions may not meet strategy criteria
- Adjust pair selection parameters in `config.yaml`
- Check volatility and volume thresholds

**4. Position Not Closing**
- Verify stop-loss/take-profit levels are reasonable
- Check for exchange rate limits
- Review logs for error messages

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs in `logs/` directory

## 🎯 Roadmap

Future enhancements:
- [ ] Machine learning strategy optimization
- [ ] Telegram notifications
- [ ] Web dashboard for monitoring
- [ ] Backtesting framework
- [ ] Multi-exchange support
- [ ] Advanced portfolio optimization
- [ ] Paper trading mode

---

**Remember**: Always test thoroughly before risking real capital. Happy trading! 🚀
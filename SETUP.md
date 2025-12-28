# Setup Guide

## Quick Start

### 1. Get KuCoin API Credentials

1. Log in to [KuCoin](https://www.kucoin.com/)
2. Go to API Management
3. Create a new API key with:
   - Trading permissions enabled
   - Withdrawal disabled (for security)
   - Optional: Enable IP whitelist

### 2. Environment Setup

```bash
# Clone repository
git clone https://github.com/loureed691/crypto-trading.git
cd crypto-trading

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your credentials
```

### 3. Test Configuration

```bash
# Validate configuration
python cli.py validate

# Expected output:
# ✓ Configuration file loaded successfully
# ✓ All configuration checks passed!
```

### 4. Start with Testnet

**Important**: Always start with testnet mode!

```bash
# In .env file, set:
TRADING_MODE=testnet
INITIAL_CAPITAL=1000

# Run the bot
python cli.py run
```

### 5. Monitor Performance

```bash
# In another terminal, check performance
python cli.py performance

# Or view logs
tail -f logs/trading_bot_*.log
```

## Configuration Tips

### Conservative Settings (Recommended for Beginners)

```yaml
# config.yaml
risk_management:
  max_portfolio_risk: 0.1   # 10% total risk
  max_position_risk: 0.01   # 1% per trade
  max_leverage: 1           # No leverage
  min_risk_reward_ratio: 3.0

position_sizing:
  method: fixed
  min_position_size_usdt: 10
  max_position_size_usdt: 100
```

### Aggressive Settings (For Experienced Traders)

```yaml
# config.yaml
risk_management:
  max_portfolio_risk: 0.2   # 20% total risk
  max_position_risk: 0.02   # 2% per trade
  max_leverage: 3           # 3x leverage
  min_risk_reward_ratio: 2.0

position_sizing:
  method: kelly_criterion
  kelly_fraction: 0.25
  max_position_size_usdt: 1000
```

## Strategy Selection

Choose strategies based on your market view:

### Enable Trend Following (Bull Markets)
```yaml
strategies:
  enabled:
    - trend_following
    - momentum
```

### Enable Mean Reversion (Range Markets)
```yaml
strategies:
  enabled:
    - mean_reversion
```

### Enable All (Adaptive)
```yaml
strategies:
  enabled:
    - trend_following
    - mean_reversion
    - breakout
    - momentum
```

## Common Configurations

### Day Trading Setup
```yaml
general:
  check_interval: 60  # Check every minute
  max_concurrent_positions: 3

pair_selection:
  min_24h_volume_usdt: 5000000  # $5M minimum
  volatility_range:
    min: 0.03
    max: 0.10
```

### Swing Trading Setup
```yaml
general:
  check_interval: 300  # Check every 5 minutes
  max_concurrent_positions: 5

pair_selection:
  min_24h_volume_usdt: 1000000  # $1M minimum
  volatility_range:
    min: 0.02
    max: 0.15
```

## Docker Deployment

```bash
# Build image
docker-compose build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Maintenance

### Daily Tasks
- Check bot logs for errors
- Review performance metrics
- Monitor open positions

### Weekly Tasks
- Analyze win rate and P&L
- Adjust configuration if needed
- Update strategy parameters

### Monthly Tasks
- Review overall performance
- Optimize strategy selection
- Update dependencies

## Troubleshooting

### Bot Not Trading
1. Check market conditions match strategy criteria
2. Verify sufficient balance
3. Review pair selection settings
4. Check risk limits aren't too restrictive

### High Loss Rate
1. Reduce leverage
2. Increase min_risk_reward_ratio
3. Tighten pair selection criteria
4. Review strategy selection

### API Errors
1. Verify API credentials
2. Check rate limits
3. Ensure trading permissions
4. Verify IP whitelist

## Support

- Check logs in `logs/` directory
- Review database: `sqlite3 trading_bot.db`
- Open GitHub issue for bugs
- Join community discussions

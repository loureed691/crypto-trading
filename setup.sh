#!/bin/bash

# Setup script for Crypto Trading Bot

set -e

echo "==================================="
echo "Crypto Trading Bot Setup"
echo "==================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if Python 3.9+
required_version="3.9"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9 or higher is required"
    exit 1
fi

echo "✓ Python version OK"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your KuCoin API credentials"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs
echo "✓ Logs directory created"
echo ""

# Validate configuration
echo "Validating configuration..."
python cli.py validate || {
    echo ""
    echo "⚠️  Configuration validation failed"
    echo "Please edit .env file with your API credentials and try again"
    echo ""
    exit 1
}
echo ""

# Run tests
echo "Running tests..."
pytest tests/ -v || {
    echo ""
    echo "⚠️  Some tests failed, but setup is complete"
    echo ""
}

echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your KuCoin API credentials"
echo "2. Review config.yaml for strategy settings"
echo "3. Start with testnet mode: TRADING_MODE=testnet"
echo "4. Run the bot: python cli.py run"
echo "5. Monitor performance: python cli.py performance"
echo ""
echo "For more information, see SETUP.md"
echo ""

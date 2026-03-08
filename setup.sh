#!/bin/bash
# TechPulse — setup script
set -e

echo "=== TechPulse Setup ==="
echo ""

# Check Python version
PYTHON=$(which python3.11 2>/dev/null || which python3.10 2>/dev/null || which python3.9 2>/dev/null || which python3)
PYVER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PYVER at $PYTHON"

# Create venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
fi

# Activate
source .venv/bin/activate

# Upgrade pip
pip install -q --upgrade pip

echo "Installing dependencies..."
pip install -q -r requirements.txt

# Playwright for TikTok
echo "Installing Playwright (needed for TikTok scraping)..."
playwright install chromium --with-deps 2>/dev/null || echo "  [!] Playwright install failed — TikTok scraping disabled"

# Create .env if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "=== Configure your API keys ==="
    echo "Edit .env with your keys:"
    echo "  - REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET (https://www.reddit.com/prefs/apps)"
    echo "  - YOUTUBE_API_KEY (https://console.developers.google.com)"
    echo "  - ANTHROPIC_API_KEY (https://console.anthropic.com)"
    echo ""
    echo "Note: XDA and GSMArena don't need API keys."
    echo "      PCComponents search works without any key."
fi

echo ""
echo "=== Setup complete! ==="
echo "To run TechPulse:"
echo "  source .venv/bin/activate"
echo "  python main.py"

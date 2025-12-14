#!/bin/bash
set -e

echo "🚀 Setting up Twitter AI Agent..."

# Detect Python
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    echo "❌ Python 3 not found. Please install Python 3.10+."
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# Create virtual environment
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Install dependencies
if [ ! -f requirements.txt ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

echo "📦 Installing dependencies..."
pip install --upgrade pip
if ! pip install -r requirements.txt; then
    echo "❌ Failed to install dependencies."
    exit 1
fi

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Create directories
mkdir -p data/{prompts,selectors,generated_images,screenshots}
mkdir -p logs

# Copy env file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  Created .env from example. Please edit it with your credentials."
    else
        echo "⚠️  .env.example not found, skipping .env creation."
    fi
fi

# Initialize database (if using alembic)
# alembic upgrade head

echo "✅ Setup complete!"
echo "Run: uvicorn app.main:app --reload"

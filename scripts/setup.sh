#!/bin/bash
set -e

echo "🚀 Setting up Twitter AI Agent..."

# Detect Python
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+."
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi

source venv/bin/activate

# Install dependencies
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

# Copy env file if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  Created .env from template - please edit with your credentials"
    else
        echo "⚠️  .env.example not found, skipping .env creation"
    fi
fi

# Initialize database (creates tables)
echo "Initializing database..."
python -c "from app.storage import init_db; init_db()"

# Seed default selectors
if [ -f scripts/seed_selectors.py ]; then
    echo "Seeding default selectors..."
    python scripts/seed_selectors.py
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Start PostgreSQL and Redis (or use docker-compose)"
echo "  3. Run: uvicorn app.main:app --reload"
echo ""

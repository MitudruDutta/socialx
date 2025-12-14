v# Twitter AI Agent Bot

Autonomous Twitter bot with AI-powered content generation, mention monitoring, and campaign management.

## ⚠️ Legal Disclaimer

**This project uses unofficial methods to interact with Twitter and includes evasion techniques.**

Users are responsible for:
- Compliance with Twitter's Terms of Service (https://twitter.com/tos)
- Ensuring use cases are legally authorized
- Risk of account suspension or legal action from Twitter

**Use only for authorized testing or research.**

## Features

- 🎧 Monitor Twitter mentions without official API
- 💬 Generate context-aware responses using LLMs
- 🎨 Create images with Nano Banana (lightweight SD)
- 📊 Campaign management and scheduling
- 🔒 Stealth mode with anti-detection
- 🏥 Self-monitoring and auto-healing

## Quick Start

```bash
# Setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# Configure
# 1. Copy the example file
cp .env.example .env
# 2. Edit .env with your credentials (see .env.example for details)
# 3. Ensure you do NOT commit .env to version control!

# Run
uvicorn app.main:app --reload
```

## Docker

```bash
cd docker
docker-compose up -d
```

## API Endpoints

- `GET /health` - System health check
- `POST /api/v1/tweets/generate` - Generate tweet text
- `POST /api/v1/tweets/create` - Create content with optional image
- `GET /api/v1/tweets/mentions` - Fetch recent mentions
- `POST /api/v1/tweets/run-workflow` - Run full agent workflow

## Architecture

```
app/
├── agents/          # AI agent orchestration
├── automation/      # Playwright browser automation
├── generators/      # Text & image generation
├── monitoring/      # Health checks & alerts
├── tasks/           # Celery scheduled tasks
└── api/             # FastAPI endpoints
```

## Configuration

**Security Warning:** Never commit your `.env` file or credentials to version control. In production, use a secrets manager (e.g., AWS Secrets Manager, Vault) instead of plaintext files.

Key environment variables:

- `TWITTER_USERNAME/PASSWORD` - Twitter credentials (consider using OAuth tokens if possible)
- `OPENAI_API_KEY` - Primary LLM
- `GOOGLE_API_KEY` - Fallback LLM (free tier)
- `PROXY_*` - Residential proxy settings (Highly Recommended)
- `REQUIRE_HUMAN_REVIEW` - **Enabled by default.** Disabling this voids support and risks unchecked posting.

## Safety

- **Human Review:** Required by default. ⚠️ Disabling this requires explicit risk acceptance.
- **Rate Limits:** Built-in hard limits (e.g., max 50 posts/day) to prevent abuse.
- **Session Persistence:** Reuses cookies to avoid frequent logins.
- **Error Recovery:** Automatic backoff on failures.
- **Alerts:** Integration with Telegram for critical notifications.

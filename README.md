<p align="center">
  <h1 align="center">🤖 SocialX</h1>
  <p align="center">
    Autonomous Twitter bot with AI-powered content generation, intelligent mention monitoring, and campaign management.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-Powered-121212?logo=chainlink&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/Playwright-Automation-2EAD33?logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

---

## ⚠️ Legal Disclaimer

> **This project uses unofficial methods to interact with Twitter and includes evasion techniques.**

By using this software, you acknowledge:
- Full responsibility for compliance with [Twitter's Terms of Service](https://twitter.com/tos)
- Risk of account suspension or legal action from Twitter/X
- This tool is intended for **authorized testing, research, or personal automation only**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎧 **Mention Monitoring** | Real-time monitoring of Twitter mentions without official API |
| 💬 **AI Responses** | Context-aware reply generation using OpenAI, Google Gemini, or Ollama |
| 🎨 **Image Generation** | Create images with Nano Banana (lightweight Stable Diffusion) |
| 📊 **Campaign Management** | Schedule and manage content campaigns |
| 🔒 **Stealth Mode** | Anti-detection with browser fingerprint evasion |
| 🏥 **Self-Healing** | Auto-recovery, health monitoring, and Telegram alerts |
| 👁️ **Human Review** | Optional approval workflow before posting (enabled by default) |

---

## 🏗️ Architecture

```
socialx/
├── app/
│   ├── agents/           # AI agent orchestration (LangChain/LangGraph)
│   ├── api/              # FastAPI REST endpoints
│   ├── automation/       # Playwright browser automation + stealth
│   ├── generators/       # Text (LLM) & Image (Diffusers) generation
│   ├── monitoring/       # Health checks & Telegram alerts
│   ├── storage/          # PostgreSQL models & migrations
│   ├── tasks/            # Celery scheduled tasks
│   └── utils/            # Shared utilities
├── docker/               # Docker & docker-compose configs
├── data/
│   ├── prompts/          # Custom prompt templates
│   ├── selectors/        # Twitter DOM selectors
│   └── training/         # Fine-tuning data
└── tests/                # Unit, integration & e2e tests
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- (Optional) CUDA-compatible GPU for local image generation

### Installation

```bash
# Clone the repository
git clone https://github.com/MitudruDutta/socialx.git
cd socialx

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Run Locally

```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminals:
# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Run with Docker

```bash
cd docker
docker-compose up -d
```

This starts:
- **PostgreSQL** - Database
- **Redis** - Cache & message broker
- **App** - FastAPI server (port 8000)
- **Celery Worker** - Background task processing
- **Celery Beat** - Scheduled task runner
- **Playwright** - Browser automation container

---

## 🔌 API Reference

### Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service status |
| `GET` | `/health` | Comprehensive health check (DB, Redis, disk, memory) |
| `POST` | `/api/v1/tweets/generate` | Generate tweet text from topic |
| `POST` | `/api/v1/tweets/create` | Create content with optional image |
| `GET` | `/api/v1/tweets/mentions` | Fetch recent mentions |
| `POST` | `/api/v1/tweets/run-workflow` | Execute full agent workflow |

### Example: Generate a Tweet

```bash
curl -X POST http://localhost:8000/api/v1/tweets/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI automation trends", "tone": "professional"}'
```

### Example: Run Full Workflow

```bash
curl -X POST http://localhost:8000/api/v1/tweets/run-workflow
```

---

## ⚙️ Configuration

### Environment Variables


Create a `.env` file from `.env.example` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | App secret key (min 32 chars) |
| `ENCRYPTION_KEY` | ✅ | Encryption key for sensitive data |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `TWITTER_USERNAME` | ✅ | Twitter account username |
| `TWITTER_PASSWORD` | ✅ | Twitter account password |
| `TWITTER_EMAIL` | ✅ | Twitter account email |
| `OPENAI_API_KEY` | ⚡ | Primary LLM (recommended) |
| `GOOGLE_API_KEY` | ⚡ | Fallback LLM (free tier available) |
| `PROXY_HOST` | 🔒 | Residential proxy host (highly recommended) |
| `TELEGRAM_BOT_TOKEN` | 📢 | For alert notifications |

### LLM Priority

The system uses a fallback chain for text generation:
1. **OpenAI** (GPT-3.5/4) - Primary, best quality
2. **Google Gemini** - Fallback, free tier available
3. **Ollama** (Local) - Final fallback, fully offline

### Rate Limits

Built-in safety limits (configurable in `.env`):

```env
MAX_TWEETS_PER_HOUR=5
MAX_REPLIES_PER_HOUR=10
MIN_ACTION_DELAY=30    # seconds
MAX_ACTION_DELAY=120   # seconds
```

---

## 🔐 Safety & Security

### Human Review Mode

**Enabled by default.** When `REQUIRE_HUMAN_REVIEW=true`:
- Generated content is saved as drafts
- No automatic posting occurs
- Review via database or future dashboard

To enable auto-posting (at your own risk):
```env
REQUIRE_HUMAN_REVIEW=false
```

### Anti-Detection

The bot includes stealth measures:
- Browser fingerprint randomization
- Human-like delays between actions
- Session persistence (cookie reuse)
- Residential proxy support

### Monitoring & Alerts

- **Health Checks**: Database, Redis, disk, memory
- **Telegram Alerts**: Critical errors, workflow failures
- **Sentry Integration**: Error tracking and performance monitoring

---

## 📅 Scheduled Tasks

Celery Beat runs these tasks automatically:

| Task | Schedule | Description |
|------|----------|-------------|
| `check_mentions` | Every 15 min | Fetch and process new mentions |
| `health_check` | Every 5 min | System health verification |
| `cleanup_media` | Daily | Remove old generated images |
| `generate_and_post_content` | Configurable | Auto-generate and post content |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

---

## 🛠️ Development

### Project Structure

```
app/
├── agents/orchestrator.py    # Main workflow: listen → respond → execute
├── automation/
│   ├── playwright_bot.py     # Browser automation
│   ├── selectors.py          # Twitter DOM selectors
│   └── stealth.py            # Anti-detection scripts
├── generators/
│   ├── text_generator.py     # LLM-powered text generation
│   └── image_generator.py    # Nano Banana image generation
├── monitoring/
│   ├── health_checker.py     # System health checks
│   └── alert_manager.py      # Telegram notifications
└── tasks/
    ├── celery_app.py         # Celery configuration
    └── scheduled_tasks.py    # Periodic tasks
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Cache & message broker |
| `celery_worker` | - | Background task processor |
| `celery_beat` | - | Task scheduler |
| `playwright` | - | Browser automation (2GB shared memory) |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is for educational and research purposes. Use responsibly and in compliance with all applicable laws and platform terms of service.

---

<p align="center">
  SocialX — Built with ❤️ using FastAPI, LangChain, Playwright, and Diffusers
</p>

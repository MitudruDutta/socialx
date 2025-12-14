# Twitter AI Agent

## Project Overview
This project is an autonomous Twitter bot designed to monitor mentions, generate context-aware responses using LLMs, and manage content campaigns. It operates without the official Twitter API, utilizing Playwright for browser automation to interact with the platform directly.

## Architecture
The system is built as a distributed Python application:

*   **API Layer:** FastAPI (`app/main.py`) provides endpoints for controlling the agent and monitoring health.
*   **Agent Logic:** `app/agents/orchestrator.py` manages the workflow (Listen -> Respond -> Execute).
*   **Automation:** Playwright (`app/automation/`) handles browser interactions (login, posting, scraping).
*   **AI/ML:**
    *   **Text:** LangChain integration with OpenAI/Google Gemini (`app/generators/text_generator.py`).
    *   **Image:** Local Stable Diffusion/Nano Banana via Diffusers (`app/generators/image_generator.py`).
*   **Background Tasks:** Celery with Redis for scheduling and asynchronous job processing.
*   **Persistence:** PostgreSQL with SQLAlchemy and Alembic for migrations.

## Key Directories
*   `app/agents`: Core AI orchestration logic.
*   `app/automation`: Browser automation scripts (Playwright).
*   `app/generators`: wrappers for Text and Image generation models.
*   `app/monitoring`: Health checks and alerting.
*   `docker/`: Docker configuration files.
*   `tests/`: Pytest suite (Unit, Integration, E2E).

## Getting Started

### Prerequisites
*   Python 3.10+
*   PostgreSQL & Redis (or use Docker)
*   Chrome/Chromium (for Playwright)

### Local Development
1.  **Setup Environment:**
    ```bash
    cd twitter-ai-agent
    chmod +x scripts/setup.sh
    ./scripts/setup.sh
    ```
2.  **Configuration:**
    Copy `.env.example` to `.env` and fill in credentials (Twitter, OpenAI, DB URL).
    ```bash
    cp .env.example .env
    ```
3.  **Run Application:**
    ```bash
    uvicorn app.main:app --reload
    ```

### Docker
To run the full stack (App, Worker, Postgres, Redis):
```bash
cd twitter-ai-agent/docker
docker-compose up -d
```

## Development Conventions

*   **Configuration:** All settings are managed via Pydantic in `app/config.py`. Use environment variables to override defaults.
*   **Async/Await:** The codebase is primarily asynchronous (FastAPI, Playwright). Ensure new I/O bound code uses `async`.
*   **Logging:** Use `loguru` for all logging (`from loguru import logger`).
*   **Testing:** Run tests with `pytest`.
    ```bash
    pytest
    ```
*   **Database:** Use SQLAlchemy for ORM interactions. Migrations are handled by Alembic.

## Common Commands
*   **Start API:** `uvicorn app.main:app --reload`
*   **Run Tests:** `pytest`
*   **Lint/Format:** (Check `setup.sh` or CI workflows for specifics, usually `black` / `ruff`)
*   **Database Migration:** `alembic upgrade head`

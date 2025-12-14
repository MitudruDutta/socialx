import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("TWITTER_USERNAME", "test_user")
    monkeypatch.setenv("TWITTER_PASSWORD", "test_pass")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("REQUIRE_HUMAN_REVIEW", "true")

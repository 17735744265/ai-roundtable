"""Pytest fixtures for AI Roundtable tests."""

import os
import sys
import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_roundtable.db"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["DEBUG"] = "false"


@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Async HTTP client for testing FastAPI endpoints."""
    from app.main import app
    from app.database import engine
    from app.models.session import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def sample_topic():
    return "Remote work: should it be the default?"


@pytest.fixture
def sample_guest_ids():
    return ["eff_expert", "tech_arch", "crit_thinker"]

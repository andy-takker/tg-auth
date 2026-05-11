"""Shared pytest fixtures.

Strategy:
- Spin up a real Litestar app via ``create_app`` against a tmp-file SQLite DB
  (via aiosqlite). Each test function gets a fresh DB.
- Inject a fake ``PyJWKClient`` so we can sign our own RS256 tokens with a
  generated keypair and get the real ``verify_telegram_id_token`` path to
  validate them.
- Use ``litestar.testing.AsyncTestClient`` for HTTP integration.
- For unit tests on the repository, expose a bare ``AsyncSession`` fixture
  bound to the same in-test SQLite database.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient
from litestar import Litestar
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tg_auth.adapters.database import (
    tables,  # noqa: F401  — register tables on metadata
)
from tg_auth.adapters.database.base import BaseTable
from tg_auth.application.config import AppConfig
from tg_auth.presentors.rest.app_factory import create_app

TEST_CLIENT_ID = "8506301481"
TEST_ISSUER = "https://oauth.telegram.org"


# ---------------------------------------------------------------------------
# JWT signing infra
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rsa_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def fake_jwks_client(rsa_private_key: rsa.RSAPrivateKey) -> PyJWKClient:
    """A drop-in replacement for ``jwt.PyJWKClient`` that returns the test
    public key for any incoming token."""
    fake = MagicMock(spec=PyJWKClient)
    signing_key = SimpleNamespace(key=rsa_private_key.public_key())
    fake.get_signing_key_from_jwt.return_value = signing_key
    return fake


@pytest.fixture
def make_id_token(
    rsa_private_key: rsa.RSAPrivateKey,
) -> Callable[..., str]:
    """Factory that produces an RS256-signed JWT mimicking Telegram's id_token.

    Pass kwargs to override individual claims (e.g. ``aud="other"`` or
    ``exp=0`` to test failure modes)."""

    def _make(**overrides: object) -> str:
        now = int(time.time())
        claims: dict[str, object] = {
            "iss": TEST_ISSUER,
            "aud": TEST_CLIENT_ID,
            "sub": "1234567890",
            "iat": now,
            "exp": now + 3600,
            "id": 1234567890,
            "name": "Test User",
            "preferred_username": "testuser",
        }
        claims.update(overrides)
        return jwt.encode(
            claims,
            rsa_private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    return _make


# ---------------------------------------------------------------------------
# App + config
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def app_config(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    monkeypatch.setenv("APP_TG_CLIENT_ID", TEST_CLIENT_ID)
    # Litestar's CookieBackendConfig requires exactly 16/24/32 bytes (AES key).
    monkeypatch.setenv("APP_SECRET_KEY", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("APP_JWT_SECRET", "test-jwt-secret-not-for-prod")
    monkeypatch.setenv("APP_JWT_ACCESS_TTL", "900")
    monkeypatch.setenv("APP_JWT_REFRESH_TTL", "604800")
    monkeypatch.setenv("APP_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("APP_DEBUG", "false")
    return AppConfig()


@pytest_asyncio.fixture
async def test_app(
    app_config: AppConfig, fake_jwks_client: PyJWKClient
) -> AsyncIterator[Litestar]:
    app = create_app(config=app_config, jwks_client=fake_jwks_client)
    container = app.state.dishka_container

    # Create schema directly (bypass Alembic for test speed).
    engine = await container.get(AsyncEngine)
    async with engine.begin() as conn:
        await conn.run_sync(BaseTable.metadata.create_all)

    yield app

    await container.close()


@pytest_asyncio.fixture
async def client(test_app: Litestar) -> AsyncIterator[AsyncTestClient]:
    # base_url must be HTTPS — the session cookie is configured with
    # ``secure=True`` for production, and httpx (which AsyncTestClient wraps)
    # refuses to send Secure cookies over plain HTTP.
    async with AsyncTestClient(app=test_app, base_url="https://testserver") as c:
        yield c


# ---------------------------------------------------------------------------
# Bare DB session for repository unit tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine(db_path: Path) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(BaseTable.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session

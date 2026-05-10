"""Integration tests against a real Litestar app + SQLite DB.

The fake ``PyJWKClient`` is wired in via the ``test_app`` fixture in
``tests/conftest.py``. Tokens are signed with the matching test private key.
"""

from __future__ import annotations

from collections.abc import Callable

from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_302_FOUND,
    HTTP_401_UNAUTHORIZED,
)
from litestar.testing import AsyncTestClient


async def test_login_creates_user_and_sets_cookie(
    client: AsyncTestClient, make_id_token: Callable[..., str]
) -> None:
    token = make_id_token()

    response = await client.post("/api/v1/auth/telegram", json={"id_token": token})

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["name"] == "Test User"
    assert "session" in response.cookies


async def test_login_with_invalid_token_returns_401(
    client: AsyncTestClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/telegram", json={"id_token": "not-a-jwt"}
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert "Invalid id_token" in response.text


async def test_login_with_empty_token_returns_401(
    client: AsyncTestClient,
) -> None:
    response = await client.post("/api/v1/auth/telegram", json={"id_token": ""})

    assert response.status_code == HTTP_401_UNAUTHORIZED


async def test_app_route_redirects_anonymous_to_root(
    client: AsyncTestClient,
) -> None:
    response = await client.get("/app", follow_redirects=False)

    assert response.status_code in {HTTP_302_FOUND, 301, 303, 307}
    assert response.headers["location"] == "/"


async def test_index_redirects_when_logged_in(
    client: AsyncTestClient, make_id_token: Callable[..., str]
) -> None:
    await client.post("/api/v1/auth/telegram", json={"id_token": make_id_token()})

    response = await client.get("/", follow_redirects=False)

    assert response.status_code in {HTTP_302_FOUND, 301, 303, 307}
    assert response.headers["location"] == "/app"


async def test_app_renders_status_page_when_logged_in(
    client: AsyncTestClient, make_id_token: Callable[..., str]
) -> None:
    await client.post("/api/v1/auth/telegram", json={"id_token": make_id_token()})

    response = await client.get("/app")

    assert response.status_code == HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "You're signed in" in response.text
    assert "Test User" in response.text


async def test_logout_clears_session(
    client: AsyncTestClient, make_id_token: Callable[..., str]
) -> None:
    await client.post("/api/v1/auth/telegram", json={"id_token": make_id_token()})

    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == HTTP_204_NO_CONTENT

    after = await client.get("/app", follow_redirects=False)
    assert after.headers["location"] == "/"


async def test_app_self_heals_stale_session(
    client: AsyncTestClient, make_id_token: Callable[..., str]
) -> None:
    """Login → wipe DB user → next /app must clear cookie and redirect to /."""
    await client.post("/api/v1/auth/telegram", json={"id_token": make_id_token()})

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncEngine

    from tg_auth.adapters.database.tables import TelegramAccount, User

    container = client.app.state.dishka_container
    engine = await container.get(AsyncEngine)
    async with engine.begin() as conn:
        await conn.execute(delete(TelegramAccount))
        await conn.execute(delete(User))

    response = await client.get("/app", follow_redirects=False)
    assert response.status_code in {HTTP_302_FOUND, 301, 303, 307}
    assert response.headers["location"] == "/"


async def test_health_live_returns_ok(client: AsyncTestClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == HTTP_200_OK
    assert response.json() == {"status": "ok"}


async def test_health_ready_returns_ok(client: AsyncTestClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["status"] == "ok"
    assert any(c["name"] == "database" for c in body["checks"])

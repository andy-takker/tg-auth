"""HTTP route handlers, request/response DTOs, and the Telegram id_token verifier.

Persistence:
- ``AsyncSession`` injected via Dishka (``FromDishka[AsyncSession]``).
- :func:`tg_auth.repository.upsert_user_from_claims` maps OIDC claims to a
  persisted ``User`` + ``TelegramAccount``.

The Telegram OIDC config and the ``PyJWKClient`` are still read from
``request.app.state`` — they're per-app, not per-request.
"""

from http import HTTPStatus
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Request, get, post
from litestar.response import Redirect, Response, Template

from tg_auth.domain.entities.telegram import TelegramAuthDTO
from tg_auth.domain.entities.user import UserDTO
from tg_auth.domain.use_cases.fetch_user_by_id import FetchUserByIDUseCase
from tg_auth.domain.use_cases.upsert_user_from_telegram import (
    UpsertUserFromTelegramUseCase,
)


@get("/")
async def index(request: Request) -> Template | Redirect:
    if request.session.get("user"):
        return Redirect(path="/app")
    return Template("index.html")


@post("/api/v1/auth/telegram")
@inject
async def telegram_login(
    data: TelegramAuthDTO,
    request: Request,
    upsert_user_from_telegram: FromDishka[UpsertUserFromTelegramUseCase],
) -> Response[UserDTO]:
    user = await upsert_user_from_telegram.execute(data)

    request.session["user"] = {"id": str(user.id)}

    return Response(
        content=user,
        status_code=HTTPStatus.OK,
    )


@post("/api/v1/auth/logout", status_code=HTTPStatus.NO_CONTENT)
async def logout(request: Request) -> None:
    request.clear_session()


@get("/app")
@inject
async def app_route(
    request: Request,
    fetch_user_by_id: FromDishka[FetchUserByIDUseCase],
) -> UserDTO | Redirect:
    sess_user = request.session.get("user")
    if not sess_user:
        return Redirect(path="/")

    user_id = UUID(sess_user["id"])
    user = await fetch_user_by_id.execute(user_id)
    if user is None:
        # Session points at a user that no longer exists (DB wiped, manual
        # delete, fresh PoC after schema reset). Self-heal: drop the cookie
        # and bounce back to the login page so the user can re-auth.
        request.clear_session()
        return Redirect(path="/")

    return user


route_handlers = [index, telegram_login, logout, app_route]

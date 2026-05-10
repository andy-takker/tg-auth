"""Authentication-related HTTP routes.

Handlers stay thin: parse request → delegate to use case → shape response.
"""

from http import HTTPStatus
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Request, get, post
from litestar.response import Redirect, Response, Template

from tg_auth.domains.entities.telegram import TelegramAuthDTO
from tg_auth.domains.entities.user import UserDTO
from tg_auth.domains.use_cases.fetch_user_by_id import FetchUserByIDUseCase
from tg_auth.domains.use_cases.upsert_user_from_telegram import (
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
    return Response(content=user, status_code=HTTPStatus.OK)


@post("/api/v1/auth/logout", status_code=HTTPStatus.NO_CONTENT)
async def logout(request: Request) -> None:
    request.clear_session()


@get("/app")
@inject
async def app_route(
    request: Request,
    fetch_user_by_id: FromDishka[FetchUserByIDUseCase],
) -> Template | Redirect:
    sess_user = request.session.get("user")
    if not sess_user:
        return Redirect(path="/")

    user_id = UUID(sess_user["id"])
    user = await fetch_user_by_id.execute(user_id)
    if user is None:
        # Self-heal: session points at a deleted user (DB wiped, manual delete,
        # fresh PoC after schema reset). Drop the cookie and bounce to login.
        request.clear_session()
        return Redirect(path="/")

    return Template("app.html", context={"user": user})

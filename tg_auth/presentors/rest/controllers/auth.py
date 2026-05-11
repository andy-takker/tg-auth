"""Authentication-related HTTP routes.

Cookie session powers the HTML pages (``/`` and ``/app``).
JWT access + refresh tokens power the JSON API (``/api/v1/...``).
The two are issued together by ``POST /api/v1/auth/telegram``.
"""

from dataclasses import dataclass
from http import HTTPStatus
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Request, get, post
from litestar.exceptions import NotAuthorizedException
from litestar.response import Redirect, Response, Template

from tg_auth.domains.entities.telegram import TelegramAuthDTO
from tg_auth.domains.entities.tokens import TokenPair
from tg_auth.domains.entities.user import UserDTO, UserID
from tg_auth.domains.interfaces.tokens import InvalidTokenError, ITokenIssuer
from tg_auth.domains.use_cases.fetch_user_by_id import FetchUserByIDUseCase
from tg_auth.domains.use_cases.refresh_tokens import RefreshTokensUseCase
from tg_auth.domains.use_cases.upsert_user_from_telegram import (
    UpsertUserFromTelegramUseCase,
)


@dataclass(frozen=True, kw_only=True, slots=True)
class LoginResponse:
    user: UserDTO
    tokens: TokenPair


@dataclass(frozen=True, kw_only=True, slots=True)
class RefreshDTO:
    refresh_token: str


def _bearer_user_id(request: Request, token_issuer: ITokenIssuer) -> UserID:
    """Extract and validate the access token from the ``Authorization`` header.

    Returned UUID is the application user id encoded in the token's ``sub``
    claim. Raises ``NotAuthorizedException`` (→ 401) on any failure.
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise NotAuthorizedException(detail="Missing Bearer token")
    token = header.removeprefix("Bearer ").strip()
    try:
        return token_issuer.validate_access(token)
    except InvalidTokenError as e:
        raise NotAuthorizedException(detail=f"Invalid access token: {e}") from e


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
    token_issuer: FromDishka[ITokenIssuer],
) -> Response[LoginResponse]:
    user = await upsert_user_from_telegram.execute(data)

    # Cookie session for HTML pages.
    request.session["user"] = {"id": str(user.id)}

    # Bearer-token pair for API consumers.
    tokens = token_issuer.issue_pair(user.id)

    return Response(
        content=LoginResponse(user=user, tokens=tokens),
        status_code=HTTPStatus.OK,
    )


@post("/api/v1/auth/refresh", status_code=HTTPStatus.OK)
@inject
async def refresh_tokens(
    data: RefreshDTO,
    refresh_uc: FromDishka[RefreshTokensUseCase],
) -> TokenPair:
    return await refresh_uc.execute(data.refresh_token)


@post("/api/v1/auth/logout", status_code=HTTPStatus.NO_CONTENT)
async def logout(request: Request) -> None:
    """Clears the cookie session.

    Bearer tokens are stateless — the client just discards them. Add a
    revocation list (e.g. Redis) here if you need server-side invalidation.
    """
    request.clear_session()


@get("/api/v1/me")
@inject
async def me(
    request: Request,
    token_issuer: FromDishka[ITokenIssuer],
    fetch_user_by_id: FromDishka[FetchUserByIDUseCase],
) -> UserDTO:
    """Protected JSON endpoint — requires ``Authorization: Bearer <access>``."""
    user_id = _bearer_user_id(request, token_issuer)
    user = await fetch_user_by_id.execute(user_id)
    if user is None:
        raise NotAuthorizedException(detail="User no longer exists")
    return user


@get("/app")
@inject
async def app_route(
    request: Request,
    fetch_user_by_id: FromDishka[FetchUserByIDUseCase],
) -> Template | Redirect:
    sess_user = request.session.get("user")
    if not sess_user:
        return Redirect(path="/")

    user_id = UserID(UUID(sess_user["id"]))
    user = await fetch_user_by_id.execute(user_id)
    if user is None:
        # Self-heal: session points at a deleted user (DB wiped, manual delete,
        # fresh PoC after schema reset). Drop the cookie and bounce to login.
        request.clear_session()
        return Redirect(path="/")

    return Template("app.html", context={"user": user})

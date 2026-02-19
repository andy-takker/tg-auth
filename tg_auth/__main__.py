import hmac
import time
from dataclasses import dataclass
from hashlib import sha256
from http import HTTPStatus
from os import environ
from pathlib import Path
from uuid import UUID, uuid4

from litestar import Litestar, Request, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.response import Redirect, Response, Template
from litestar.template.config import TemplateConfig


def verify_telegram_login(
    payload: dict, bot_token: str, max_age_seconds: int = 300
) -> dict:
    if not bot_token:
        raise ValueError("BOT_TOKEN is empty")

    if "hash" not in payload:
        raise ValueError("Missing 'hash' in payload")

    auth_date = payload.get("auth_date")
    if auth_date is None:
        raise ValueError("Missing 'auth_date' in payload")

    # auth_date can come as str/int; normalize
    try:
        auth_date_int = int(auth_date)
    except (TypeError, ValueError) as e:
        raise ValueError("Invalid 'auth_date'") from e

    now = int(time.time())
    if now - auth_date_int > max_age_seconds:
        raise ValueError("Auth data is too old")

    received_hash = str(payload["hash"])

    # Build data_check_string (exclude hash)
    pairs = []
    for k, v in payload.items():
        if k == "hash":
            continue
        pairs.append(f"{k}={v}")
    data_check_string = "\n".join(sorted(pairs))

    secret_key = sha256(bot_token.encode("utf-8")).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid Telegram hash")

    return payload


@dataclass
class TelegramLoginDTO:
    id: int
    first_name: str
    auth_date: int
    hash: str

    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


@dataclass
class TelegramUserDTO:
    id: int
    user_id: UUID
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None


BOT_TOKEN = environ["APP_BOT_TOKEN"]
SECRET_KEY = environ["APP_SECRET_KEY"]

telegram_users: dict[UUID, TelegramUserDTO] = {}


@get("/")
async def index(request: Request) -> Template | Redirect:
    if request.session.get("user"):
        return Redirect(path="/app")
    return Template("./index.html")


@post("/api/v1/auth/telegram")
async def telegram_login(
    data: TelegramLoginDTO, request: Request
) -> Response[TelegramUserDTO]:
    payload = data.__dict__.copy()
    verified = verify_telegram_login(payload, bot_token=BOT_TOKEN, max_age_seconds=300)

    telegram_user = TelegramUserDTO(
        id=int(verified["id"]),
        user_id=uuid4(),
        username=verified.get("username"),
        first_name=verified.get("first_name"),
        last_name=verified.get("last_name"),
        photo_url=verified.get("photo_url"),
    )

    telegram_users[telegram_user.user_id] = telegram_user

    request.session["user"] = {
        "id": str(telegram_user.user_id),
    }

    return Response(
        content=telegram_user,
        status_code=HTTPStatus.OK,
    )


@get("/app")
async def app_route(request: Request) -> TelegramUserDTO | None:
    user = request.session.get("user")
    if user:
        return telegram_users[UUID(user["id"])]
    return None


cookie_backend_config = CookieBackendConfig(
    secret=SECRET_KEY.encode("utf-8"),
    key="session",
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=60 * 60 * 24 * 30,  # 30 дней
)

app = Litestar(
    route_handlers=[telegram_login, index, app_route],
    middleware=[cookie_backend_config.middleware],
    template_config=TemplateConfig(
        directory=Path("./"),
        engine=JinjaTemplateEngine,
    ),
)

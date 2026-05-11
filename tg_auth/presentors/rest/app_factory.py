from pathlib import Path

from dishka import AsyncContainer, make_async_container
from dishka.integrations.litestar import setup_dishka
from jwt import PyJWKClient
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.template.config import TemplateConfig

from tg_auth.adapters.database.config import DatabaseConfig
from tg_auth.adapters.database.di import DatabaseProvider
from tg_auth.adapters.healthcheck.di import HealthcheckProvider
from tg_auth.adapters.jwt.di import JwtProvider
from tg_auth.application.config import AppConfig, JwtConfig
from tg_auth.domains.di import DomainProvider
from tg_auth.presentors.rest.controllers import route_handlers

TEMPLATES_PATH = Path(__file__).parent / "templates"


def create_app(
    config: AppConfig,
    *,
    jwks_client: PyJWKClient | None = None,
) -> Litestar:
    """Build the Litestar application.

    ``jwks_client`` is exposed as a parameter so tests can inject a fake one
    without monkey-patching. In normal use it's built from the config.
    """
    cookie_backend_config = CookieBackendConfig(
        secret=config.session.secret_key.encode("utf-8"),
        key=config.session.cookie_name,
        httponly=True,
        # SameSite=Lax + httponly is enough for our same-origin cookie flow.
        # ``secure`` stays True so the cookie is only sent over HTTPS.
        secure=True,
        samesite="lax",
        max_age=config.session.max_age_seconds,
    )

    if jwks_client is None:
        jwks_client = PyJWKClient(
            config.telegram.jwks_url, cache_keys=True, lifespan=600
        )

    container: AsyncContainer = make_async_container(
        DatabaseProvider(),
        DomainProvider(),
        HealthcheckProvider(),
        JwtProvider(),
        context={
            AppConfig: config,
            DatabaseConfig: config.database,
            JwtConfig: config.jwt,
            PyJWKClient: jwks_client,
        },
    )

    # In-memory rate limit on the auth POST. PoC scope — for prod swap the
    # store for Redis (litestar.stores.redis) so it's shared across replicas.
    rate_limit = RateLimitConfig(
        rate_limit=("minute", 30),
        # Anchored regexes — Litestar joins this list with `|` and an
        # un-anchored "/" greedily matches every path, disabling the limiter.
        exclude=[
            r"^/$",
            r"^/app$",
            r"^/health/live$",
            r"^/health/ready$",
            r"^/api/v1/auth/logout$",
            r"^/api/v1/auth/refresh$",
            r"^/api/v1/me$",
        ],
    )

    app = Litestar(
        route_handlers=route_handlers,
        middleware=[cookie_backend_config.middleware, rate_limit.middleware],
        template_config=TemplateConfig(
            directory=TEMPLATES_PATH,
            engine=JinjaTemplateEngine,
        ),
        logging_config=None,
        debug=config.debug,
    )

    # Expose shared resources to handlers via request.app.state.*
    app.state.config = config
    app.state.jwks_client = jwks_client
    app.state.dishka_container = container

    # Wires container lifecycle (close on shutdown) and request-scope sessions.
    setup_dishka(container=container, app=app)

    return app

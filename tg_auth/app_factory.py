from pathlib import Path

from dishka import make_async_container
from dishka.integrations.litestar import setup_dishka
from jwt import PyJWKClient
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.template.config import TemplateConfig

from tg_auth.adapters.database.config import DatabaseConfig
from tg_auth.adapters.database.di import DatabaseProvider
from tg_auth.config import AppConfig
from tg_auth.domain.di import DomainProvider
from tg_auth.routers import route_handlers

PROJECT_PATH = Path(__file__).parent


def create_app(config: AppConfig) -> Litestar:
    cookie_backend_config = CookieBackendConfig(
        secret=config.session.secret_key.encode("utf-8"),
        key=config.session.cookie_name,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=config.session.max_age_seconds,
    )

    # PyJWKClient caches keys in-process and refreshes when an unknown `kid`
    # shows up. One instance per app is enough.
    jwks_client = PyJWKClient(config.telegram.jwks_url, cache_keys=True, lifespan=600)

    container = make_async_container(
        DatabaseProvider(),
        DomainProvider(),
        context={
            AppConfig: config,
            DatabaseConfig: config.database,
            PyJWKClient: jwks_client,
        },
    )

    app = Litestar(
        route_handlers=route_handlers,
        middleware=[cookie_backend_config.middleware],
        template_config=TemplateConfig(
            directory=PROJECT_PATH,
            engine=JinjaTemplateEngine,
        ),
        logging_config=None,
        debug=config.debug,
    )

    # Expose shared resources to handlers via request.app.state.*
    app.state.config = config
    app.state.jwks_client = jwks_client

    # Wires container lifecycle (close on shutdown) and request-scope sessions.
    setup_dishka(container=container, app=app)

    return app

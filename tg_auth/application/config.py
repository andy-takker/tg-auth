"""Application-level configuration.

Frozen dataclasses initialised from environment variables via
``default_factory`` lambdas. Per-adapter sub-configs (e.g. ``DatabaseConfig``)
live next to their adapter and are aggregated here.
"""

from dataclasses import dataclass, field
from os import environ

from tg_auth.adapters.database.config import DatabaseConfig


@dataclass(frozen=True, kw_only=True, slots=True)
class TelegramConfig:
    """Telegram OIDC client configuration."""

    client_id: str = field(default_factory=lambda: environ["APP_TG_CLIENT_ID"])
    issuer: str = "https://oauth.telegram.org"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"


@dataclass(frozen=True, kw_only=True, slots=True)
class SessionConfig:
    """Cookie-backed session configuration."""

    secret_key: str = field(default_factory=lambda: environ["APP_SECRET_KEY"])
    cookie_name: str = "session"
    max_age_seconds: int = 60 * 60 * 24 * 30  # 30 days


@dataclass(frozen=True, kw_only=True, slots=True)
class HttpConfig:
    host: str = field(default_factory=lambda: environ.get("APP_HTTP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(environ.get("APP_HTTP_PORT", 8000)))


@dataclass(frozen=True, kw_only=True, slots=True)
class AppConfig:
    telegram: TelegramConfig = field(default_factory=lambda: TelegramConfig())
    session: SessionConfig = field(default_factory=lambda: SessionConfig())
    http: HttpConfig = field(default_factory=lambda: HttpConfig())
    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig())
    debug: bool = field(
        default_factory=lambda: environ.get("APP_DEBUG", "true").lower() == "true"
    )

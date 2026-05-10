from dataclasses import dataclass, field
from os import environ


@dataclass(frozen=True, kw_only=True, slots=True)
class DatabaseConfig:
    dsn: str = field(
        default_factory=lambda: environ.get(
            "APP_DB_URL", "sqlite+aiosqlite:///./tg_auth.db"
        )
    )
    echo: bool = field(
        default_factory=lambda: environ.get("APP_DB_ECHO", "false").lower() == "true"
    )
    pool_size: int = field(
        default_factory=lambda: int(environ.get("APP_DATABASE_POOL_SIZE", 10))
    )
    max_overflow: int = field(
        default_factory=lambda: int(environ.get("APP_DATABASE_MAX_OVERFLOW", 10))
    )
    pool_timeout: int = field(
        default_factory=lambda: int(environ.get("APP_DATABASE_POOL_TIMEOUT", 10))
    )

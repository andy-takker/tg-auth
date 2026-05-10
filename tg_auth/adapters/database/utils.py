import os
from argparse import Namespace
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Final
from uuid import UUID

import orjson
import sqlalchemy.dialects.postgresql as pg
from alembic.config import Config
from sqlalchemy import Index, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

PROJECT_PATH: Final = Path(__file__).parent.parent.parent
ALEMBIC_INI_PATH: Final[Path] = PROJECT_PATH / "adapters" / "database" / "alembic.ini"
WHERE_ACTIVE = text("deleted_at IS NULL")


@asynccontextmanager
async def create_engine(
    dsn: str, debug: bool, pool_size: int, pool_timeout: int, max_overflow: int
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        url=dsn,
        echo=debug,
        pool_size=pool_size,
        pool_timeout=pool_timeout,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        json_serializer=_orjson_dumps,
        json_deserializer=orjson.loads,
    )
    yield engine
    await engine.dispose()


def create_sessionmaker(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


def make_alembic_config(cmd_opts: Namespace, pg_url: str) -> Config:
    config = Config(
        file_=ALEMBIC_INI_PATH,
        ini_section=cmd_opts.name,
        cmd_opts=cmd_opts,
    )

    alembic_location = config.get_main_option("script_location")
    if not alembic_location:
        raise ValueError

    if not os.path.isabs(alembic_location):
        config.set_main_option("script_location", str(PROJECT_PATH / alembic_location))

    config.set_main_option("sqlalchemy.url", pg_url)

    config.attributes["configure_logger"] = False

    return config


def make_pg_enum(enum_cls: type[Enum], **kwargs: Any) -> pg.ENUM:
    return pg.ENUM(
        enum_cls,
        values_callable=_choices,
        **kwargs,
    )


def _choices(enum_cls: type[Enum]) -> tuple[str, ...]:
    return tuple(map(str, enum_cls))


def uq_active_ix(*cols: str, name: str | None = None) -> Index:
    return Index(name, *cols, unique=True, postgresql_where=WHERE_ACTIVE)


def _decimal_to_str(v: Decimal) -> str:
    s = format(v, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return _decimal_to_str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError


def _orjson_dumps(obj: Any, *, default: Callable[[Any], Any] = _default) -> str:
    return orjson.dumps(
        obj,
        default=default,
        option=(orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_UUID | orjson.OPT_UTC_Z),
    ).decode()

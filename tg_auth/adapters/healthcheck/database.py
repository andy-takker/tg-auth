"""Database readiness probe — runs ``SELECT 1`` against the configured engine."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tg_auth.domains.entities.healthcheck import HealthcheckResult, HealthcheckStatus


class DatabaseHealthcheck:
    name = "database"

    def __init__(self, engine: AsyncEngine, timeout: float = 2.0) -> None:
        self._engine = engine
        self._timeout = timeout

    async def check(self) -> HealthcheckResult:
        try:
            async with asyncio.timeout(self._timeout):
                async with self._engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
        except Exception as e:  # noqa: BLE001
            return HealthcheckResult(
                name=self.name,
                status=HealthcheckStatus.DOWN,
                detail=f"{type(e).__name__}: {e}",
            )
        return HealthcheckResult(name=self.name, status=HealthcheckStatus.OK)

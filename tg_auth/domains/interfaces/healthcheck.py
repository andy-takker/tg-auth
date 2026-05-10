from typing import Protocol

from tg_auth.domains.entities.healthcheck import HealthcheckResult


class IHealthcheck(Protocol):
    """A single readiness probe — e.g. the database, an outbound HTTP API.

    Implementations live under ``tg_auth/adapters/healthcheck/``.
    """

    name: str

    async def check(self) -> HealthcheckResult: ...

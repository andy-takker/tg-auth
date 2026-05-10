import asyncio
from collections.abc import Sequence

from tg_auth.domains.entities.healthcheck import HealthcheckResult, HealthcheckStatus
from tg_auth.domains.interfaces.healthcheck import IHealthcheck


class CheckReadinessUseCase:
    """Run every registered healthcheck in parallel and aggregate the result."""

    def __init__(self, healthchecks: Sequence[IHealthcheck]) -> None:
        self._healthchecks = healthchecks

    async def execute(self) -> tuple[HealthcheckStatus, list[HealthcheckResult]]:
        if not self._healthchecks:
            return HealthcheckStatus.OK, []

        results = await asyncio.gather(
            *(hc.check() for hc in self._healthchecks), return_exceptions=False
        )
        overall = (
            HealthcheckStatus.OK
            if all(r.status == HealthcheckStatus.OK for r in results)
            else HealthcheckStatus.DOWN
        )
        return overall, list(results)

from collections.abc import Sequence

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine

from tg_auth.adapters.healthcheck.database import DatabaseHealthcheck
from tg_auth.domains.interfaces.healthcheck import IHealthcheck


class HealthcheckProvider(Provider):
    @provide(scope=Scope.APP)
    def database_healthcheck(self, engine: AsyncEngine) -> DatabaseHealthcheck:
        return DatabaseHealthcheck(engine=engine)

    @provide(scope=Scope.APP)
    def healthchecks(self, database: DatabaseHealthcheck) -> Sequence[IHealthcheck]:
        # Add more probes here as the system grows (Redis, NATS, outbound HTTP).
        return [database]

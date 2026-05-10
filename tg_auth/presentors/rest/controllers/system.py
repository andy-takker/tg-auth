"""System / observability routes — liveness and readiness probes."""

from http import HTTPStatus

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import get
from litestar.exceptions import HTTPException

from tg_auth.domains.entities.healthcheck import HealthcheckStatus
from tg_auth.domains.use_cases.check_readiness import CheckReadinessUseCase


@get("/health/live", sync_to_thread=False)
def health_live() -> dict[str, str]:
    """Liveness probe — process is alive and the event loop is responsive.

    Always returns 200; orchestrators interpret a non-200 (or timeout) as
    "kill and restart this process".
    """
    return {"status": "ok"}


@get("/health/ready")
@inject
async def health_ready(
    check_readiness: FromDishka[CheckReadinessUseCase],
) -> dict[str, object]:
    """Readiness probe — the process can serve traffic (DB reachable, etc.).

    Returns 200 with per-component status when everything's up, 503 otherwise.
    """
    overall, results = await check_readiness.execute()
    payload: dict[str, object] = {
        "status": overall.value,
        "checks": [
            {"name": r.name, "status": r.status.value, "detail": r.detail}
            for r in results
        ],
    }
    if overall != HealthcheckStatus.OK:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=payload,  # type: ignore[arg-type]
        )
    return payload

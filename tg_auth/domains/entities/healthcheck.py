from dataclasses import dataclass
from enum import StrEnum, unique


@unique
class HealthcheckStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass(frozen=True, kw_only=True, slots=True)
class HealthcheckResult:
    name: str
    status: HealthcheckStatus
    detail: str | None = None

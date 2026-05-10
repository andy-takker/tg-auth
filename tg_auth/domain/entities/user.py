from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class UserDTO:
    id: UUID
    name: str | None = None
    phone_number: str | None = None

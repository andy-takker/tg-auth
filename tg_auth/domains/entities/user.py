from dataclasses import dataclass
from typing import NewType
from uuid import UUID

UserID = NewType("UserID", UUID)


@dataclass(frozen=True, kw_only=True, slots=True)
class UserDTO:
    id: UserID
    name: str | None = None
    phone_number: str | None = None

"""Domain-level interface for the users repository.

Use cases depend on this Protocol, never on the concrete SQLAlchemy
implementation in ``tg_auth.adapters.database``. That keeps the dependency
direction inbound (adapters → domains, not the other way).
"""

from typing import Any, Protocol
from uuid import UUID

from tg_auth.domains.entities.user import UserDTO


class IUsersRepository(Protocol):
    async def upsert_user_from_claims(self, claims: dict[str, Any]) -> UserDTO:
        """Idempotently turn Telegram OIDC claims into a persisted user.

        Lookup precedence:
        1. existing telegram_account by ``telegram_id`` (returning user);
        2. existing user by ``phone_number`` (cross-channel link);
        3. create new user + telegram_account.
        """
        ...

    async def fetch_user_by_id(self, user_id: UUID) -> UserDTO | None: ...

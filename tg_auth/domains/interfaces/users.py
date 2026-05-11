from abc import ABC, abstractmethod
from typing import Any

from tg_auth.domains.entities.user import UserDTO, UserID


class IUsersRepository(ABC):
    @abstractmethod
    async def upsert_user_from_claims(self, claims: dict[str, Any]) -> UserDTO:
        """Idempotently turn Telegram OIDC claims into a persisted user.

        Lookup precedence:
        1. existing telegram_account by ``telegram_id`` (returning user);
        2. existing user by ``phone_number`` (cross-channel link);
        3. create new user + telegram_account.
        """
        pass

    @abstractmethod
    async def fetch_user_by_id(self, user_id: UserID) -> UserDTO | None:
        pass

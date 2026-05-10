from typing import Any

import jwt
from jwt import PyJWKClient
from litestar.exceptions import NotAuthorizedException

from tg_auth.adapters.database.repositories.users import UsersRepository
from tg_auth.domain.entities.telegram import TelegramAuthDTO
from tg_auth.domain.entities.user import UserDTO
from tg_auth.domain.uow import AbstractUow


class UpsertUserFromTelegramUseCase:
    def __init__(
        self,
        uow: AbstractUow,
        jwks_client: PyJWKClient,
        users_repo: UsersRepository,
        telegram_client_id: str,
        telegram_issuer: str,
    ) -> None:
        self._uow = uow
        self._jwks_client = jwks_client
        self._telegram_client_id = telegram_client_id
        self._telegram_issuer = telegram_issuer
        self._users_repo = users_repo

    async def execute(self, telegram_dto: TelegramAuthDTO) -> UserDTO:
        try:
            claims = _verify_telegram_id_token(
                id_token=telegram_dto.id_token,
                jwks_client=self._jwks_client,
                telegram_client_id=self._telegram_client_id,
                telegram_issuer=self._telegram_issuer,
            )
        except (jwt.PyJWTError, ValueError) as e:
            raise NotAuthorizedException(detail=f"Invalid id_token: {e}") from e
        async with self._uow:
            user = await self._users_repo.upsert_user_from_claims(claims)
        return UserDTO(id=user.id, name=user.name, phone_number=user.phone_number)


def _verify_telegram_id_token(
    id_token: str,
    jwks_client: PyJWKClient,
    telegram_client_id: str,
    telegram_issuer: str,
) -> dict[str, Any]:
    """Validate a Telegram OIDC id_token (JWT) against the published JWKS."""
    if not id_token:
        raise ValueError("Empty id_token")

    signing_key = jwks_client.get_signing_key_from_jwt(id_token).key
    return jwt.decode(
        id_token,
        signing_key,
        algorithms=["RS256", "ES256"],
        audience=telegram_client_id,
        issuer=telegram_issuer,
        options={"require": ["iss", "aud", "exp", "iat", "sub"]},
        leeway=30,
    )

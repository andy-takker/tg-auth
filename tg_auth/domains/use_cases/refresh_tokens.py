from litestar.exceptions import NotAuthorizedException

from tg_auth.domains.entities.tokens import TokenPair
from tg_auth.domains.interfaces.tokens import InvalidTokenError, ITokenIssuer
from tg_auth.domains.interfaces.users import IUsersRepository
from tg_auth.domains.uow import AbstractUow


class RefreshTokensUseCase:
    """Validate a refresh token, confirm the user still exists, issue a new
    access + refresh pair (rotation)."""

    def __init__(
        self,
        uow: AbstractUow,
        token_issuer: ITokenIssuer,
        users_repo: IUsersRepository,
    ) -> None:
        self._uow = uow
        self._token_issuer = token_issuer
        self._users_repo = users_repo

    async def execute(self, refresh_token: str) -> TokenPair:
        try:
            user_id = self._token_issuer.validate_refresh(refresh_token)
        except InvalidTokenError as e:
            raise NotAuthorizedException(detail=f"Invalid refresh token: {e}") from e

        async with self._uow:
            user = await self._users_repo.fetch_user_by_id(user_id)

        if user is None:
            raise NotAuthorizedException(detail="User no longer exists")

        return self._token_issuer.issue_pair(user.id)

from uuid import UUID

from tg_auth.domains.entities.user import UserDTO
from tg_auth.domains.interfaces.users import IUsersRepository
from tg_auth.domains.uow import AbstractUow


class FetchUserByIDUseCase:
    def __init__(
        self,
        uow: AbstractUow,
        users_repo: IUsersRepository,
    ) -> None:
        self._uow = uow
        self._users_repo = users_repo

    async def execute(self, user_id: UUID) -> UserDTO | None:
        async with self._uow:
            return await self._users_repo.fetch_user_by_id(user_id)

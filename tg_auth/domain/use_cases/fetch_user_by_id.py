from uuid import UUID

from tg_auth.adapters.database.repositories.users import UsersRepository
from tg_auth.domain.entities.user import UserDTO
from tg_auth.domain.uow import AbstractUow


class FetchUserByIDUseCase:
    def __init__(
        self,
        uow: AbstractUow,
        users_repo: UsersRepository,
    ) -> None:
        self._uow = uow
        self._users_repo = users_repo

    async def execute(self, user_id: UUID) -> UserDTO | None:
        async with self._uow:
            user = await self._users_repo.fetch_user_by_id(user_id)
        return (
            UserDTO(id=user.id, name=user.name, phone_number=user.phone_number)
            if user
            else None
        )

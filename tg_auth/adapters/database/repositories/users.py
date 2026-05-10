from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tg_auth.adapters.database.tables import TelegramAccount, User
from tg_auth.adapters.database.uow import SqlalchemyUow


class UsersRepository:
    def __init__(self, uow: SqlalchemyUow) -> None:
        self._uow = uow

    @property
    def _session(self) -> AsyncSession:
        return self._uow.session

    async def upsert_user_from_claims(self, claims: dict[str, Any]) -> User:
        telegram_id = int(claims.get("id", claims["sub"]))
        phone: str | None = claims.get("phone_number")
        name: str | None = claims.get("name")
        username: str | None = claims.get("preferred_username")
        picture: str | None = claims.get("picture")

        telegram_account = await self.fetch_telegram_account_with_user_by_id(
            telegram_id
        )
        if telegram_account is not None:
            telegram_account.username = username
            telegram_account.name = name
            telegram_account.picture = picture
            if phone:
                telegram_account.phone_number = phone
                if not telegram_account.user.phone_number:
                    telegram_account.user.phone_number = phone
            return telegram_account.user

        user: User | None = None
        if phone:
            user = await self.fetch_user_by_phone_number(phone)

        if user is None:
            user = User(phone_number=phone, name=name)
            self._session.add(user)
            await self._session.flush()

        self._session.add(
            TelegramAccount(
                user_id=user.id,
                telegram_id=telegram_id,
                username=username,
                name=name,
                picture=picture,
                phone_number=phone,
            )
        )
        await self._session.flush()
        return user

    async def fetch_telegram_account_with_user_by_id(
        self, telegram_id: int
    ) -> TelegramAccount | None:
        stmt = (
            select(TelegramAccount)
            .where(TelegramAccount.telegram_id == telegram_id)
            .options(selectinload(TelegramAccount.user))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def fetch_user_by_phone_number(self, phone_number: str) -> User | None:
        stmt = select(User).where(User.phone_number == phone_number)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def fetch_user_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

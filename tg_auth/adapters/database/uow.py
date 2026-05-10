import asyncio
import logging
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
)

from tg_auth.domains.uow import AbstractUow

logger = logging.getLogger(__name__)


class SessionUow(Protocol):
    @property
    def session(self) -> AsyncSession: ...


class SqlalchemyUow(AbstractUow):
    __session: AsyncSession | None
    __transaction: AsyncSessionTransaction | None
    session_factory: async_sessionmaker[AsyncSession]

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

        self.__session = None
        self.__transaction = None

    @property
    def session(self) -> AsyncSession:
        if self.__session is None:
            raise Exception("Session is not created")
        return self.__session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
        self.__transaction = None

    async def create_transaction(self) -> None:
        if self.__session is not None:
            logger.warning("Attempt to create already existing session")
            if self.__transaction is not None:
                raise Exception("Session is already in transaction")
            else:
                self.__transaction = await self.session.begin()
        else:
            self.__session = self.session_factory()
            self.__transaction = await self.session.begin()

    async def close_transaction(self, *exc: Any) -> None:
        try:
            close_task = asyncio.create_task(self.session.close())
            try:
                await close_task
            except asyncio.CancelledError:
                await close_task
                raise
        finally:
            self.__transaction = None
            self.__session = None

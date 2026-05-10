from collections.abc import AsyncIterator

from dishka import AnyOf, Provider, Scope, from_context, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from tg_auth.adapters.database.config import DatabaseConfig
from tg_auth.adapters.database.repositories.users import UsersRepository
from tg_auth.adapters.database.uow import SqlalchemyUow
from tg_auth.adapters.database.utils import create_engine, create_sessionmaker
from tg_auth.config import AppConfig
from tg_auth.domain.uow import AbstractUow


class DatabaseProvider(Provider):
    # Resolve types passed via context={...} in make_async_container.
    app_config = from_context(provides=AppConfig, scope=Scope.APP)
    database_config = from_context(provides=DatabaseConfig, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def engine(
        self,
        database_config: DatabaseConfig,
        app_config: AppConfig,
    ) -> AsyncIterator[AsyncEngine]:
        async with create_engine(
            dsn=database_config.dsn,
            pool_size=database_config.pool_size,
            pool_timeout=database_config.pool_timeout,
            max_overflow=database_config.max_overflow,
            debug=app_config.debug,
        ) as engine:
            yield engine

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_sessionmaker(engine=engine)

    @provide(scope=Scope.REQUEST)
    def uow(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> AnyOf[AbstractUow, SqlalchemyUow]:
        return SqlalchemyUow(
            session_factory=session_factory,
        )

    @provide(scope=Scope.REQUEST)
    def user_repository(self, uow: SqlalchemyUow) -> UsersRepository:
        return UsersRepository(uow=uow)

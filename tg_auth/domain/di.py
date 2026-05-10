from dishka import Provider, Scope, from_context, provide
from jwt import PyJWKClient

from tg_auth.adapters.database.repositories.users import UsersRepository
from tg_auth.config import AppConfig
from tg_auth.domain.uow import AbstractUow
from tg_auth.domain.use_cases.fetch_user_by_id import FetchUserByIDUseCase
from tg_auth.domain.use_cases.upsert_user_from_telegram import (
    UpsertUserFromTelegramUseCase,
)


class DomainProvider(Provider):
    scope = Scope.REQUEST

    # Resolve types passed via context={...} in make_async_container.
    app_config = from_context(provides=AppConfig, scope=Scope.APP)
    jwks_client = from_context(provides=PyJWKClient, scope=Scope.APP)

    @provide()
    def upsert_user_from_telegram(
        self,
        uow: AbstractUow,
        jwks_client: PyJWKClient,
        users_repo: UsersRepository,
        app_config: AppConfig,
    ) -> UpsertUserFromTelegramUseCase:
        return UpsertUserFromTelegramUseCase(
            uow=uow,
            jwks_client=jwks_client,
            users_repo=users_repo,
            telegram_client_id=app_config.telegram.client_id,
            telegram_issuer=app_config.telegram.issuer,
        )

    @provide()
    def fetch_user_by_id(
        self,
        uow: AbstractUow,
        users_repo: UsersRepository,
    ) -> FetchUserByIDUseCase:
        return FetchUserByIDUseCase(uow=uow, users_repo=users_repo)

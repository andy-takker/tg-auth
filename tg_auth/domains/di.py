from collections.abc import Sequence

from dishka import Provider, Scope, from_context, provide
from jwt import PyJWKClient

from tg_auth.application.config import AppConfig
from tg_auth.domains.interfaces.healthcheck import IHealthcheck
from tg_auth.domains.interfaces.users import IUsersRepository
from tg_auth.domains.uow import AbstractUow
from tg_auth.domains.use_cases.check_readiness import CheckReadinessUseCase
from tg_auth.domains.use_cases.fetch_user_by_id import FetchUserByIDUseCase
from tg_auth.domains.use_cases.upsert_user_from_telegram import (
    UpsertUserFromTelegramUseCase,
)


class DomainProvider(Provider):
    scope = Scope.REQUEST

    # Resolve types passed via context={...} in make_async_container.
    app_config = from_context(provides=AppConfig, scope=Scope.APP)
    jwks_client = from_context(provides=PyJWKClient, scope=Scope.APP)

    @provide
    def upsert_user_from_telegram(
        self,
        uow: AbstractUow,
        jwks_client: PyJWKClient,
        users_repo: IUsersRepository,
        app_config: AppConfig,
    ) -> UpsertUserFromTelegramUseCase:
        return UpsertUserFromTelegramUseCase(
            uow=uow,
            jwks_client=jwks_client,
            users_repo=users_repo,
            telegram_client_id=app_config.telegram.client_id,
            telegram_issuer=app_config.telegram.issuer,
        )

    @provide
    def fetch_user_by_id(
        self,
        uow: AbstractUow,
        users_repo: IUsersRepository,
    ) -> FetchUserByIDUseCase:
        return FetchUserByIDUseCase(uow=uow, users_repo=users_repo)

    @provide
    def check_readiness(
        self,
        healthchecks: Sequence[IHealthcheck],
    ) -> CheckReadinessUseCase:
        return CheckReadinessUseCase(healthchecks=healthchecks)

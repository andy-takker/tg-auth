from dishka import AnyOf, Provider, Scope, from_context, provide

from tg_auth.adapters.jwt.tokens import JwtTokenIssuer
from tg_auth.application.config import JwtConfig
from tg_auth.domains.interfaces.tokens import ITokenIssuer


class JwtProvider(Provider):
    jwt_config = from_context(provides=JwtConfig, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def token_issuer(
        self, jwt_config: JwtConfig
    ) -> AnyOf[ITokenIssuer, JwtTokenIssuer]:
        return JwtTokenIssuer(config=jwt_config)

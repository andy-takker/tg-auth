from tg_auth.presentors.rest.controllers.auth import (
    app_route,
    index,
    logout,
    me,
    refresh_tokens,
    telegram_login,
)
from tg_auth.presentors.rest.controllers.system import health_live, health_ready

route_handlers = [
    index,
    telegram_login,
    refresh_tokens,
    logout,
    me,
    app_route,
    health_live,
    health_ready,
]

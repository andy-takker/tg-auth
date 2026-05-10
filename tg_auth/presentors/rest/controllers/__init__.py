from tg_auth.presentors.rest.controllers.auth import (
    app_route,
    index,
    logout,
    telegram_login,
)
from tg_auth.presentors.rest.controllers.system import health_live, health_ready

route_handlers = [
    index,
    telegram_login,
    logout,
    app_route,
    health_live,
    health_ready,
]

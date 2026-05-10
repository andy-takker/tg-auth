import uvicorn

from tg_auth.application.config import AppConfig
from tg_auth.application.logging import setup_logging
from tg_auth.presentors.rest.app_factory import create_app


def main() -> None:
    config = AppConfig()
    setup_logging()
    litestar_app = create_app(config=config)

    uvicorn.run(
        litestar_app,
        host=config.http.host,
        port=config.http.port,
        forwarded_allow_ips="*",
        log_config=None,
    )


if __name__ == "__main__":
    main()

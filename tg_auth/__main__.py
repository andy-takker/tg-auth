import uvicorn

from tg_auth.app_factory import create_app
from tg_auth.config import AppConfig
from tg_auth.logging import setup_logging


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

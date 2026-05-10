import argparse

from alembic.config import CommandLine

from tg_auth.adapters.database.config import DatabaseConfig
from tg_auth.adapters.database.utils import make_alembic_config
from tg_auth.application.logging import LoggingConfig, setup_logging


def main() -> None:
    log_config = LoggingConfig()
    setup_logging(
        log_level=log_config.log_level,
        use_json=log_config.use_json,
    )

    alembic = CommandLine()
    alembic.parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
    options = alembic.parser.parse_args()
    db_config = DatabaseConfig()
    if "cmd" not in options:
        alembic.parser.error("Too few arguments")
        exit(128)
    else:
        config = make_alembic_config(options, pg_url=db_config.dsn)
        alembic.run_cmd(config, options)
        exit()


if __name__ == "__main__":
    main()

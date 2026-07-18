from logging.config import fileConfig

from alembic import context

from db import Base, _build_database_url, engine

# Import models so Base.metadata picks up all tables
import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from alembic.ini with the runtime database URL
config.set_main_option("sqlalchemy.url", _build_database_url())


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Reuse the server engine so IAM mode injects a fresh RDS token when the
    # migration Job opens its connection. The default password mode remains
    # unchanged because the engine still uses _build_database_url().
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

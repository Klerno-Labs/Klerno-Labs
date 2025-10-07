"""Alembic environment script for Klerno Labs.

This sets up the SQLAlchemy context using the DATABASE_URL environment variable
if provided, otherwise falling back to the sqlite development database.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import models metadata if/when SQLAlchemy models are added.
# from app import models


def get_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./data/klerno.db")


# this is the Alembic Config object, which provides access to the values within
# the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:  # pragma: no cover
    fileConfig(config.config_file_name)

# Override URL from env var
config.set_main_option("sqlalchemy.url", get_url())


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Alembic's Config.get_section returns a mapping; cast to dict for static checkers
    from typing import cast

    section = cast("dict", config.get_section(config.config_ini_section))
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():  # pragma: no cover
    run_migrations_offline()
else:
    run_migrations_online()

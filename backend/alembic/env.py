from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ---- Carrega .env respeitando o comportamento padrão ----
# Por padrão usa backend/.env (igual era antes de eu mexer).
# Para usar outro arquivo (ex: .env.test), sete ENV_FILE=caminho
try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).resolve().parent.parent

    env_file = os.environ.get("ENV_FILE")
    if env_file:
        path = Path(env_file)
        if not path.is_absolute():
            path = (backend_dir / env_file).resolve()
        if path.exists():
            print(f"[alembic] Carregando env de: {path}")
            load_dotenv(path, override=True)
    else:
        # Modo padrão - carrega backend/.env se existir (não muda nada no dev)
        default = backend_dir / ".env"
        if default.exists():
            load_dotenv(default, override=False)  # override=False pra não sobrescrever vars já setadas
except ImportError:
    pass

# Sobrescreve a URL do alembic.ini com a DATABASE_URL do .env (se existir)
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the *same* Base the application uses so autogenerate sees every model.
from app.core.database import Base
from app import models  # noqa: F401  -- import side-effects register models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())

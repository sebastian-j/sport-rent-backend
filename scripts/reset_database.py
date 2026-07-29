import argparse
import asyncio
import subprocess
import sys
from collections.abc import Callable, Sequence

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


def confirm_database_reset(
    database_name: str,
    *,
    assume_yes: bool,
    input_function: Callable[[str], str] = input,
) -> bool:
    if assume_yes:
        return True

    confirmation = input_function(
        "This will permanently delete all data from database "
        f'"{database_name}". Type its name to continue: '
    )
    return confirmation == database_name


async def recreate_public_schema() -> None:
    reset_engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    try:
        async with reset_engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
    finally:
        await reset_engine.dispose()


def upgrade_database() -> None:
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")


def run_seed() -> None:
    subprocess.run(
        [sys.executable, "-m", "scripts.seed"],
        check=True,
    )


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recreate the database schema, migrate it and run all seeds.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the interactive database-name confirmation",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    parsed_arguments = parse_arguments(arguments)
    database_url = make_url(settings.database_url)
    database_name = database_url.database

    if not database_name:
        raise ValueError("DATABASE_URL must contain a database name")

    print(f"Target database: {database_url.render_as_string(hide_password=True)}")

    if not confirm_database_reset(
        database_name,
        assume_yes=parsed_arguments.yes,
    ):
        print("Database reset cancelled.")
        return 1

    print("Recreating public schema...")
    asyncio.run(recreate_public_schema())

    print("Applying migrations...")
    upgrade_database()

    print("Running the main seed script...")
    run_seed()

    print("Database reset completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

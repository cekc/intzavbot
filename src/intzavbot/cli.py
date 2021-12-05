from urllib.parse import urlparse

import click
from aiogram import Bot, Dispatcher
from aiogram.utils.executor import Executor
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from intzavbot.handlers.meta_handler import register_handlers
from intzavbot.models import Base


@click.group()
@click.option("--token", required=True, metavar="TOKEN", help="Telegram bot token")
@click.option("--db", required=True, metavar="CONN", help="database connection URI")
@click.option("--skip-updates", is_flag=True, default=False, help="Skip pending updates")
@click.option("--log-sql", is_flag=True, default=False, help="log SQL queries issued by ORM")
@click.pass_context
def cli(ctx: click.Context, token: str, db: str, skip_updates: bool, log_sql: bool) -> None:
    """
    Telegram bot for Intellectual Zavalinka game.
    """

    bot = Bot(token=token)
    dispatcher = Dispatcher(bot)

    url = make_url(db)
    if url.drivername.startswith("postgres"):
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername == "sqlite":
        url = url.set(drivername="sqlite+aiosqlite")
    elif url.drivername == "mysql":
        url = url.set(drivername="mysql+aiomysql")
    engine = create_async_engine(url, echo=log_sql)
    session_factory = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def create_tables(_):
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    register_handlers(dispatcher, session_factory)

    executor = Executor(dispatcher, skip_updates=skip_updates)
    executor.on_startup(create_tables)

    ctx.obj = executor


@cli.command()
@click.pass_obj
def polling(executor: Executor) -> None:
    """
    Start bot in long polling mode.
    """

    executor.start_polling()


@cli.command()
@click.option("--url", required=True, help="webhook URL")
@click.option("--host", required=True, help="app listen host")
@click.option("--port", type=int, required=True, help="app listen port")
@click.pass_obj
def webhook(executor: Executor, url: str, host: str, port: int) -> None:
    """
    Start bot in webhook mode.
    """

    async def prepare_webhook(dispatcher: Dispatcher) -> None:
        await dispatcher.bot.set_webhook(url)
    executor.on_startup(prepare_webhook)

    executor.start_webhook(urlparse(url).path, host=host, port=port)


def main() -> None:
    cli(auto_envvar_prefix="INTZAVBOT")

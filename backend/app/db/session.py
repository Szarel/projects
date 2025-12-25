from typing import AsyncIterator

import logging
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _sanitize_database_url(raw_url: str) -> tuple[URL, dict]:
    """Preserve incoming query params; translate sslmode to connect_args for asyncpg."""
    url = make_url(raw_url.strip())
    if url.drivername in {"postgresql", "postgres", "postgresql+psycopg2"}:
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    sslmode = query.get("sslmode")
    channel_binding = query.get("channel_binding")

    # Remove asyncpg-unsupported params from URL but keep their intent via connect_args
    if "sslmode" in query or "channel_binding" in query:
        query = {k: v for k, v in query.items() if k not in {"sslmode", "channel_binding"}}
        url = url.set(query=query)

    connect_args: dict = {}
    if sslmode in {"require", "verify-full", "verify-ca", "prefer"}:
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False
    else:
        # Default for Neon: require TLS even if sslmode not provided
        connect_args["ssl"] = True

    logger.info(
        "DB URL (masked): driver=%s host=%s db=%s user=%s sslmode=%s channel_binding=%s",
        url.drivername,
        url.host,
        url.database,
        url.username,
        sslmode,
        channel_binding,
    )
    return url, connect_args


_url, _connect_args = _sanitize_database_url(settings.database_url)

engine: AsyncEngine = create_async_engine(
    str(_url),
    future=True,
    echo=False,
    connect_args=_connect_args,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

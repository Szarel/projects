from typing import AsyncIterator

import logging
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _sanitize_database_url(raw_url: str) -> URL:
    """Drop ssl-related query params that asyncpg rejects; TLS enforced via connect_args."""
    url = make_url(raw_url.strip())
    # Force asyncpg driver when Postgres URL lacks it (Render/Neon often provide plain postgresql://)
    if url.drivername in {"postgresql", "postgres", "postgresql+psycopg2"}:
        url = url.set(drivername="postgresql+asyncpg")
    clean_query = {k: v for k, v in url.query.items() if k not in {"sslmode", "channel_binding"}}
    url = url.set(query=clean_query)
    logger.info(
        "DB URL (masked): driver=%s host=%s db=%s user=%s",
        url.drivername,
        url.host,
        url.database,
        url.username,
    )
    return url


engine: AsyncEngine = create_async_engine(
    str(_sanitize_database_url(settings.database_url)),
    future=True,
    echo=False,
    connect_args={"ssl": True},  # Require TLS for Neon/PG when URL lacks ssl params
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

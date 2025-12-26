from typing import AsyncIterator

import logging
import ssl
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
    # libpq semantics:
    # - require/prefer: encrypt without verifying cert chain/hostname
    # - verify-ca/verify-full: verify certificate (and hostname for verify-full)
    if sslmode == "disable":
        connect_args["ssl"] = False
    else:
        # Default is TLS on (Neon/Supabase require it). If sslmode is missing, treat as "require".
        effective_mode = sslmode or "require"
        if effective_mode in {"require", "prefer"}:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx
        elif effective_mode in {"verify-ca", "verify-full"}:
            ctx = ssl.create_default_context()
            ctx.check_hostname = effective_mode == "verify-full"
            ctx.verify_mode = ssl.CERT_REQUIRED
            connect_args["ssl"] = ctx
        else:
            # Unknown value: safest fallback is TLS without hostname verification.
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx

    # PgBouncer/Poolers: avoid prepared statements to prevent DuplicatePreparedStatementError.
    # Force both caches to zero on every connection.
    query = dict(url.query)
    connect_args["statement_cache_size"] = 0
    query["prepared_statement_cache_size"] = "0"
    url = url.set(query=query)

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
    _url.render_as_string(hide_password=False),
    future=True,
    echo=False,
    connect_args=_connect_args,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

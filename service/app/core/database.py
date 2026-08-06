"""Async SQLAlchemy engine, session factory, and request-scoped dependency.

Backend is chosen by DATABASE_URL: PostgreSQL (asyncpg) in production, SQLite
(aiosqlite) for local dev/testing. The same ORM models and migrations work on
both.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if _IS_SQLITE:
    # SQLite connections are file-locked and cheap; allow async access from any
    # worker thread.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(pool_size=5, max_overflow=10, pool_timeout=30)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if _IS_SQLITE:
    # SQLite disables foreign-key enforcement by default; turn it on so
    # ON DELETE CASCADE works. Registered on the sync engine behind the async one.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):  # pragma: no cover
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # critical for async: post-commit attr access must not lazy-load
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async session; rollback on error.

    No auto-commit at the end of the dependency: services commit explicitly
    after writes, so read-only endpoints never open a write transaction.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

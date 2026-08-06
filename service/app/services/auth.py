"""Authentication workflows: register, authenticate, token issuance/rotation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user import create_user as _create_user, get_user_by_identifier


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    return await _create_user(db, data)


async def authenticate_user(
    db: AsyncSession, identifier: str, password: str
) -> User | None:
    """Return the user if credentials match, else ``None``.

    Never distinguishes 'user not found' from 'wrong password' — both return
    None so the caller can't tell which and leak user existence.
    """
    user = await get_user_by_identifier(db, identifier)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def issue_token_pair(db: AsyncSession, user_id: int) -> tuple[str, str]:
    """Mint a new (access, refresh) pair and persist the refresh token's hash."""
    access = create_access_token(user_id)
    raw_refresh = create_refresh_token(user_id)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires_at,
            revoked=False,
        )
    )
    await db.commit()
    return access, raw_refresh


async def get_valid_refresh_token(
    db: AsyncSession, token_hash: str
) -> RefreshToken | None:
    """Return the row iff it exists, is not revoked, and has not expired.

    Expiry is filtered in SQL with ``func.now()`` so it works uniformly on
    PostgreSQL and SQLite (no Python tz-aware vs naive comparison).
    """
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > func.now(),
        )
    )
    return result.scalar_one_or_none()


async def rotate_refresh_token(
    db: AsyncSession, token: RefreshToken
) -> tuple[str, str]:
    """Revoke *token* and issue a fresh pair for its owner.

    Fail-closed: the revoke commits before the new pair is issued, so if the
    second step fails the user simply re-logs in (no token is left usable).
    """
    user_id = token.user_id
    token.revoked = True
    await db.commit()
    return await issue_token_pair(db, user_id)

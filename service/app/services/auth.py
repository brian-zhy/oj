"""Authentication workflows: register, authenticate, token issuance/rotation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, update
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

logger = logging.getLogger(__name__)


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
    await _prune_live_tokens(db, user_id)
    return access, raw_refresh


async def _prune_live_tokens(db: AsyncSession, user_id: int) -> None:
    """把该用户的有效 refresh 行数压到 ``MAX_LIVE_REFRESH_TOKENS`` 以内。

    轮换宽限期允许同一个旧令牌在极短窗口内换出多对令牌（见
    ``within_rotation_grace``），若不设上限，循环重放就能无限插入有效行。
    超出时撤销最早的行——正常多设备登录远达不到这个数量。
    """
    ids = (
        await db.execute(
            select(RefreshToken.id)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at > func.now(),
            )
            .order_by(RefreshToken.id.asc())
        )
    ).scalars().all()
    surplus = len(ids) - settings.MAX_LIVE_REFRESH_TOKENS
    if surplus <= 0:
        return
    doomed = ids[:surplus]
    # 只置 revoked，不写 rotated_at：这是主动作废，不给重放留窗口。
    result = await db.execute(
        update(RefreshToken).where(RefreshToken.id.in_(doomed)).values(revoked=True)
    )
    await db.commit()
    logger.info(
        "用户 %s 有效 refresh 令牌超出上限，撤销最早的 %d 行", user_id, result.rowcount
    )


async def revoke_user_tokens(db: AsyncSession, user_id: int) -> int:
    """Revoke all live refresh tokens of *user_id* (e.g. on ban / password reset).

    ``get_current_user`` treats "no live refresh token" as "logged out", so
    revoking here kicks every existing session on the user's next request.
    Returns the number of tokens revoked.

    同样只置 ``revoked`` 而不写 ``rotated_at``：改密/封禁这类主动作废必须立刻
    失效，不能被轮换宽限期放行。另外必须把**正处于轮换宽限期内**的行
    （revoked=True 且 rotated_at 非空）的宽限资格一并取消——否则封禁后
    旧令牌仍能在宽限窗内换出新对，踢人形同虚设。
    """
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.rotated_at.isnot(None),
            ),
        )
    )
    tokens = result.scalars().all()
    grace = timedelta(seconds=settings.REFRESH_ROTATION_GRACE_SECONDS + 1)
    for token in tokens:
        token.revoked = True
        # 处于轮换宽限期的行：把 rotated_at 回拨出宽限窗口（保留非空以维持
        # 「曾轮换」的语义），主动作废因此不会被宽限期放行
        if token.rotated_at is not None:
            token.rotated_at = _as_utc(token.rotated_at) - grace
    if tokens:
        await db.commit()
    return len(tokens)


def _as_utc(value: datetime) -> datetime:
    """把库里取出的时间统一成 UTC aware。

    SQLite 的 ``DateTime(timezone=True)`` 读回来是 naive，PostgreSQL 是 aware；
    两者直接相减会抛 "can't subtract offset-naive and offset-aware datetimes"。
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def within_rotation_grace(token: RefreshToken) -> bool:
    """已作废的令牌是否仍处在轮换宽限期内（可被并发重放合法使用）。

    只有轮换会写下 ``rotated_at``；主动吊销（改密、封禁、超出数量上限）以及本列
    引入前的历史行都留空，一律按「不在宽限期内」处理——宁可让用户重新登录，
    也不给本该立刻失效的令牌续命。
    """
    if not token.revoked or token.rotated_at is None:
        return False
    elapsed = _as_utc(datetime.now(timezone.utc)) - _as_utc(token.rotated_at)
    return elapsed <= timedelta(seconds=settings.REFRESH_ROTATION_GRACE_SECONDS)


async def get_refresh_token_row(
    db: AsyncSession, token_hash: str
) -> RefreshToken | None:
    """Return the row iff it exists and has not expired — **ignoring** the
    revoked flag, so the caller can tell "真失效" apart from "宽限期内的重放".

    Expiry is filtered in SQL with ``func.now()`` so it works uniformly on
    PostgreSQL and SQLite (no Python tz-aware vs naive comparison).
    """
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
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

    宽限期内的重放（``token.revoked`` 已由上一次轮换置位）直接放行签新对，
    不重复改写 ``rotated_at``——否则输掉竞态的那个请求会把宽限窗口重新推后。
    """
    user_id = token.user_id
    if not token.revoked:
        token.revoked = True
        token.rotated_at = datetime.now(timezone.utc)
        await db.commit()
    return await issue_token_pair(db, user_id)

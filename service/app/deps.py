"""Shared FastAPI dependencies."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.user import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="tokens")
# auto_error=False 版本：无 token 时返回 None 而不是 401，供可选认证依赖使用
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="tokens", auto_error=False)


async def _has_live_refresh_token(db: AsyncSession, user_id: int) -> bool:
    """该用户是否仍持有有效的刷新令牌（被删除/吊销即视为登录已失效）。"""
    result = await db.execute(
        select(RefreshToken.id)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
        )
        .limit(1)
    )
    return result.scalar() is not None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise credentials_exc
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exc
    # 令牌吊销检查：刷新令牌被清除（如密码被重置）的用户的下一次请求立即失效
    if not await _has_live_refresh_token(db, user_id):
        raise credentials_exc
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选的当前用户依赖，用于允许未认证用户访问的路由"""
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
        user = await get_user_by_id(db, user_id)
        if user is not None and not await _has_live_refresh_token(db, user_id):
            return None
        return user
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        return None

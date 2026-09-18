"""令牌资源路由：签发（登录）、轮换（刷新）。"""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, hash_token
from app.schemas.auth import RefreshRequest, TokenResponse
from app.services import auth as auth_service
from app.services.auth import get_valid_refresh_token, rotate_refresh_token
from app.services.user import get_user_by_id
from app.utils.ip import get_client_ip
from app.utils.ratelimit import check

router = APIRouter(prefix="/tokens", tags=["tokens"])

# 按 IP 限流：签发 10 次/分钟（防撞库），刷新 30 次/分钟（正常轮换远低于此）
_TOKEN_ISSUE_LIMIT = (10, 60)
_TOKEN_REFRESH_LIMIT = (30, 60)


def _check_ip_limit(request: Request, action: str, limit: tuple[int, int]) -> None:
    max_requests, window = limit
    ok, wait = check(f"ip:{action}:{get_client_ip(request)}", max_requests, window)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁，请 {wait} 秒后再试",
        )


@router.post("", response_model=TokenResponse, summary="登录（签发令牌）")
async def create_token(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """用凭据换取一对 access + refresh 令牌。

    OAuth2 的 ``username`` 表单字段可填**用户名或邮箱**。
    """
    _check_ip_limit(request, "issue", _TOKEN_ISSUE_LIMIT)
    user = await auth_service.authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员",
        )
    access, refresh = await auth_service.issue_token_pair(db, user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌（轮换）")
async def rotate_token(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """用有效的 refresh 令牌换取新的一对令牌。

    提交的 refresh 令牌会被作废（轮换），再次使用将返回 401。
    """
    _check_ip_limit(request, "refresh", _TOKEN_REFRESH_LIMIT)
    try:
        decode_token(payload.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的刷新令牌",
        )
    token = await get_valid_refresh_token(db, hash_token(payload.refresh_token))
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的刷新令牌",
        )
    # 封禁用户不再续发令牌（封禁前已登录的会话由此断粮）
    user = await get_user_by_id(db, token.user_id)
    if user is None or user.is_banned:
        token.revoked = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员",
        )
    access, new_refresh = await rotate_refresh_token(db, token)
    return TokenResponse(access_token=access, refresh_token=new_refresh)

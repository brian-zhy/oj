"""令牌资源路由：签发（登录）、轮换（刷新）。"""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, hash_token
from app.schemas.auth import RefreshRequest, TokenResponse
from app.services import auth as auth_service
from app.services.auth import get_valid_refresh_token, rotate_refresh_token

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.post("", response_model=TokenResponse, summary="登录（签发令牌）")
async def create_token(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """用凭据换取一对 access + refresh 令牌。

    OAuth2 的 ``username`` 表单字段可填**用户名或邮箱**。
    """
    user = await auth_service.authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access, refresh = await auth_service.issue_token_pair(db, user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌（轮换）")
async def rotate_token(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """用有效的 refresh 令牌换取新的一对令牌。

    提交的 refresh 令牌会被作废（轮换），再次使用将返回 401。
    """
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
    access, new_refresh = await rotate_refresh_token(db, token)
    return TokenResponse(access_token=access, refresh_token=new_refresh)

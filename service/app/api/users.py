"""用户资源路由：注册、当前用户。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="注册用户",
)
async def create_user(
    payload: UserCreate, db: AsyncSession = Depends(get_db)
) -> User:
    """注册一个新用户（创建 users 资源）。

    用户名与邮箱均需唯一；密码以 bcrypt 哈希存储。重复注册返回 409。
    """
    return await auth_service.register_user(db, payload)


@router.get("/me", response_model=UserOut, summary="获取当前用户")
async def read_current_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """返回当前已登录用户的信息。

    ``/users/me`` 是「当前用户」的别名；将来若新增 ``/users/{id}``，本路由
    须声明在其之前，以免 ``me`` 被当作 id 捕获。
    """
    return current_user

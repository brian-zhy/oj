"""用户资料管理服务。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserProfileUpdate
from app.core.security import verify_password, hash_password


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """根据用户ID获取用户。

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        用户对象或 None
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_number(db: AsyncSession, user_number: int) -> User | None:
    """根据用户编号获取用户。

    Args:
        db: 数据库会话
        user_number: 用户编号

    Returns:
        用户对象或 None
    """
    result = await db.execute(
        select(User).where(User.user_number == user_number)
    )
    return result.scalar_one_or_none()


async def update_user_profile(
    db: AsyncSession,
    user_id: int,
    payload: UserProfileUpdate
) -> User:
    """更新用户资料。

    Args:
        db: 数据库会话
        user_id: 用户ID
        payload: 更新数据

    Returns:
        更新后的用户对象

    Raises:
        ValueError: 用户不存在或数据无效
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    # 检查用户名是否重复
    if payload.username and payload.username != user.username:
        existing_user = await db.execute(
            select(User).where(User.username == payload.username)
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("用户名已被使用")

    # 更新字段
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


async def update_user_password(
    db: AsyncSession,
    user_id: int,
    old_password: str,
    new_password: str
) -> None:
    """更新用户密码。

    Args:
        db: 数据库会话
        user_id: 用户ID
        old_password: 旧密码
        new_password: 新密码

    Raises:
        ValueError: 用户不存在或旧密码错误
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    # 验证旧密码
    if not verify_password(old_password, user.hashed_password):
        raise ValueError("旧密码错误")

    # 更新密码
    user.hashed_password = hash_password(new_password)
    await db.commit()


async def check_username_available(db: AsyncSession, username: str) -> bool:
    """检查用户名是否可用。

    Args:
        db: 数据库会话
        username: 用户名

    Returns:
        是否可用
    """
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none() is None


async def check_email_available(db: AsyncSession, email: str) -> bool:
    """检查邮箱是否可用。

    Args:
        db: 数据库会话
        email: 邮箱

    Returns:
        是否可用
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none() is None


async def check_phone_available(db: AsyncSession, phone: str) -> bool:
    """检查手机号是否可用。

    Args:
        db: 数据库会话
        phone: 手机号

    Returns:
        是否可用
    """
    result = await db.execute(
        select(User).where(User.phone == phone)
    )
    return result.scalar_one_or_none() is None

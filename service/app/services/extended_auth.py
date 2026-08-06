"""扩展认证服务，支持多种登录方式和验证码。"""

from __future__ import annotations

import random
import string
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User


def generate_captcha() -> tuple[str, str]:
    """生成验证码和对应的图片数据。

    Returns:
        (captcha_text, captcha_image_data): 验证码文本和base64编码的图片数据
    """
    # 生成随机验证码
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
    captcha = ''.join(random.choice(chars) for _ in range(5))

    # 生成简单的图片数据（这里返回验证码文本，实际前端会绘制）
    return captcha.upper(), captcha


def validate_captcha(user_input: str, expected_captcha: str) -> bool:
    """验证验证码。

    Args:
        user_input: 用户输入的验证码
        expected_captcha: 期望的验证码

    Returns:
        bool: 验证是否正确
    """
    return user_input.strip().upper() == expected_captcha.upper()


async def get_email_by_identifier(
    db: AsyncSession,
    identifier: str
) -> str | None:
    """根据标识符获取用户邮箱。

    支持以下标识符类型：
    - 手机号 (1[3-9]\\d{9})
    - 用户编号 (-?\\d{1,6})
    - 邮箱 (包含@)
    - 用户名

    Args:
        db: 数据库会话
        identifier: 用户标识符

    Returns:
        用户的邮箱地址，如果未找到则返回 None
    """
    # 手机号
    if _is_phone(identifier):
        result = await db.execute(
            select(User.email).where(User.phone == identifier)
        )
        return result.scalar_one_or_none()

    # 用户编号
    if _is_user_number(identifier):
        result = await db.execute(
            select(User.email).where(User.user_number == int(identifier))
        )
        return result.scalar_one_or_none()

    # 邮箱
    if '@' in identifier:
        return identifier

    # 用户名
    result = await db.execute(
        select(User.email).where(User.username == identifier)
    )
    return result.scalar_one_or_none()


def _is_phone(value: str) -> bool:
    """检查是否为手机号。"""
    return bool(match := __import__('re').match(r'^1[3-9]\d{9}$', value))


def _is_user_number(value: str) -> bool:
    """检查是否为用户编号。"""
    try:
        num = int(value)
        return -1000000 <= num <= 999999  # 支持6位数编号
    except (ValueError, TypeError):
        return False


async def create_user_with_number(
    db: AsyncSession,
    username: str,
    email: str,
    hashed_password: str,
    phone: str | None = None,
    **extra_fields: Any
) -> User:
    """创建新用户并分配用户编号。

    Args:
        db: 数据库会话
        username: 用户名
        email: 邮箱
        hashed_password: 哈希后的密码
        phone: 手机号（可选）
        **extra_fields: 其他用户字段

    Returns:
        创建的用户对象
    """
    # 获取当前最大用户编号
    result = await db.execute(
        select(User.user_number).order_by(User.user_number.desc()).limit(1)
    )
    max_number = result.scalar_one_or_none() or 1000

    # 创建新用户
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        phone=phone,
        user_number=max_number + 1,
        **extra_fields
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def check_user_banned(db: AsyncSession, user_id: int) -> bool:
    """检查用户是否被封禁。

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        是否被封禁
    """
    result = await db.execute(
        select(User.is_banned).where(User.id == user_id)
    )
    is_banned = result.scalar_one_or_none()
    return bool(is_banned)

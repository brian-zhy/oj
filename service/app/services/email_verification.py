"""邮箱验证码服务。"""

from __future__ import annotations

import hashlib
import random
import string
from datetime import UTC, datetime, timedelta
from typing import Any

# 验证码存储（生产环境应使用Redis）
_verification_codes: dict[str, dict[str, Any]] = {}

# 密码重置令牌存储
_password_reset_tokens: dict[str, dict[str, Any]] = {}


def generate_verification_code(length: int = 6) -> str:
    """生成数字验证码。

    Args:
        length: 验证码长度

    Returns:
        验证码字符串
    """
    return ''.join(random.choices(string.digits, k=length))


def generate_email_token(email: str) -> str:
    """生成邮箱验证令牌。

    Args:
        email: 邮箱地址

    Returns:
        验证令牌
    """
    timestamp = str(datetime.now(UTC).timestamp())
    data = f"{email}:{timestamp}"
    token = hashlib.sha256(data.encode()).hexdigest()[:16]
    return token


def store_verification_code(
    token: str,
    code: str,
    expiry_minutes: int = 10
) -> str:
    """存储验证码。

    Args:
        token: 验证令牌
        code: 验证码
        expiry_minutes: 过期时间（分钟）

    Returns:
        存储的验证码ID
    """
    expiry = datetime.now(UTC) + timedelta(minutes=expiry_minutes)

    verification_data = {
        "code": code,
        "expiry": expiry,
        "attempts": 0,
        "max_attempts": 3
    }

    _verification_codes[token] = verification_data
    return token


def verify_code(token: str, user_code: str) -> bool:
    """验证验证码。

    Args:
        token: 验证令牌
        user_code: 用户输入的验证码

    Returns:
        验证是否成功
    """
    verification_data = _verification_codes.get(token)

    if not verification_data:
        return False

    # 检查是否过期
    if verification_data["expiry"] < datetime.now(UTC):
        del _verification_codes[token]
        return False

    # 检查尝试次数
    if verification_data["attempts"] >= verification_data["max_attempts"]:
        del _verification_codes[token]
        return False

    # 增加尝试次数
    verification_data["attempts"] += 1

    # 验证码匹配
    if verification_data["code"] == user_code:
        # 验证成功，删除验证码
        del _verification_codes[token]
        return True

    return False


def get_verification_data(token: str) -> dict[str, Any] | None:
    """获取验证码数据。

    Args:
        token: 验证令牌

    Returns:
        验证码数据或None
    """
    return _verification_codes.get(token)


def delete_verification_code(token: str) -> None:
    """删除验证码。

    Args:
        token: 验证令牌
    """
    if token in _verification_codes:
        del _verification_codes[token]


def cleanup_expired_codes() -> None:
    """清理过期的验证码。"""
    now = datetime.now(UTC)
    expired_tokens = [
        token for token, data in _verification_codes.items()
        if data["expiry"] < now
    ]

    for token in expired_tokens:
        del _verification_codes[token]


def generate_password_reset_token(email: str) -> str:
    """生成密码重置令牌。

    Args:
        email: 用户邮箱

    Returns:
        重置令牌
    """
    timestamp = str(datetime.now(UTC).timestamp())
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    data = f"{email}:{timestamp}:{random_str}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def store_password_reset_token(
    token: str,
    email: str,
    expiry_minutes: int = 30
) -> str:
    """存储密码重置令牌。

    Args:
        token: 重置令牌
        email: 用户邮箱
        expiry_minutes: 过期时间（分钟）

    Returns:
        存储的令牌
    """
    expiry = datetime.now(UTC) + timedelta(minutes=expiry_minutes)

    reset_data = {
        "email": email,
        "expiry": expiry,
        "used": False
    }

    _password_reset_tokens[token] = reset_data
    return token


def verify_password_reset_token(token: str) -> dict[str, Any] | None:
    """验证密码重置令牌。

    Args:
        token: 重置令牌

    Returns:
        令牌数据（包含email）如果有效，否则返回None
    """
    reset_data = _password_reset_tokens.get(token)

    if not reset_data:
        return None

    # 检查是否过期
    if reset_data["expiry"] < datetime.now(UTC):
        del _password_reset_tokens[token]
        return None

    # 检查是否已使用
    if reset_data["used"]:
        return None

    return reset_data


def mark_password_reset_token_used(token: str) -> None:
    """标记密码重置令牌为已使用。

    Args:
        token: 重置令牌
    """
    if token in _password_reset_tokens:
        _password_reset_tokens[token]["used"] = True


def delete_password_reset_token(token: str) -> None:
    """删除密码重置令牌。

    Args:
        token: 重置令牌
    """
    if token in _password_reset_tokens:
        del _password_reset_tokens[token]


def cleanup_expired_reset_tokens() -> None:
    """清理过期的密码重置令牌。"""
    now = datetime.now(UTC)
    expired_tokens = [
        token for token, data in _password_reset_tokens.items()
        if data["expiry"] < now
    ]

    for token in expired_tokens:
        del _password_reset_tokens[token]

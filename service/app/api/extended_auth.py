"""扩展认证API：支持验证码登录和多种登录方式。"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.schemas.user import UserLogin, UserCreate
from app.schemas.auth import TokenResponse
from app.services import auth as auth_service
from app.services.extended_auth import (
    generate_captcha,
    validate_captcha,
    get_email_by_identifier,
    create_user_with_number,
    check_user_banned
)
from app.core.security import hash_password
from app.deps import get_current_user
from app.models.user import User
from app.services.email_verification import (
    generate_verification_code,
    generate_email_token,
    store_verification_code,
    verify_code,
    delete_verification_code,
    generate_password_reset_token,
    store_password_reset_token,
    verify_password_reset_token,
    mark_password_reset_token_used,
    delete_password_reset_token
)
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["extended-auth"])


# 存储验证码的内存缓存（生产环境应使用 Redis）
_captcha_store: dict[str, dict[str, Any]] = {}


def generate_captcha_id() -> str:
    """生成验证码会话ID。"""
    return hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:16]


@router.get("/email-config-test", summary="测试邮箱配置")
async def test_email_config() -> dict[str, Any]:
    """测试邮箱配置是否正确。

    Returns:
        邮箱配置状态和详细信息
    """
    from app.services.email_service import email_service

    config_info = {
        "configured": email_service.is_configured,
        "smtp_host": email_service.smtp_host if email_service.is_configured else None,
        "smtp_port": email_service.smtp_port if email_service.is_configured else None,
        "smtp_email": email_service.smtp_email if email_service.is_configured else None,
        "from_name": email_service.from_name if email_service.is_configured else None,
        "password_set": bool(email_service.smtp_password) if email_service.is_configured else False,
    }

    return config_info


@router.get("/captcha", summary="生成图形验证码")
async def create_captcha() -> dict[str, str]:
    """生成新的图形验证码。

    Returns:
        包含 captcha_id 和 captcha_text 的字典
    """
    captcha_text, captcha_data = generate_captcha()
    captcha_id = generate_captcha_id()

    # 存储验证码，5分钟后过期
    expiry = datetime.now(UTC) + timedelta(minutes=5)
    _captcha_store[captcha_id] = {
        "text": captcha_text,
        "expiry": expiry
    }

    return {
        "captcha_id": captcha_id,
        "captcha_text": captcha_text  # 前端用于绘制验证码图片
    }


@router.post("/login", response_model=TokenResponse, summary="登录（支持多种标识符）")
async def login_with_identifier(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """使用用户名/UID/手机/邮箱登录。

    Args:
        payload: 登录数据，包含 identifier、password 和 captcha
        db: 数据库会话

    Returns:
        访问令牌和刷新令牌

    Raises:
        HTTPException: 认证失败时
    """
    # 验证验证码
    if not payload.captcha_id or not payload.captcha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供验证码"
        )

    captcha_data = _captcha_store.get(payload.captcha_id)
    if not captcha_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期或无效"
        )

    if captcha_data["expiry"] < datetime.now(UTC):
        # 清理过期验证码
        del _captcha_store[payload.captcha_id]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期"
        )

    if not validate_captcha(payload.captcha, captcha_data["text"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图形验证码错误"
        )

    # 清理已使用的验证码
    del _captcha_store[payload.captcha_id]

    # 根据标识符获取邮箱
    email = await get_email_by_identifier(db, payload.identifier)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    # 验证用户凭据
    user = await auth_service.authenticate_user(db, email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 检查封禁状态
    if await check_user_banned(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员"
        )

    # 签发令牌
    access, refresh = await auth_service.issue_token_pair(db, user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/send-verification", summary="发送邮箱验证码")
async def send_verification_code(request: dict[str, str]) -> dict[str, str]:
    """发送邮箱验证码。

    Args:
        request: 包含email字段的对象

    Returns:
        发送结果和验证令牌
    """
    email = request.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供邮箱地址"
        )

    # 验证邮箱格式
    import re
    email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    if not re.match(email_regex, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式不正确"
        )

    try:
        # 生成验证码和令牌
        code = generate_verification_code(6)
        token = generate_email_token(email)

        # 存储验证码（10分钟有效期）
        stored_token = store_verification_code(token, code, expiry_minutes=10)

        # 发送邮件
        success = await email_service.send_verification_email(email, code, 10)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="发送验证码失败，请稍后重试"
            )

        return {
            "message": "验证码已发送到您的邮箱",
            "token": token,
            "expiry_minutes": "10"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送验证码失败: {str(e)}"
        )


@router.post("/register", response_model=dict, summary="注册新用户")
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """注册新用户（支持邮箱和手机注册）。

    Args:
        payload: 用户注册数据
        db: 数据库会话

    Returns:
        创建的用户信息和令牌

    Raises:
        HTTPException: 注册失败时
    """
    # 确定注册方式：邮箱注册或手机注册
    is_email_register = payload.email is not None
    is_phone_register = payload.phone is not None

    if not is_email_register and not is_phone_register:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供邮箱或手机号进行注册"
        )

    # 验证邮箱注册
    if is_email_register:
        if not payload.email_token or not payload.email_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供邮箱验证码"
            )

        # 验证邮箱验证码
        if not verify_code(payload.email_token, payload.email_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱验证码错误或已过期"
            )

        # 删除已使用的验证码
        delete_verification_code(payload.email_token)

    # 验证手机注册（目前为模拟验证，生产环境需要接入真实短信服务）
    if is_phone_register:
        if not payload.phone_token or not payload.phone_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供手机验证码"
            )

        # TODO: 实现手机验证码验证逻辑
        # 目前简化处理：假设验证码都是"123456"
        if payload.phone_code != "123456":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机验证码错误"
            )

    # 检查用户名是否已存在
    from sqlalchemy import select
    existing_user = await db.execute(
        select(User).where(User.username == payload.username)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    if is_email_register:
        existing_email = await db.execute(
            select(User).where(User.email == payload.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被使用"
            )

    # 检查手机号是否已存在
    if is_phone_register:
        existing_phone = await db.execute(
            select(User).where(User.phone == payload.phone)
        )
        if existing_phone.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="手机号已被使用"
            )

    # 哈希密码
    hashed_pwd = hash_password(payload.password)

    # 创建用户（手机注册时生成虚拟邮箱）
    user_email = payload.email
    if is_phone_register and not user_email:
        # 为手机注册用户生成虚拟邮箱
        user_email = f"phone+{payload.phone}@temp.local"

    # 创建用户
    user = await create_user_with_number(
        db,
        username=payload.username,
        email=user_email,
        hashed_password=hashed_pwd,
        phone=payload.phone
    )

    # 签发令牌
    access, refresh = await auth_service.issue_token_pair(db, user.id)

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_number": user.user_number,
            "phone": user.phone
        },
        "tokens": {
            "access_token": access,
            "refresh_token": refresh
        }
    }


@router.get("/me", summary="获取当前用户详细信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """获取当前登录用户的详细信息。

    Args:
        current_user: 当前用户

    Returns:
        用户详细信息
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "user_number": current_user.user_number,
        "phone": current_user.phone,
        "is_active": current_user.is_active,
        "is_banned": current_user.is_banned,
        "is_admin": current_user.is_admin,
        "is_cheater": current_user.is_cheater,
        "can_speak": current_user.can_speak,
        "can_manage_users": current_user.can_manage_users,
        "can_manage_posts": current_user.can_manage_posts,
        "avatar_url": current_user.avatar_url,
        "user_tag": current_user.user_tag,
        "username_color": current_user.username_color,
        "bio": current_user.bio,
        "created_at": current_user.created_at
    }


@router.post("/password-reset/request", summary="请求密码重置")
async def request_password_reset(
    payload: dict[str, str],
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """请求密码重置，发送重置链接到用户邮箱。

    Args:
        payload: 包含email字段的对象
        db: 数据库会话

    Returns:
        发送结果

    Raises:
        HTTPException: 邮箱不存在或发送失败时
    """
    email = payload.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供邮箱地址"
        )

    # 验证邮箱格式
    import re
    email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    if not re.match(email_regex, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式不正确"
        )

    # 检查邮箱是否存在于数据库中
    from sqlalchemy import select
    existing_user = await db.execute(
        select(User).where(User.email == email)
    )
    user = existing_user.scalar_one_or_none()

    if not user:
        # 为了安全，不透露邮箱是否存在，但返回成功消息
        # 在生产环境中，你可能想要记录这个尝试
        print(f"[Password Reset] 尝试重置不存在的邮箱: {email}")
        return {
            "message": "如果该邮箱已注册，您将收到密码重置链接",
            "expiry_minutes": "30"
        }

    # 生成重置令牌
    token = generate_password_reset_token(email)
    store_password_reset_token(token, email, expiry_minutes=30)

    # 构建重置链接
    # 注意：这里假设前端运行在 http://localhost:5173
    # 生产环境应该从配置文件读取前端URL
    frontend_url = "http://localhost:5173"
    reset_link = f"{frontend_url}/reset-password?token={token}"

    # 发送邮件
    success = await email_service.send_password_reset_email(
        email=email,
        reset_link=reset_link,
        expiry_minutes=30
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送密码重置邮件失败，请稍后重试"
        )

    return {
        "message": "密码重置链接已发送到您的邮箱",
        "expiry_minutes": "30"
    }


@router.post("/password-reset/confirm", summary="确认密码重置")
async def confirm_password_reset(
    payload: dict[str, str],
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """使用重置令牌确认密码重置。

    Args:
        payload: 包含token和new_password字段的对象
        db: 数据库会话

    Returns:
        重置结果

    Raises:
        HTTPException: 令牌无效或重置失败时
    """
    token = payload.get("token")
    new_password = payload.get("new_password")

    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供重置令牌和新密码"
        )

    # 验证密码长度
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为6位"
        )

    # 验证重置令牌
    reset_data = verify_password_reset_token(token)
    if not reset_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效或已过期"
        )

    email = reset_data["email"]

    # 查找用户
    from sqlalchemy import select
    existing_user = await db.execute(
        select(User).where(User.email == email)
    )
    user = existing_user.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 哈希新密码
    hashed_pwd = hash_password(new_password)

    # 更新密码
    user.hashed_password = hashed_pwd
    await db.commit()

    # 标记令牌为已使用
    mark_password_reset_token_used(token)

    print(f"[Password Reset] 用户 {email} 的密码已成功重置")

    return {
        "message": "密码重置成功，请使用新密码登录"
    }


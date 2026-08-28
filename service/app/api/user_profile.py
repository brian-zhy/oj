"""用户资料管理API。"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserProfileUpdate, PasswordUpdate, UserOut
from app.services import user_profile as user_service

router = APIRouter(prefix="/users", tags=["user-profile"])

_ALLOWED_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


@router.get("/me", response_model=UserOut, summary="获取当前用户信息")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前登录用户的详细资料信息。"""
    return current_user


@router.put("/me/profile", response_model=UserOut, summary="更新用户资料")
async def update_user_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """更新当前用户的资料信息。

    Args:
        payload: 更新的用户资料数据
        current_user: 当前用户
        db: 数据库会话

    Returns:
        更新后的用户信息
    """
    try:
        updated_user = await user_service.update_user_profile(
            db, current_user.id, payload
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/me/password", summary="更新用户密码")
async def update_user_password(
    payload: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """更新当前用户的密码。

    Args:
        payload: 包含旧密码和新密码的数据
        current_user: 当前用户
        db: 数据库会话

    Returns:
        成功消息
    """
    try:
        await user_service.update_user_password(
            db, current_user.id, payload.old_password, payload.new_password
        )
        return {"message": "密码更新成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/me/avatar", summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """上传当前用户的头像文件（multipart/form-data，字段名 file）。

    保存到服务端 static/uploads/avatars/，并将 avatar_url 更新为对应路径。
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_AVATAR_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg/jpeg/png/gif/webp 图片",
        )

    content = await file.read()
    if len(content) > _MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片不能超过 5MB",
        )

    upload_dir = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{current_user.user_number}_avatar_{int(time.time() * 1000)}{ext}"
    (upload_dir / filename).write_bytes(content)

    avatar_url = f"/static/uploads/avatars/{filename}"
    current_user.avatar_url = avatar_url
    await db.commit()

    return {"success": True, "avatar_url": avatar_url}


@router.get("/{user_id}", response_model=UserOut, summary="获取指定用户信息")
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> User:
    """根据用户ID获取用户信息。

    Args:
        user_id: 用户ID
        db: 数据库会话

    Returns:
        用户信息
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.get("/number/{user_number}", response_model=UserOut, summary="根据用户编号获取用户信息")
async def get_user_by_number(
    user_number: int,
    db: AsyncSession = Depends(get_db),
) -> User:
    """根据用户编号获取用户信息。

    Args:
        user_number: 用户编号
        db: 数据库会话

    Returns:
        用户信息
    """
    user = await user_service.get_user_by_number(db, user_number)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

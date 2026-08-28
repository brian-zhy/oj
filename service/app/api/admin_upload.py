"""管理员上传接口 —— 用户头像."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/users/{user_number}/avatar")
async def upload_user_avatar(
    user_number: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传指定用户的头像（需要管理员权限）。"""
    if not (current_user.is_admin or current_user.is_super_admin or current_user.can_manage_users):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    result = await db.execute(select(User).where(User.user_number == user_number))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/gif/webp 图片")

    upload_dir = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{user_number}_avatar_{int(time.time() * 1000)}{ext}"
    path = upload_dir / filename
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片不能超过 5MB")
    path.write_bytes(content)

    avatar_url = f"/static/uploads/avatars/{filename}"
    user.avatar_url = avatar_url
    await db.commit()

    return {"success": True, "avatar_url": avatar_url}

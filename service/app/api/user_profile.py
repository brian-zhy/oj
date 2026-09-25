"""用户资料管理API。"""

from __future__ import annotations

import re
import time
from pathlib import Path

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.tag_card import UserTagCard
from app.models.user import User
from app.schemas.user import UserProfileUpdate, PasswordUpdate, UserOut
from app.services import user_profile as user_service

router = APIRouter(prefix="/users", tags=["user-profile"])

_ALLOWED_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

# 主题商店：内置渐变预设（前端按 key 渲染对应 CSS 渐变）
_ALLOWED_THEME_PRESETS = {"dawn", "ocean", "dusk", "sakura"}


async def _require_tag_manager(user: User) -> None:
    # 仅明确授予 Tag 管理权限（或超管）可操作；普通管理员不天然持有
    if not (user.is_super_admin or user.can_manage_tags):
        raise HTTPException(status_code=403, detail="需要 Tag 管理权限")


def _card_dict(card: UserTagCard) -> dict:
    return {
        "id": card.id,
        "name": card.name,
        "enabled": card.enabled,
        "created_at": card.created_at.isoformat() if card.created_at else None,
    }


@router.get("/me/tag-cards", summary="我的 Tag 卡列表")
async def list_my_tag_cards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    cards = (await db.execute(
        select(UserTagCard).where(UserTagCard.user_id == current_user.id)
        .order_by(UserTagCard.id)
    )).scalars().all()
    return {"items": [_card_dict(c) for c in cards]}


@router.put("/me/tag-cards/{card_id}/toggle", summary="佩戴/摘下 Tag 卡（佩戴制：同时仅一张）")
async def toggle_my_tag_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    card = (await db.execute(
        select(UserTagCard).where(
            UserTagCard.id == card_id, UserTagCard.user_id == current_user.id)
    )).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Tag 卡不存在")
    if not card.enabled:
        # 佩戴制：先摘下其他卡
        others = (await db.execute(
            select(UserTagCard).where(
                UserTagCard.user_id == current_user.id,
                UserTagCard.enabled.is_(True))
        )).scalars().all()
        for c in others:
            c.enabled = False
        card.enabled = True
    else:
        card.enabled = False
    await db.commit()
    return _card_dict(card)


@router.post("/{user_id}/tag-cards", status_code=201,
             summary="授予 Tag 卡（需 Tag 管理权限）")
async def grant_tag_card(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await _require_tag_manager(current_user)
    target = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tag 名称不能为空")
    if len(name) > 50:
        raise HTTPException(status_code=400, detail="Tag 名称过长（≤50 字）")
    exists = (await db.execute(
        select(UserTagCard.id).where(
            UserTagCard.user_id == user_id, UserTagCard.name == name)
    )).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="该用户已有同名 Tag 卡")
    card = UserTagCard(user_id=user_id, name=name)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return _card_dict(card)


@router.delete("/{user_id}/tag-cards/{card_id}", status_code=204,
               summary="删除 Tag 卡（需 Tag 管理权限）")
async def delete_tag_card(
    user_id: int,
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await _require_tag_manager(current_user)
    card = (await db.execute(
        select(UserTagCard).where(
            UserTagCard.id == card_id, UserTagCard.user_id == user_id)
    )).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Tag 卡不存在")
    await db.delete(card)
    await db.commit()


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


@router.post("/me/cover", summary="上传个人主页封面")
async def upload_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """上传当前用户的个人主页封面图（multipart/form-data，字段名 file）。"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_AVATAR_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg/jpeg/png/gif/webp 图片",
        )

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片不能超过 8MB",
        )

    upload_dir = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "covers"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{current_user.user_number}_cover_{int(time.time() * 1000)}{ext}"
    (upload_dir / filename).write_bytes(content)

    cover_url = f"/static/uploads/covers/{filename}"
    current_user.cover_url = cover_url
    await db.commit()

    return {"success": True, "cover_url": cover_url}


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


@router.post("/me/theme/background", summary="上传主题背景图")
async def upload_theme_background(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """上传自定义背景图（multipart/form-data，字段名 file），上传后自动启用。

    存到 static/uploads/themes/；图片类型与大小限制与头像一致。
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

    upload_dir = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "themes"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{current_user.user_number}_theme_{int(time.time() * 1000)}{ext}"
    (upload_dir / filename).write_bytes(content)

    # 覆盖旧的自定义图，保留/启用状态由用户后续 PUT 控制
    current_user.theme_background = f"/static/uploads/themes/{filename}"
    current_user.theme_enabled = True
    await db.commit()

    return {
        "success": True,
        "theme_background": current_user.theme_background,
        "theme_enabled": current_user.theme_enabled,
    }


@router.put("/me/theme", summary="设置主题背景（选择/清除/开关）")
async def update_theme(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """更新主题：``background`` 传图片 URL、``preset:xxx``（内置渐变）或
    null（恢复默认）；``enabled`` 控制是否应用。二者均可选。"""
    if "background" in payload:
        bg = payload.get("background")
        if bg is None or bg == "":
            current_user.theme_background = None
            current_user.theme_enabled = False
        elif str(bg).startswith("preset:"):
            preset = str(bg).split(":", 1)[1]
            if preset not in _ALLOWED_THEME_PRESETS:
                raise HTTPException(
                    status_code=400, detail=f"未知主题预设：{preset}"
                )
            current_user.theme_background = str(bg)
            current_user.theme_enabled = True
        elif str(bg).startswith("/static/uploads/themes/"):
            # 仅接受本站上传目录内的路径，防外链/注入
            current_user.theme_background = str(bg)
            current_user.theme_enabled = True
        else:
            raise HTTPException(
                status_code=400, detail="background 需为本站上传路径或 preset:xxx"
            )

    if "enabled" in payload:
        if not isinstance(payload["enabled"], bool):
            raise HTTPException(status_code=400, detail="enabled 需为布尔值")
        if payload["enabled"] and current_user.theme_background is None:
            raise HTTPException(
                status_code=400, detail="还没有可选用的主题背景，请先上传或选择预设"
            )
        current_user.theme_enabled = payload["enabled"]

    await db.commit()
    return {
        "success": True,
        "theme_background": current_user.theme_background,
        "theme_enabled": current_user.theme_enabled,
    }


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


# 用户名规则与外号一致：3-50 位字母、数字或下划线（见 schemas/user.py）
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,50}$")


@router.get("/by-username/{username}", response_model=UserOut, summary="根据用户名获取用户信息")
async def get_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """根据用户名获取用户信息。

    讨论区/犇犇里的 @提及 需要指向用户主页，而主页路由用的是用户编号，
    提到的人只给了用户名，所以补上这个入口，避免前端再发一次批量解析请求。
    """
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    user = await user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

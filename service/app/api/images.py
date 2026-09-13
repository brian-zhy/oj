"""图床接口 —— 上传 / 列表 / 删除 / 锁定 / 配额。

空间规则（参照洛谷）：
  - 「无水印」或「体积超过 IMAGE_PREMIUM_SIZE_THRESHOLD」的图片占用高级空间
  - 其余图片（带水印且不超阈值）占用普通空间
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.deps import get_current_user
from app.models.image import UserImage
from app.models.user import User
from app.schemas.image import ImageItem, ImageListResponse, ImageQuotaResponse
from app.utils.ratelimit import check
from app.utils.watermark import apply_watermark

router = APIRouter(prefix="/images", tags=["images"])

_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
# 水印选项：none = 无水印（占高级空间）；text = 叠加站点文字水印（占普通空间）
_WATERMARK_CHOICES = {"none", "text"}
_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "images"

# 上传频率限制：每用户每分钟最多 20 张，防止刷接口
_UPLOAD_LIMIT = 20
_UPLOAD_WINDOW_SECONDS = 60


async def _used_bytes(db: AsyncSession, user_id: int, premium: bool) -> int:
    """某用户某一类空间已占用的字节数。"""
    total = await db.scalar(
        select(func.coalesce(func.sum(UserImage.size_bytes), 0)).where(
            UserImage.user_id == user_id,
            UserImage.is_premium.is_(premium),
        )
    )
    return int(total or 0)


async def _quota_payload(db: AsyncSession, user_id: int) -> ImageQuotaResponse:
    count = await db.scalar(
        select(func.count()).select_from(UserImage).where(UserImage.user_id == user_id)
    )
    return ImageQuotaResponse(
        total_count=int(count or 0),
        premium_used=await _used_bytes(db, user_id, True),
        premium_quota=settings.IMAGE_PREMIUM_QUOTA_BYTES,
        basic_used=await _used_bytes(db, user_id, False),
        basic_quota=settings.IMAGE_BASIC_QUOTA_BYTES,
        premium_threshold=settings.IMAGE_PREMIUM_SIZE_THRESHOLD,
    )


async def _get_own_image(db: AsyncSession, image_id: int, user: User) -> UserImage:
    """取出属于当前用户的图片，否则 404（不泄露他人图片是否存在）。"""
    image = await db.get(UserImage, image_id)
    if image is None or image.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    return image


@router.post(
    "/upload",
    response_model=ImageItem,
    status_code=status.HTTP_201_CREATED,
    summary="上传图片到图床",
)
async def upload_image(
    file: UploadFile = File(...),
    watermark: str = Form(
        "none",
        description="none = 无水印（占高级空间）；text = 叠加站点文字水印（占普通空间）",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserImage:
    ok, wait = check(f"image:{current_user.id}", _UPLOAD_LIMIT, _UPLOAD_WINDOW_SECONDS)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"上传太频繁，请 {wait} 秒后再试",
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg / jpeg / png / gif / webp 图片",
        )
    if watermark not in _WATERMARK_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="水印参数仅支持 none / text",
        )

    content = await file.read()
    raw_size = len(content)
    if raw_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")
    max_bytes = settings.IMAGE_MAX_FILE_BYTES
    if raw_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"单张图片不能超过 {max_bytes // 1024 // 1024}MB",
        )

    # 先渲染水印再判定配额：水印会改变文件体积，按「最终存下来的字节」算才准。
    # 生成失败（没装 Pillow、找不到字体、动图/超大图等）时退化为无水印。
    if watermark == "text":
        stamped = apply_watermark(content, settings.IMAGE_WATERMARK_TEXT)
        if stamped is None:
            watermark = "none"
        else:
            content = stamped
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"加水印后超过 {max_bytes // 1024 // 1024}MB，请压缩后再试或选择无水印",
                )
    size = len(content)

    is_premium = watermark == "none" or size > settings.IMAGE_PREMIUM_SIZE_THRESHOLD

    used = await _used_bytes(db, current_user.id, is_premium)
    quota = (
        settings.IMAGE_PREMIUM_QUOTA_BYTES if is_premium
        else settings.IMAGE_BASIC_QUOTA_BYTES
    )
    if used + size > quota:
        space = "高级空间" if is_premium else "普通空间"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{space}不足：已用 {used / 1024:.0f}KB，"
                f"本图 {size / 1024:.0f}KB，上限 {quota / 1024 / 1024:.0f}MB"
            ),
        )

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}_{int(time.time() * 1000)}{ext}"
    (_UPLOAD_DIR / filename).write_bytes(content)

    image = UserImage(
        user_id=current_user.id,
        url=f"/static/uploads/images/{filename}",
        original_name=(file.filename or "").strip()[:200] or None,
        size_bytes=size,
        content_type=file.content_type,
        watermark=watermark,
        is_premium=is_premium,
        is_locked=False,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


@router.get("", response_model=ImageListResponse, summary="我的图片列表")
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    premium: bool | None = Query(None, description="只看占用高级空间的图片"),
    locked: bool | None = Query(None, description="只看已锁定的图片"),
    q: str | None = Query(None, max_length=100, description="按原始文件名搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImageListResponse:
    conds = [UserImage.user_id == current_user.id]
    if premium is not None:
        conds.append(UserImage.is_premium.is_(premium))
    if locked is not None:
        conds.append(UserImage.is_locked.is_(locked))
    if q:
        conds.append(UserImage.original_name.ilike(f"%{q}%"))

    total = await db.scalar(select(func.count()).select_from(UserImage).where(*conds))
    rows = (
        await db.execute(
            select(UserImage)
            .where(*conds)
            .order_by(UserImage.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return ImageListResponse(
        items=[ImageItem.model_validate(r) for r in rows],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


@router.get("/quota", response_model=ImageQuotaResponse, summary="空间占用情况")
async def get_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImageQuotaResponse:
    return await _quota_payload(db, current_user.id)


@router.patch("/{image_id}/lock", response_model=ImageItem, summary="切换图片锁定状态")
async def toggle_lock(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserImage:
    image = await _get_own_image(db, image_id, current_user)
    image.is_locked = not image.is_locked
    await db.commit()
    await db.refresh(image)
    return image


@router.delete("/{image_id}", summary="删除图片")
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    image = await _get_own_image(db, image_id, current_user)
    if image.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片已锁定，请先解锁再删除",
        )

    # 先删磁盘文件再删记录；文件可能已被手动清理，忽略失败
    try:
        (_UPLOAD_DIR / Path(image.url).name).unlink(missing_ok=True)
    except OSError:
        pass

    await db.delete(image)
    await db.commit()
    return {"success": True}

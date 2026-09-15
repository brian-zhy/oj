"""首页轮播广告接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.home_ad import HomeAd
from app.models.user import User

router = APIRouter(prefix="/home-ads", tags=["home-ads"])


class HomeAdInput(BaseModel):
    image: str = Field(min_length=1, max_length=500)
    link: str = Field(min_length=1, max_length=500)


@router.get("", summary="获取首页广告列表")
async def list_home_ads(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = await db.execute(
        select(HomeAd)
        .where(HomeAd.is_active.is_(True))
        .order_by(HomeAd.sort_order.asc(), HomeAd.id.asc())
    )
    ads = rows.scalars().all()
    return {
        "ads": [
            {
                "id": ad.id,
                "image": ad.image,
                "link": ad.link,
                "sort_order": ad.sort_order,
            }
            for ad in ads
        ]
    }


@router.put("", summary="管理员更新首页广告列表")
async def upsert_home_ads(
    payload: list[HomeAdInput],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    if len(payload) > 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="最多只能添加 6 个广告")

    normalized = [
        {"image": item.image.strip(), "link": item.link.strip()}
        for item in payload
    ]
    if any(not item["image"] or not item["link"] for item in normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图像与跳转链接都不能为空")

    await db.execute(delete(HomeAd))
    for idx, item in enumerate(normalized):
        ad = HomeAd(
            image=item["image"],
            link=item["link"],
            sort_order=idx,
            is_active=True,
        )
        db.add(ad)

    await db.commit()
    return {"success": True}

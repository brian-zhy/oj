"""犇犇API路由。"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models.benben import Benben
from app.models.user import User
from app.schemas.benben import BenbenCreate, BenbenResponse
from app.services.benben import benben_service

router = APIRouter(prefix="/benben", tags=["benben"])


@router.post("", response_model=BenbenResponse, status_code=status.HTTP_201_CREATED)
async def create_benben(
    payload: BenbenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BenbenResponse:
    """发布新的犇犇动态"""
    try:
        benben = await benben_service.create_benben(
            db=db,
            user_number=current_user.user_number,
            content=payload.content,
            reply_to=payload.reply_to,
            is_admin=current_user.is_admin
        )

        # 获取 reply_to_username
        reply_to_username = None
        if payload.reply_to:
            # 查询被回复的犇犇的用户信息
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            parent_result = await db.execute(
                select(Benben).options(selectinload(Benben.user)).where(Benben.id == payload.reply_to)
            )
            parent_benben = parent_result.scalar_one_or_none()
            if parent_benben and parent_benben.user:
                reply_to_username = parent_benben.user.username

        # 构建响应数据
        response_data = BenbenResponse(
            id=benben.id,
            user_number=benben.user_number,
            username=current_user.username,
            avatar_url=current_user.avatar_url,
            is_admin=current_user.is_admin,
            is_cheater=current_user.is_cheater,
            username_color=current_user.username_color,
            user_tag=current_user.user_tag,
            content=benben.content,
            reply_to=benben.reply_to,
            reply_to_username=reply_to_username,
            created_at=benben.created_at,
            is_owner=True
        )

        return response_data

    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("", response_model=list[BenbenResponse])
async def get_benben_list(
    limit: int = Query(20, ge=1, le=100),
    before_id: Optional[int] = Query(None),
    mode: str = Query("all", pattern="^(all|my)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> list[BenbenResponse]:
    """获取犇犇列表"""
    try:
        benben_list = await benben_service.get_benben_list(
            db=db,
            limit=limit,
            before_id=before_id,
            mode=mode,
            user_number=current_user.user_number if current_user else None
        )

        # 丰富用户信息
        enriched_list = benben_service.enrich_benben_with_user_info(
            benben_list,
            current_user.user_number if current_user else None
        )

        # 为每条犇犇获取 reply_to_username
        reply_to_ids = [item["reply_to"] for item in enriched_list if item["reply_to"]]
        reply_to_usernames = {}
        if reply_to_ids:
            from sqlalchemy import select, distinct
            from sqlalchemy.orm import selectinload

            # 查询所有被回复的犇犇及其用户信息
            parent_result = await db.execute(
                select(Benben)
                .options(selectinload(Benben.user))
                .where(Benben.id.in_(reply_to_ids))
            )
            parent_benbens = parent_result.scalars().all()
            reply_to_usernames = {
                benben.id: benben.user.username if benben.user else None
                for benben in parent_benbens
            }

        # 为每条犇犇添加 reply_to_username
        for item in enriched_list:
            if item["reply_to"]:
                item["reply_to_username"] = reply_to_usernames.get(item["reply_to"])

        return [BenbenResponse(**item) for item in enriched_list]

    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{benben_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_benben(
    benben_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除犇犇动态"""
    try:
        await benben_service.delete_benben(
            db=db,
            benben_id=benben_id,
            user_number=current_user.user_number,
            is_admin=current_user.is_admin
        )
        return None

    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
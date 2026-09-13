"""站内通知 API。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])

# 前端标签页分组。@ 和「被回复」是两回事（被 @ 仅代表提及），所以分开统计
GROUP_TYPES: dict[str, tuple[str, ...]] = {
    "mention": ("mention",),
    "reply": ("reply",),
    "system": ("status", "assign", "team"),
}


def _group_filter(group: str):
    """返回该分组的 SQL 过滤条件；all / 未知分组不过滤。"""
    types = GROUP_TYPES.get(group)
    if not types:
        return None
    return Notification.type.in_(types)


def _notification_dict(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "type": n.type,
        "content": n.content,
        "ticket_id": n.ticket_id,
        "link": n.link,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/unread-count", summary="未读通知数量（顶栏红点）")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    rows = (await db.execute(
        select(Notification.type, sa_func.count())
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .group_by(Notification.type)
    )).all()
    by_type = {t: n for t, n in rows}
    by_group = {
        group: sum(by_type.get(t, 0) for t in types)
        for group, types in GROUP_TYPES.items()
    }
    return {"count": sum(by_type.values()), "by_group": by_group}


@router.get("", summary="通知列表")
async def list_notifications(
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    group: str = Query("all", description="all / mention / reply / system"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    base = select(Notification).where(Notification.user_id == current_user.id)
    condition = _group_filter(group)
    if condition is not None:
        base = base.where(condition)
    total = (
        await db.execute(select(sa_func.count()).select_from(base.subquery()))
    ).scalar() or 0
    result = await db.execute(
        base.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(page * page_size)
        .limit(page_size)
    )
    items = result.scalars().unique().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "group": group,
        "notifications": [_notification_dict(n) for n in items],
    }


@router.put("/read-all", summary="全部标记已读")
async def read_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True}


@router.put("/{notification_id}/read", summary="标记单条已读")
async def read_one(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    n.is_read = True
    await db.commit()
    return {"success": True}

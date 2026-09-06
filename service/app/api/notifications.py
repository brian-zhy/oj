"""站内通知 API。"""

from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.services.ticket import TicketService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _notification_dict(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "type": n.type,
        "content": n.content,
        "ticket_id": n.ticket_id,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/unread-count", summary="未读通知数量（顶栏红点）")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
    )
    return {"count": len(result.all())}


@router.get("", summary="通知列表")
async def list_notifications(
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    base = select(Notification).where(Notification.user_id == current_user.id)
    total = (
        await db.execute(select(_count()).select_from(base.subquery()))
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
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "content": n.content,
                "ticket_id": n.ticket_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


def _count():
    from sqlalchemy import func as sa_func
    return sa_func.count()


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

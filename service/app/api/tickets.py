"""工单系统 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.ticket import TicketReply
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketReplyCreate, TicketStatusUpdate
from app.services.ticket import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _require_staff(user: User) -> None:
    if not TicketService.is_staff_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要用户管理权限")


def _reply_dict(reply: TicketReply) -> dict:
    user = reply.user
    return {
        "id": reply.id,
        "user_id": reply.user_id,
        "content": reply.content,
        "is_staff": reply.is_staff,
        "action_text": reply.action_text or "",
        "created_at": reply.created_at.isoformat() if reply.created_at else None,
        "user": TicketService._user_brief(user),
    }


@router.post("", summary="创建工单")
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """创建工单（一事一单）。封禁用户仅可提交账号申诉。"""
    try:
        ticket = await TicketService.create_ticket(
            db, current_user, payload.title, payload.category, payload.content
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return TicketService._ticket_dict(ticket)


@router.get("/similar", summary="相似工单查询")
async def search_similar_tickets(
    title: str = Query(..., min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """按标题模糊搜索公开工单，减少重复工单创建。"""
    return await TicketService.search_similar(db, title)


@router.get("", summary="工单列表")
async def list_tickets(
    scope: str = Query("my", pattern="^(my|all)$"),
    ticket_status: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """我的工单（scope=my）或全部工单（scope=all，需用户管理权限）。"""
    if scope == "all":
        _require_staff(current_user)
    return await TicketService.list_tickets(
        db,
        scope=scope,
        creator_id=current_user.id,
        status=ticket_status,
        category=category,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticket_id}", summary="工单详情")
async def get_ticket_detail(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    if not TicketService.can_view(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该工单")

    data = TicketService._ticket_dict(ticket)
    # 工单描述 = 创建时的首条内容（独立于回复展示）
    data["description"] = ticket.replies[0].content if ticket.replies else ""
    data["replies"] = [_reply_dict(r) for r in ticket.replies]
    data["can_manage"] = TicketService.is_staff_user(current_user)
    data["is_creator"] = ticket.creator_id == current_user.id
    return data


@router.put("/{ticket_id}/description", summary="编辑工单描述")
async def update_ticket_description(
    ticket_id: int,
    payload: TicketReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """编辑工单描述（仅创建者，工单未完结时）。"""
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    try:
        await TicketService.update_description(db, ticket, current_user, payload.content)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True}


@router.post("/{ticket_id}/replies", summary="回复工单")
async def reply_ticket(
    ticket_id: int,
    payload: TicketReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    try:
        await TicketService.add_reply(db, ticket, current_user, payload.content)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return {"success": True}


@router.put("/{ticket_id}/status", summary="流转工单状态")
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    try:
        ticket = await TicketService.update_status(db, ticket, current_user, payload.status)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "status": ticket.status}

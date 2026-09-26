"""工单系统 API。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.ticket import TicketAttachment, TicketReply
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketReplyCreate, TicketStatusUpdate
from app.services.ticket import TicketService
from app.utils.ratelimit import check

router = APIRouter(prefix="/tickets", tags=["tickets"])

# 附件限制：10MB；扩展名黑名单（拦可执行文件），其余放行
_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
_FORBIDDEN_ATTACHMENT_EXT = {
    ".exe", ".bat", ".cmd", ".sh", ".msi", ".dll", ".so", ".jar", ".apk", ".ps1",
}


def _require_staff(user: User) -> None:
    if not TicketService.is_staff_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要用户管理权限")


def _attachment_dict(att: TicketAttachment) -> dict:
    return {
        "id": att.id,
        "reply_id": att.reply_id,
        "orig_name": att.orig_name,
        "stored_path": att.stored_path,
        "size_bytes": att.size_bytes,
        "uploader_id": att.uploader_id,
    }


def _reply_dict(reply: TicketReply, attachments: Optional[list] = None) -> dict:
    user = reply.user
    return {
        "id": reply.id,
        "user_id": reply.user_id,
        "content": reply.content,
        "is_staff": reply.is_staff,
        "action_text": reply.action_text or "",
        "action_target": TicketService._user_brief(reply.action_target) if reply.action_target_user_id else None,
        "created_at": reply.created_at.isoformat() if reply.created_at else None,
        "user": TicketService._user_brief(user),
        "attachments": attachments or [],
    }


@router.post("", summary="创建工单")
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """创建工单（一事一单）。封禁用户仅可提交账号申诉。"""
    # 10 分钟内最多 3 张
    ok, wait = check(f"ticket:{current_user.user_number}", 3, 600)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"创建太频繁，请 {wait} 秒后再试",
        )

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
    """工单列表。

    scope=my  → 我的工单
    scope=all → 全部工单（所有登录用户可见公开类；管理员额外可见账号申诉等私密工单）
    """
    include_private = TicketService.is_staff_user(current_user)
    return await TicketService.list_tickets(
        db,
        scope=scope,
        creator_id=current_user.id,
        status=ticket_status,
        category=category,
        page=page,
        page_size=page_size,
        include_private=include_private,
    )


@router.get("/staff", summary="可指派的管理员列表")
async def list_staff(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    _require_staff(current_user)
    return await TicketService.list_staff(db)


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
    # 附件：一次性查出，按 reply 分组（描述附件 = 首条回复的附件）
    att_rows = (await db.execute(
        select(TicketAttachment)
        .where(TicketAttachment.ticket_id == ticket.id)
        .order_by(TicketAttachment.id)
    )).scalars().all()
    by_reply: dict[int, list] = {}
    for a in att_rows:
        by_reply.setdefault(a.reply_id, []).append(_attachment_dict(a))
    data["description_attachments"] = by_reply.get(ticket.replies[0].id, []) if ticket.replies else []
    data["replies"] = [{**_reply_dict(r), "attachments": by_reply.get(r.id, [])} for r in ticket.replies]
    data["can_manage"] = TicketService.is_staff_user(current_user)
    data["is_creator"] = ticket.creator_id == current_user.id
    return data


class TicketTitleUpdate(BaseModel):
    title: str


@router.put("/{ticket_id}/title", summary="修改工单标题")
async def update_ticket_title(
    ticket_id: int,
    payload: TicketTitleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """修改工单标题（创建者或管理员；工单完结后仅管理员可改）。"""
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    try:
        await TicketService.update_title(db, ticket, current_user, payload.title)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "title": ticket.title}


@router.post("/{ticket_id}/attachments", summary="上传工单附件")
async def upload_ticket_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    reply_id: Optional[int] = Query(None, description="挂到指定回复；缺省挂到工单描述"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """上传附件（multipart，字段名 file）。创建者或管理员可传，工单未完结。

    reply_id 缺省时自动挂到工单描述（首条回复）。
    """
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")

    orig_name = file.filename or "附件"
    ext = Path(orig_name).suffix.lower()
    if ext in _FORBIDDEN_ATTACHMENT_EXT:
        raise HTTPException(status_code=400, detail=f"不允许上传 {ext} 类型的文件")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > _MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=400, detail="附件不能超过 10MB")

    upload_dir = Path(__file__).resolve().parent.parent.parent / "static" / "uploads" / "tickets" / str(ticket_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / stored_name).write_bytes(content)
    stored_path = f"/static/uploads/tickets/{ticket_id}/{stored_name}"

    try:
        att = await TicketService.add_attachment(
            db, ticket, current_user, reply_id,
            orig_name=orig_name, stored_path=stored_path, size_bytes=len(content),
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "attachment": _attachment_dict(att)}


@router.delete("/{ticket_id}/attachments/{attachment_id}", summary="删除工单附件")
async def delete_ticket_attachment(
    ticket_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """删除附件（上传者本人或管理员）。"""
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")
    try:
        path = await TicketService.delete_attachment(db, ticket, current_user, attachment_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    # 磁盘文件一并清理（相对路径映射到 static 目录）
    disk = Path(__file__).resolve().parent.parent.parent / path.lstrip("/").removeprefix("static/")
    try:
        disk.unlink(missing_ok=True)
    except OSError:
        pass
    return {"success": True}


@router.put("/{ticket_id}/description", summary="编辑工单描述")


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
        reply = await TicketService.add_reply(db, ticket, current_user, payload.content)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    # reply_id 供前端挂附件
    return {"success": True, "reply_id": reply.id}


class TicketAssignPayload(BaseModel):
    assignee_id: Optional[int] = None


@router.put("/{ticket_id}/assign", summary="指派责任人")
async def assign_ticket(
    ticket_id: int,
    payload: TicketAssignPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket or ticket.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工单不存在")

    assignee: Optional[User] = None
    if payload.assignee_id is not None:
        result = await db.execute(
            select(User).where(User.id == payload.assignee_id)
        )
        assignee = result.scalar_one_or_none()
        if not assignee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="被指派的管理员不存在")

    try:
        await TicketService.assign(db, ticket, current_user, assignee)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return TicketService._ticket_dict(ticket)


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

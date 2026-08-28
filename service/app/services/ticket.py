"""工单业务逻辑（参照洛谷工单设计适配本站）。

规则要点：
- 一事一单：标题须明确具体（由前端引导，后端做长度与重复提示）。
- 类别权限：封禁用户仅可提交「账号申诉」；未封禁用户不可提交申诉。
- 公开可见：综合类工单默认公开（登录用户可见），申诉私密（仅创建者与管理员）。
- 状态流转：管理员回复 → 待补充；用户回复 → 待处理；管理员可挂起/处理中/完成/关闭/删除。
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketReply
from app.models.user import User
from app.schemas.ticket import TICKET_STATUSES

VALID_STATUSES = set(TICKET_STATUSES.keys())

OPEN_STATUSES = {"pending", "replied", "processing", "suspended"}


class TicketService:
    """工单服务"""

    @staticmethod
    async def create_ticket(
        db: AsyncSession,
        creator: User,
        title: str,
        category: str,
        content: str,
    ) -> Ticket:
        """创建工单。

        规则：
        - 封禁用户仅可提交「账号申诉」（appeal）
        - 未封禁用户不可提交「账号申诉」
        """
        if creator.is_banned and category != "appeal":
            raise PermissionError("被封禁的用户仅可提交「账号申诉」工单")
        if not creator.is_banned and category == "appeal":
            raise PermissionError("账号申诉工单仅封禁用户可提交")

        is_public = category != "appeal"

        ticket = Ticket(
            title=title.strip(),
            category=category,
            status="pending",
            creator_id=creator.id,
            is_public=is_public,
        )
        db.add(ticket)
        await db.flush()

        reply = TicketReply(
            ticket_id=ticket.id,
            user_id=creator.id,
            content=content.strip(),
            is_staff=False,
        )
        db.add(reply)
        ticket.last_reply_at = reply.created_at
        ticket.last_reply_by = "user"

        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    def _user_brief(user: User | None) -> dict[str, Any]:
        if user is None:
            return {
                "user_id": None,
                "username": "已删除用户",
                "user_tag": "",
                "is_admin": False,
                "is_banned": False,
                "user_number": None,
                "avatar_url": "",
            }
        return {
            "user_id": user.id,
            "username": user.username,
            "user_tag": user.user_tag or "",
            "is_admin": bool(user.is_admin),
            "is_banned": bool(user.is_banned),
            "user_number": user.user_number,
            "avatar_url": user.avatar_url or "",
        }

    @staticmethod
    def _ticket_dict(ticket: Ticket) -> dict[str, Any]:
        return {
            "id": ticket.id,
            "ticket_no": f"#{1000 + ticket.id}",
            "title": ticket.title,
            "category": ticket.category,
            "status": ticket.status,
            "creator_id": ticket.creator_id,
            "is_public": ticket.is_public,
            "last_reply_at": ticket.last_reply_at.isoformat() if ticket.last_reply_at else None,
            "last_reply_by": ticket.last_reply_by,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "creator": TicketService._user_brief(ticket.creator),
        }

    @staticmethod
    async def list_tickets(
        db: AsyncSession,
        *,
        scope: str = "my",
        creator_id: Optional[int] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """工单列表。

        scope=my   → 只看自己的
        scope=all  → 全部（删除态不可见，需管理员权限，由 API 层校验）
        """
        query = select(Ticket).options(selectinload(Ticket.creator))

        if scope == "my" and creator_id is not None:
            query = query.where(Ticket.creator_id == creator_id)
        else:
            query = query.where(Ticket.status != "deleted")

        if status:
            query = query.where(Ticket.status == status)
        if category:
            query = query.where(Ticket.category == category)

        total_result = await db.execute(
            select(sa_func.count()).select_from(query.subquery())
        )
        total = total_result.scalar() or 0

        result = await db.execute(
            query.order_by(
                Ticket.last_reply_at.desc().nullslast(), Ticket.id.desc()
            )
            .offset(page * page_size)
            .limit(page_size)
        )
        tickets = result.scalars().unique().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "tickets": [TicketService._ticket_dict(t) for t in tickets],
        }

    @staticmethod
    async def search_similar(
        db: AsyncSession,
        title: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """按标题模糊搜索公开工单（相似工单查询）。"""
        keyword = (title or "").strip()
        if len(keyword) < 2:
            return []
        result = await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.creator))
            .where(
                Ticket.is_public.is_(True),
                Ticket.status != "deleted",
                Ticket.title.ilike(f"%{keyword}%"),
            )
            .order_by(Ticket.id.desc())
            .limit(limit)
        )
        return [TicketService._ticket_dict(t) for t in result.scalars().unique().all()]

    @staticmethod
    async def get_ticket(db: AsyncSession, ticket_id: int) -> Optional[Ticket]:
        result = await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.creator), selectinload(Ticket.replies).selectinload(TicketReply.user))
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def can_view(ticket: Ticket, user: Optional[User]) -> bool:
        """可见性：创建者 / 管理员 / 公开工单的任意登录用户。"""
        if user is None:
            return False
        if ticket.creator_id == user.id:
            return True
        if user.can_manage_users or user.is_admin or user.is_super_admin:
            return True
        return bool(ticket.is_public) and ticket.status != "deleted"

    @staticmethod
    def is_staff_user(user: User) -> bool:
        return bool(user.can_manage_users or user.is_admin or user.is_super_admin)

    @staticmethod
    async def add_reply(
        db: AsyncSession,
        ticket: Ticket,
        user: User,
        content: str,
    ) -> TicketReply:
        """追加回复。

        - 工单处于终态（resolved/closed/deleted）时仅管理员可回复
        - 管理员回复 → 状态改为 replied（待用户补充）；用户回复 → pending（待处理）
        """
        is_staff = TicketService.is_staff_user(user)
        is_creator = ticket.creator_id == user.id

        if not is_staff and not is_creator:
            raise PermissionError("只能回复自己的工单")
        if not is_staff and ticket.status not in OPEN_STATUSES:
            raise PermissionError("工单已完结，如仍有问题请新建工单")

        reply = TicketReply(
            ticket_id=ticket.id,
            user_id=user.id,
            content=content.strip(),
            is_staff=is_staff,
        )
        db.add(reply)
        ticket.last_reply_at = reply.created_at
        ticket.last_reply_by = "staff" if is_staff else "user"
        if ticket.status in OPEN_STATUSES or is_staff:
            ticket.status = "replied" if is_staff else "pending"

        await db.commit()
        await db.refresh(reply)
        return reply

    @staticmethod
    async def update_status(
        db: AsyncSession,
        ticket: Ticket,
        user: User,
        new_status: str,
    ) -> Ticket:
        """管理员流转状态；创建者仅可关闭自己的工单。"""
        if new_status not in VALID_STATUSES:
            raise ValueError("无效的状态")

        if TicketService.is_staff_user(user):
            ticket.status = new_status
        elif ticket.creator_id == user.id:
            if new_status != "closed":
                raise PermissionError("创建者仅可关闭自己的工单")
            if ticket.status not in OPEN_STATUSES:
                raise PermissionError("工单已完结")
            ticket.status = "closed"
        else:
            raise PermissionError("无权限操作该工单")

        await db.commit()
        await db.refresh(ticket)
        return ticket

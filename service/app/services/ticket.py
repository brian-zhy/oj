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
            creator_username=creator.username,
            creator_tag=creator.user_tag or '',
        )
        db.add(ticket)
        await db.flush()

        reply = TicketReply(
            ticket_id=ticket.id,
            user_id=creator.id,
            content=content.strip(),
            is_staff=False,
            user_username=creator.username,
            user_tag=creator.user_tag or '',
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
    def _identity(brief: dict[str, Any], username_snap: Optional[str], tag_snap: Optional[str]) -> dict[str, Any]:
        """展示身份：有快照用快照（历史记录不随改名漂移），否则用当前身份。"""
        if username_snap:
            brief = dict(brief)
            brief['username'] = username_snap
            brief['user_tag'] = tag_snap or ''
        return brief

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
            "creator": TicketService._identity(
                TicketService._user_brief(ticket.creator), ticket.creator_username, ticket.creator_tag
            ),
            "assignee": TicketService._user_brief(ticket.assignee) if ticket.assignee_id else None,
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
        include_private: bool = True,
    ) -> dict[str, Any]:
        """工单列表。

        scope=my   → 只看自己的
        scope=all  → 全部公开工单（删除态不可见）；
                     include_private=True（管理员）时额外可见账号申诉等私密工单
        """
        query = select(Ticket).options(selectinload(Ticket.creator))

        if scope == "my" and creator_id is not None:
            query = query.where(Ticket.creator_id == creator_id)
        else:
            query = query.where(Ticket.status != "deleted")
            if not include_private:
                query = query.where(Ticket.is_public.is_(True))

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
            .options(
                selectinload(Ticket.creator),
                selectinload(Ticket.assignee),
                selectinload(Ticket.replies).selectinload(TicketReply.user),
                selectinload(Ticket.replies).selectinload(TicketReply.action_target),
            )
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
            user_username=user.username,
            user_tag=user.user_tag or '',
        )
        db.add(reply)
        ticket.last_reply_at = reply.created_at
        ticket.last_reply_by = "staff" if is_staff else "user"
        # 状态流转规则：
        # - 管理员回复：仅当工单处于「待处理」时流转为「待补充」，其他状态保持不变
        # - 用户回复：开放状态下流转回「待处理」
        if is_staff:
            if ticket.status == "pending":
                ticket.status = "replied"
        elif is_creator and ticket.status in OPEN_STATUSES:
            ticket.status = "pending"

        await db.commit()
        await db.refresh(reply)
        return reply

    @staticmethod
    async def update_description(
        db: AsyncSession,
        ticket: Ticket,
        user: User,
        content: str,
    ) -> None:
        """编辑工单描述（即创建时的首条内容，仅创建者、工单未完结时可改）。"""
        if ticket.creator_id != user.id:
            raise PermissionError("只有创建者可以编辑工单描述")
        if ticket.status not in OPEN_STATUSES:
            raise PermissionError("工单已完结，描述不可修改")
        if not ticket.replies:
            raise ValueError("工单缺少描述")

        ticket.replies[0].content = content.strip()
        await db.commit()

    @staticmethod
    async def assign(
        db: AsyncSession,
        ticket: Ticket,
        operator: User,
        assignee: Optional[User],
    ) -> None:
        """指派/更改/取消责任人（仅管理员）。

        - assignee 为 None 表示取消指派
        - 被指派人必须具备用户管理权限
        - 留下时间线记录
        """
        if not TicketService.is_staff_user(operator):
            raise PermissionError("需要用户管理权限")
        if assignee is not None and not TicketService.is_staff_user(assignee):
            raise PermissionError("责任人必须是具备用户管理权限的管理员")

        ticket.assignee_id = assignee.id if assignee else None

        action = (
            f"将责任人指派为 {assignee.username}" if assignee
            else "取消了责任人"
        )
        db.add(TicketReply(
            ticket_id=ticket.id,
            user_id=operator.id,
            content="",
            is_staff=True,
            action_text=action,
            action_target_user_id=assignee.id if assignee else None,
        ))
        await db.commit()
        await db.refresh(ticket)

    @staticmethod
    async def list_staff(db: AsyncSession) -> list[dict[str, Any]]:
        """可被指派为责任人的管理员列表。"""
        result = await db.execute(
            select(User).where(
                (User.can_manage_users.is_(True))
                | (User.is_admin.is_(True))
                | (User.is_super_admin.is_(True))
            ).order_by(User.id)
        )
        return [TicketService._user_brief(u) for u in result.scalars().all()]

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

        # 留下状态变更记录（存纯状态名，前端渲染为「某某 将工单状态设置为 已完成」）
        action = TICKET_STATUSES.get(new_status, new_status)
        db.add(TicketReply(
            ticket_id=ticket.id,
            user_id=user.id,
            content="",
            is_staff=True,
            action_text=action,
        ))

        await db.commit()
        await db.refresh(ticket)
        return ticket

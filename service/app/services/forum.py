"""讨论区业务逻辑。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.forum import ForumComment, ForumPost
from app.models.user import User

VALID_FORUMS = ("siteaffairs", "problem", "academics", "relevantaffairs")
FORUM_NAMES = {
    "siteaffairs": "站务版",
    "problem": "题目总版",
    "academics": "学术版",
    "relevantaffairs": "灌水区",
}


class ForumService:
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
    def _post_dict(post: ForumPost, reply_count: int = 0) -> dict[str, Any]:
        return {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "forum": post.forum,
            "forum_name": FORUM_NAMES.get(post.forum, post.forum),
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "author": ForumService._user_brief(post.author),
            "reply_count": reply_count,
        }

    @staticmethod
    def _comment_dict(comment: ForumComment) -> dict[str, Any]:
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "author": ForumService._user_brief(comment.author),
        }

    @staticmethod
    async def list_posts(
        db: AsyncSession,
        *,
        forum: Optional[str] = None,
        page: int = 0,
        page_size: int = 30,
    ) -> dict[str, Any]:
        """帖子列表（倒序分页，附带回复数与作者信息）。"""
        query = select(ForumPost).options(selectinload(ForumPost.author))
        if forum and forum != "all":
            query = query.where(ForumPost.forum == forum)

        count_q = select(sa_func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        result = await db.execute(
            query.order_by(ForumPost.created_at.desc(), ForumPost.id.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        posts = result.scalars().unique().all()

        # 批量统计回复数
        counts: dict[int, int] = {}
        if posts:
            ids = [p.id for p in posts]
            rows = await db.execute(
                select(ForumComment.post_id, sa_func.count())
                .where(ForumComment.post_id.in_(ids))
                .group_by(ForumComment.post_id)
            )
            counts = {pid: n for pid, n in rows.all()}

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "posts": [ForumService._post_dict(p, counts.get(p.id, 0)) for p in posts],
        }

    @staticmethod
    async def recent_posts(db: AsyncSession, limit: int = 10) -> list[dict[str, Any]]:
        """主页「近期讨论」。"""
        data = await ForumService.list_posts(db, page=0, page_size=limit)
        return data["posts"]

    @staticmethod
    async def get_post(db: AsyncSession, post_id: int) -> Optional[ForumPost]:
        result = await db.execute(
            select(ForumPost)
            .options(selectinload(ForumPost.author), selectinload(ForumPost.comments).selectinload(ForumComment.author))
            .where(ForumPost.id == post_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_post(db: AsyncSession, author: User, title: str, content: str, forum: str) -> ForumPost:
        if forum not in VALID_FORUMS:
            raise ValueError("无效的版块")
        post = ForumPost(
            title=title.strip(),
            content=content.strip(),
            forum=forum,
            author_id=author.id,
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        return post

    @staticmethod
    async def add_comment(db: AsyncSession, post: ForumPost, author: User, content: str) -> ForumComment:
        comment = ForumComment(
            post_id=post.id,
            author_id=author.id,
            content=content.strip(),
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def delete_post(db: AsyncSession, post: ForumPost, operator: User) -> None:
        """作者本人或具备帖子管理权限者可删除。"""
        if post.author_id != operator.id and not (
            operator.can_manage_posts or operator.is_admin or operator.is_super_admin
        ):
            raise PermissionError("无权删除该帖子")
        await db.delete(post)
        await db.commit()

    @staticmethod
    async def can_manage(user: Optional[User]) -> bool:
        return bool(user and (user.can_manage_posts or user.is_admin or user.is_super_admin))

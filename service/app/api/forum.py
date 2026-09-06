"""讨论区 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models.forum import ForumPost
from app.models.user import User
from app.services.forum import ForumService
from app.utils.ratelimit import check

router = APIRouter(prefix="/forum", tags=["forum"])


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    content: str = Field(min_length=1, max_length=20000)
    forum: str = Field(pattern="^(siteaffairs|problem|academics|relevantaffairs)$")


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class PostModeratePayload(BaseModel):
    is_pinned: Optional[bool] = None
    is_locked: Optional[bool] = None


class PostUpdatePayload(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    content: str = Field(min_length=1, max_length=20000)


@router.get("/recent", summary="近期讨论（主页）")
async def recent_posts(
    limit: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await ForumService.recent_posts(db, limit=limit)


@router.get("/posts", summary="帖子列表")
async def list_posts(
    forum: Optional[str] = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await ForumService.list_posts(db, forum=forum, page=page, page_size=page_size)


@router.get("/posts/{post_id}", summary="帖子详情")
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    post = await ForumService.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")

    data = ForumService._post_dict(post, reply_count=len(post.comments))
    data["comments"] = [ForumService._comment_dict(c) for c in post.comments]
    data["can_manage"] = await ForumService.can_manage(current_user)
    data["is_author"] = bool(current_user and post.author_id == current_user.id)
    return data


@router.put("/posts/{post_id}/moderate", summary="置顶/锁定帖子（仅秩序管理）")
async def moderate_post(
    post_id: int,
    payload: PostModeratePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """设置帖子的置顶/锁定状态（字段可选，传什么改什么）。"""
    post = await ForumService.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    if not await ForumService.can_manage(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要秩序管理权限")

    if payload.is_pinned is not None:
        post.is_pinned = payload.is_pinned
    if payload.is_locked is not None:
        post.is_locked = payload.is_locked
    await db.commit()
    await db.refresh(post)
    return {"success": True, "is_pinned": post.is_pinned, "is_locked": post.is_locked}


@router.post("/posts", summary="发布帖子", status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if current_user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你已被封禁，无法发帖")
    if not current_user.can_speak:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你已被禁言，无法发帖")
    # 站务版为公告性质版块：仅秩序管理（或管理员）可发帖，普通用户只读
    if payload.forum == "siteaffairs" and not (
        current_user.can_manage_posts or current_user.is_admin or current_user.is_super_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="站务版仅秩序管理可发帖",
        )
    ok, wait = check(f"post:{current_user.user_number}", 1, 60)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发布太频繁，请 {wait} 秒后再试",
        )
    post = await ForumService.create_post(
        db, current_user, payload.title, payload.content, payload.forum
    )
    return ForumService._post_dict(post, 0)


@router.put("/posts/{post_id}", summary="编辑已发布帖子（仅秩序管理）")
async def update_post(
    post_id: int,
    payload: PostUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    post = await ForumService.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    if not await ForumService.can_manage(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要秩序管理权限")

    post = await ForumService.update_post(db, post, payload.title, payload.content)
    return ForumService._post_dict(post, reply_count=len(post.comments))


@router.post("/posts/{post_id}/comments", summary="回复帖子", status_code=status.HTTP_201_CREATED)
async def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    post = await ForumService.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    if current_user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你已被封禁，无法回复")
    if not current_user.can_speak:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你已被禁言，无法回复")
    if post.is_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="帖子已锁定，无法回复")
    ok, wait = check(f"comment:{current_user.user_number}", 1, 5)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"回复太频繁，请 {wait} 秒后再试",
        )
    comment = await ForumService.add_comment(db, post, current_user, payload.content)
    return ForumService._comment_dict(comment)


@router.delete("/posts/{post_id}", summary="删除帖子")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    post = await ForumService.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    try:
        await ForumService.delete_post(db, post, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return {"success": True}

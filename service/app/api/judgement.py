"""陶片放逐 API —— 管理操作日志的公开展示页."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user_optional
from app.models.judgement import JudgementLog
from app.models.user import User

router = APIRouter(prefix="/judgement", tags=["judgement"])


def _user_brief(user: User | None) -> Dict[str, Any]:
    """用户简要信息（与参考项目 fetchUsers 查询的字段一致）."""
    if user is None:
        return {
            "id": None,
            "username": "已删除",
            "avatar_url": "",
            "user_tag": "",
            "is_admin": False,
            "is_banned": False,
            "user_number": None,
            "username_color": "",
            "is_cheater": False,
            "can_manage_posts": False,
        }
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url or "",
        "user_tag": user.user_tag or "",
        "is_admin": bool(user.is_admin),
        "is_banned": bool(user.is_banned),
        "user_number": user.user_number,
        "username_color": user.username_color or "",
        "is_cheater": bool(user.is_cheater),
        "can_manage_posts": bool(user.can_manage_posts),
    }


def _log_dict(log: JudgementLog) -> Dict[str, Any]:
    return {
        "id": log.id,
        "admin_id": log.admin_id,
        "target_user_id": log.target_user_id,
        "action_type": log.action_type,
        "action_detail": log.action_detail or {},
        "reason": log.reason or "",
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "admin": _user_brief(log.admin),
        "target_user": _user_brief(log.target_user),
    }


@router.get("/logs")
async def get_judgement_logs(
    page: int = Query(0, ge=0),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """分页获取陶片放逐日志（按时间倒序）。登录即可浏览。"""
    result = await db.execute(
        select(JudgementLog)
        .order_by(JudgementLog.created_at.desc(), JudgementLog.id.desc())
        .offset(page * page_size)
        .limit(page_size + 1)  # 多取一条判断 has_more
    )
    logs = result.scalars().unique().all()

    has_more = len(logs) > page_size
    logs = logs[:page_size]

    return {
        "logs": [_log_dict(log) for log in logs],
        "has_more": has_more,
        "page": page,
        # 是否可删除陶片（需要秩序管理权限）
        "can_manage": bool(current_user is not None and current_user.can_manage_posts),
    }


@router.delete("/logs/{log_id}")
async def delete_judgement_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """删除单条陶片（需要秩序管理权限 can_manage_posts）。"""
    if current_user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if not current_user.can_manage_posts:
        raise HTTPException(status_code=403, detail="需要秩序管理权限")

    result = await db.execute(select(JudgementLog).where(JudgementLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    await db.delete(log)
    await db.commit()
    return {"success": True}

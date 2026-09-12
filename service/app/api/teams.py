"""团队 API：列表 / 详情 / 创建 / 加入 / 退出 / 解散 / 成员管理。

设计参照 Jason227 站的团队功能适配本站：
- owner 记录在 teams.owner_id，不在 team_members（渲染时以 role='owner' 拼入）
- 团队管理员（role='admin'）可管理成员（改备注/设管理员/移除）；解散仅 owner
- 加入自由，退出自由（owner 不可退出，只能解散）
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models.notification import Notification
from app.models.team import Team, TeamMember, TeamJoinRequest
from app.models.user import User

router = APIRouter(prefix="/teams", tags=["teams"])

MAX_TEAMS_PER_USER = 10   # 每人可创建的团队数上限（防刷）
MAX_MEMBERS_PER_TEAM = 200


def _user_brief(user: User | None) -> dict[str, Any]:
    """成员卡片所需的全站统一用户信息（配色判定字段齐全）。"""
    if user is None:
        return {
            "user_id": None, "username": "已删除用户", "user_tag": "",
            "is_admin": False, "is_super_admin": False, "is_banned": False,
            "is_cheater": False, "can_manage_users": False,
            "can_manage_posts": False, "can_manage_problems": False,
            "user_number": None, "avatar_url": "",
        }
    return {
        "user_id": user.id,
        "username": user.username,
        "user_tag": user.user_tag or "",
        "is_admin": bool(user.is_admin),
        "is_super_admin": bool(user.is_super_admin),
        "is_banned": bool(user.is_banned),
        "is_cheater": bool(user.is_cheater),
        "can_manage_users": bool(user.can_manage_users),
        "can_manage_posts": bool(user.can_manage_posts),
        "can_manage_problems": bool(user.can_manage_problems),
        "user_number": user.user_number,
        "avatar_url": user.avatar_url or "",
    }


def _member_dict(member: TeamMember) -> dict[str, Any]:
    return {
        "user_id": member.user_id,
        "role": member.role,
        "note": member.note or "",
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        "user": _user_brief(member.user),
    }


def _team_dict(team: Team, member_count: int, current_user: User | None) -> dict[str, Any]:
    d = {
        "id": team.id,
        "name": team.name,
        "description": team.description or "",
        "owner": _user_brief(team.owner),
        "owner_id": team.owner_id,
        "member_count": member_count,
        "created_at": team.created_at.isoformat() if team.created_at else None,
    }
    if current_user is not None:
        d["is_owner"] = team.owner_id == current_user.id
        d["is_member"] = d["is_owner"] or any(
            m.user_id == current_user.id for m in team.members
        )
        d["is_team_admin"] = d["is_owner"] or any(
            m.user_id == current_user.id and m.role == "admin"
            for m in team.members
        )
    else:
        d.update({"is_owner": False, "is_member": False, "is_team_admin": False})
    return d


async def _load_team(db: AsyncSession, team_id: int) -> Optional[Team]:
    return (await db.execute(
        select(Team).where(Team.id == team_id)
    )).scalar_one_or_none()


async def _member_count(db: AsyncSession, team_id: int) -> int:
    return (await db.execute(
        select(sa_func.count()).select_from(TeamMember)
        .where(TeamMember.team_id == team_id)
    )).scalar() or 0


async def _require_team_manage(
    db: AsyncSession, team: Team, user: User
) -> None:
    """校验当前用户可管理该团队（owner 或团队管理员）。"""
    if team.owner_id == user.id:
        return
    self_row = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user.id,
            TeamMember.role == "admin",
        )
    )).scalar_one_or_none()
    if self_row is None:
        raise HTTPException(status_code=403, detail="需要团队管理权限")


def _notify(
    db: AsyncSession, user_id: int, content: str, actor_id: int | None = None
) -> None:
    """发一条站内通知（type=team，进顶栏铃铛）。"""
    db.add(Notification(user_id=user_id, type="team", content=content,
                        actor_id=actor_id))


@router.get("", summary="团队列表")
async def list_teams(
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    total = (await db.execute(
        select(sa_func.count()).select_from(Team)
    )).scalar() or 0
    teams = (await db.execute(
        select(Team).order_by(Team.id.desc())
        .offset(page * page_size).limit(page_size)
    )).scalars().all()
    # 人数 = team_members 行数 + owner（owner 不在成员表，需手动计入）
    items = [
        _team_dict(t, await _member_count(db, t.id) + 1, current_user) for t in teams
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201, summary="创建团队")
async def create_team(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip() or None
    if not name:
        raise HTTPException(status_code=400, detail="团队名称不能为空")
    if len(name) > 50:
        raise HTTPException(status_code=400, detail="团队名称过长（≤50 字）")
    if description and len(description) > 500:
        raise HTTPException(status_code=400, detail="团队简介过长（≤500 字）")

    my_count = (await db.execute(
        select(sa_func.count()).select_from(Team)
        .where(Team.owner_id == current_user.id)
    )).scalar() or 0
    if my_count >= MAX_TEAMS_PER_USER:
        raise HTTPException(status_code=400, detail=f"每人最多创建 {MAX_TEAMS_PER_USER} 个团队")

    team = Team(name=name, description=description, owner_id=current_user.id)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    # 创建者即首位成员（owner 不在成员表，人数按 1 计）
    return _team_dict(team, 1, current_user)


@router.get("/{team_id}", summary="团队详情")
async def team_detail(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    members = (await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id)
        .order_by(TeamMember.id)
    )).scalars().all()
    # 人数 = 成员行数 + owner（与下方 members 列表拼入 owner 保持一致）
    d = _team_dict(team, len(members) + 1, current_user)
    # 成员列表：owner 拼在最前（role='owner'），其余按加入顺序
    d["members"] = [{
        "user_id": team.owner_id,
        "role": "owner",
        "note": "",
        "joined_at": d["created_at"],
        "user": d["owner"],
    }] + [_member_dict(m) for m in members]
    # 加入申请：待审核数量（管理员侧徽标）与当前用户的申请状态
    pending_rows = (await db.execute(
        select(TeamJoinRequest).where(TeamJoinRequest.team_id == team_id)
        .order_by(TeamJoinRequest.id)
    )).scalars().all()
    d["pending_count"] = len(pending_rows)
    d["is_pending"] = current_user is not None and any(
        r.user_id == current_user.id for r in pending_rows
    )
    return d


@router.post("/{team_id}/join", summary="申请加入团队（需管理员审核）")
async def join_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    if team.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="你是团队主，无需加入")
    exists = (await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id, TeamMember.user_id == current_user.id)
    )).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="你已经是团队成员")
    count = await _member_count(db, team_id)
    if count + 1 > MAX_MEMBERS_PER_TEAM:
        raise HTTPException(status_code=400, detail=f"团队成员已达上限（{MAX_MEMBERS_PER_TEAM} 人）")
    # 加入需审核：已有待审申请则不重复提交
    pending = (await db.execute(
        select(TeamJoinRequest.id).where(
            TeamJoinRequest.team_id == team_id,
            TeamJoinRequest.user_id == current_user.id)
    )).scalar_one_or_none()
    if pending is not None:
        raise HTTPException(status_code=400, detail="已提交申请，等待审核中")
    db.add(TeamJoinRequest(team_id=team_id, user_id=current_user.id))

    # 通知团队主与所有团队管理员
    content = (f"{current_user.username} 申请加入团队「{team.name}」，"
               f"请前往团队页审核")
    admins = (await db.execute(
        select(TeamMember.user_id).where(
            TeamMember.team_id == team_id, TeamMember.role == "admin")
    )).scalars().all()
    _notify(db, team.owner_id, content, actor_id=current_user.id)
    for admin_id in admins:
        _notify(db, admin_id, content, actor_id=current_user.id)
    await db.commit()
    return {"pending": True}


@router.post("/{team_id}/leave", summary="退出团队")
async def leave_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    if team.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="团队主不能退出，如需退出请先解散团队")
    row = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.user_id == current_user.id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=400, detail="你还不是团队成员")
    await db.delete(row)
    await db.commit()
    return {"success": True}


@router.delete("/{team_id}", summary="解散团队")
async def dissolve_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅团队主可以解散团队")
    await db.delete(team)
    await db.commit()
    return {"success": True}


@router.get("/{team_id}/requests", summary="待审核申请列表（团队管理员）")
async def list_requests(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    await _require_team_manage(db, team, current_user)
    rows = (await db.execute(
        select(TeamJoinRequest).where(TeamJoinRequest.team_id == team_id)
        .order_by(TeamJoinRequest.id)
    )).scalars().all()
    return {
        "items": [{
            "user_id": r.user_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "user": _user_brief(r.user),
        } for r in rows]
    }


@router.post("/{team_id}/requests/{user_id}/approve", summary="通过加入申请")
async def approve_request(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    await _require_team_manage(db, team, current_user)
    req = (await db.execute(
        select(TeamJoinRequest).where(
            TeamJoinRequest.team_id == team_id, TeamJoinRequest.user_id == user_id)
    )).scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="该申请不存在或已处理")
    count = await _member_count(db, team_id)
    if count + 1 > MAX_MEMBERS_PER_TEAM:
        raise HTTPException(status_code=400, detail=f"团队成员已达上限（{MAX_MEMBERS_PER_TEAM} 人）")
    db.add(TeamMember(team_id=team_id, user_id=user_id))
    await db.delete(req)
    _notify(db, user_id,
            f"你申请加入团队「{team.name}」已通过，欢迎加入！",
            actor_id=current_user.id)
    await db.commit()
    return {"success": True}


@router.post("/{team_id}/requests/{user_id}/reject", summary="拒绝加入申请")
async def reject_request(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    await _require_team_manage(db, team, current_user)
    req = (await db.execute(
        select(TeamJoinRequest).where(
            TeamJoinRequest.team_id == team_id, TeamJoinRequest.user_id == user_id)
    )).scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="该申请不存在或已处理")
    await db.delete(req)
    _notify(db, user_id,
            f"你申请加入团队「{team.name}」未通过",
            actor_id=current_user.id)
    await db.commit()
    return {"success": True}


@router.put("/{team_id}/members/{user_id}", summary="管理成员（备注 / 设或撤管理员）")
async def update_member(
    team_id: int,
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    await _require_team_manage(db, team, current_user)

    member = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="该用户不是团队成员")

    new_role = payload.get("role")
    if new_role is not None:
        # 设/撤团队管理员是团主专属权限（管理员只能改备注、踢人）
        if team.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="仅团队主可以设置团队管理员")
        if new_role not in ("member", "admin"):
            raise HTTPException(status_code=400, detail="无效的角色")
        member.role = new_role
    if "note" in payload and payload["note"] is not None:
        note = payload["note"].strip()
        if len(note) > 50:
            raise HTTPException(status_code=400, detail="备注名过长（≤50 字）")
        member.note = note or None
    await db.commit()
    return _member_dict(member)


@router.delete("/{team_id}/members/{user_id}", summary="移除成员")
async def remove_member(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    team = await _load_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="团队不存在")
    await _require_team_manage(db, team, current_user)
    member = (await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="该用户不是团队成员")
    await db.delete(member)
    await db.commit()
    return {"success": True}

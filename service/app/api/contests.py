"""比赛 API（ACM 赛制 MVP）。

- 状态：pending 未开始 / running 进行中 / ended 已结束（按当前时间判定）
- 报名：未开始或进行中均可报名；已结束不可
- 提交：进行中且已报名才计成绩（走 submissions 的 contest_id 挂钩）
- 排名：ACM 规则——通过题数 desc → 罚时 asc（每题首次 AC 分钟数
  + 该题错误提交次数 × 20）
- 创建/删除：题目管理权限或站内管理员
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models.contest import Contest, ContestParticipant, ContestProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User

router = APIRouter(prefix="/contests", tags=["contests"])

ALIAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # 比赛题别名


def _can_manage_contest(user: User) -> bool:
    return bool(user.is_super_admin or user.is_admin or user.can_manage_problems)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """SQLite 读回 naive datetime，统一按 UTC 处理（Postgres 返回 aware）。"""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _status(contest: Contest) -> str:
    now = _utcnow()
    if now < _aware(contest.start_time):
        return "pending"
    if now > _aware(contest.end_time):
        return "ended"
    return "running"


def _contest_dict(
    contest: Contest, current_user: User | None, *,
    with_problems: bool = False, show_hidden_problems: bool = False,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": contest.id,
        "title": contest.title,
        "description": contest.description or "",
        "start_time": contest.start_time.isoformat() if contest.start_time else None,
        "end_time": contest.end_time.isoformat() if contest.end_time else None,
        "status": _status(contest),
        "owner": {
            "user_id": contest.owner_id,
            "username": contest.owner.username if contest.owner else "未知",
        },
        "participant_count": len(contest.participants),
        "problem_count": len(contest.problems),
        "is_owner": bool(current_user and contest.owner_id == current_user.id),
        "can_manage": bool(current_user and _can_manage_contest(current_user)),
    }
    if current_user:
        d["is_participant"] = any(
            p.user_id == current_user.id for p in contest.participants
        )
    else:
        d["is_participant"] = False
    if with_problems:
        hide_titles = _status(contest) == "pending" and not show_hidden_problems
        problems = []
        for cp in contest.problems:
            problems.append({
                "alias": ALIAS[cp.sort_order] if cp.sort_order < len(ALIAS) else str(cp.sort_order),
                "problem_id": cp.problem_id,
                "sort_order": cp.sort_order,
                # 未开始时不暴露题目标题（防提前审题）
                "title": "※" if hide_titles else cp.problem.title,
                "difficulty": cp.problem.difficulty,
                "problem_number": cp.problem.problem_number,
            })
        d["problems"] = problems
    return d


async def _load_contest(db: AsyncSession, contest_id: int) -> Optional[Contest]:
    return (await db.execute(
        select(Contest).where(Contest.id == contest_id)
    )).scalar_one_or_none()


def _parse_time(value: Any) -> datetime:
    try:
        t = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="时间格式不正确")
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t


@router.get("", summary="比赛列表")
async def list_contests(
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    total = (await db.execute(
        select(sa_func.count()).select_from(Contest)
    )).scalar() or 0
    contests = (await db.execute(
        select(Contest).order_by(Contest.start_time.desc())
        .offset(page * page_size).limit(page_size)
    )).scalars().unique().all()
    items = [_contest_dict(c, current_user) for c in contests]
    # 分区排序：进行中 → 未开始 → 已结束
    order = {"running": 0, "pending": 1, "ended": 2}
    items.sort(key=lambda x: (order[x["status"]], x["start_time"] or ""))
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201, summary="创建比赛（题目管理权限/站内管理员）")
async def create_contest(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not _can_manage_contest(current_user):
        raise HTTPException(status_code=403, detail="需要比赛管理权限")

    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="比赛名称不能为空")
    start_time = _parse_time(payload.get("start_time"))
    end_time = _parse_time(payload.get("end_time"))
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

    problem_ids = [p for p in (payload.get("problem_ids") or []) if isinstance(p, int)]
    seen: set[int] = set()
    unique_ids = [p for p in problem_ids if not (p in seen or seen.add(p))]
    if unique_ids:
        found = set((await db.execute(
            select(Problem.id).where(Problem.id.in_(unique_ids))
        )).scalars().all())
        missing = [p for p in unique_ids if p not in found]
        if missing:
            raise HTTPException(status_code=400, detail=f"题目不存在: {missing}")

    contest = Contest(
        title=title,
        description=(payload.get("description") or "").strip() or None,
        start_time=start_time, end_time=end_time,
        owner_id=current_user.id,
    )
    db.add(contest)
    await db.flush()
    for order, pid in enumerate(unique_ids):
        db.add(ContestProblem(contest_id=contest.id, problem_id=pid, sort_order=order))
    await db.commit()
    await db.refresh(contest)
    return _contest_dict(contest, current_user, with_problems=True,
                         show_hidden_problems=True)


@router.get("/{contest_id}", summary="比赛详情")
async def contest_detail(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    contest = await _load_contest(db, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    show_hidden = bool(current_user and _can_manage_contest(current_user))
    return _contest_dict(contest, current_user,
                         with_problems=True, show_hidden_problems=show_hidden)


@router.delete("/{contest_id}", summary="删除比赛（创建者或站内管理员）")
async def delete_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    contest = await _load_contest(db, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    if contest.owner_id != current_user.id and not _can_manage_contest(current_user):
        raise HTTPException(status_code=403, detail="无权删除该比赛")
    await db.delete(contest)
    await db.commit()
    return {"success": True}


@router.post("/{contest_id}/register", summary="报名比赛")
async def register_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    contest = await _load_contest(db, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    if _status(contest) == "ended":
        raise HTTPException(status_code=400, detail="比赛已结束，无法报名")
    exists = (await db.execute(
        select(ContestParticipant.id).where(
            ContestParticipant.contest_id == contest_id,
            ContestParticipant.user_id == current_user.id)
    )).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="你已报名该比赛")
    db.add(ContestParticipant(contest_id=contest_id, user_id=current_user.id))
    await db.commit()
    return {"success": True}


@router.get("/{contest_id}/rank", summary="比赛排名（ACM 赛制）")
async def contest_rank(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    contest = await _load_contest(db, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="比赛不存在")

    cps = (await db.execute(
        select(ContestProblem).where(ContestProblem.contest_id == contest_id)
        .order_by(ContestProblem.sort_order)
    )).scalars().all()
    alias_by_pid = {
        cp.problem_id: (ALIAS[cp.sort_order] if cp.sort_order < len(ALIAS) else str(cp.sort_order))
        for cp in cps
    }
    participants = (await db.execute(
        select(ContestParticipant).where(ContestParticipant.contest_id == contest_id)
        .options(selectinload(ContestParticipant.user))
    )).scalars().unique().all()

    subs = (await db.execute(
        select(Submission).where(
            Submission.contest_id == contest_id,
            Submission.status.in_(["accepted", "wrong_answer", "runtime_error",
                                   "time_limit_exceeded", "memory_limit_exceeded"]),
        )
    )).scalars().all()

    start = _aware(contest.start_time)
    # per (user, problem)：错误次数 / 首次 AC 的分钟数
    stat: dict[tuple[int, int], dict[str, Any]] = {}
    for sub in subs:
        key = (sub.user_id, sub.problem_id)
        if key not in stat:
            stat[key] = {"tries": 0, "ac_minutes": None}
        if sub.status == "accepted":
            if sub.created_at and stat[key]["ac_minutes"] is None:
                minutes = max(0, int((_aware(sub.created_at) - start).total_seconds() // 60))
                stat[key]["ac_minutes"] = minutes
        else:
            stat[key]["tries"] += 1

    rows = []
    for p in participants:
        solved_count, total_penalty = 0, 0
        detail: dict[str, Any] = {}
        for cp in cps:
            alias = alias_by_pid.get(cp.problem_id, "?")
            s = stat.get((p.user_id, cp.problem_id))
            if s is None:
                detail[alias] = {"tries": 0, "solved": False}
                continue
            if s["ac_minutes"] is not None:
                solved_count += 1
                p_ = 20 * s["tries"] + s["ac_minutes"]
                total_penalty += p_
                detail[alias] = {"tries": s["tries"], "solved": True,
                                 "minutes": s["ac_minutes"], "penalty": p_}
            else:
                detail[alias] = {"tries": s["tries"], "solved": False}
        rows.append({
            "user": {
                "user_id": p.user_id,
                "username": p.user.username if p.user else "未知",
                "avatar_url": (p.user.avatar_url or "") if p.user else "",
                "user_tag": (p.user.user_tag or "") if p.user else "",
                "is_admin": bool(p.user.is_admin) if p.user else False,
                "is_super_admin": bool(p.user.is_super_admin) if p.user else False,
                "is_cheater": bool(p.user.is_cheater) if p.user else False,
                "can_manage_users": bool(p.user.can_manage_users) if p.user else False,
                "can_manage_posts": bool(p.user.can_manage_posts) if p.user else False,
                "can_manage_problems": bool(p.user.can_manage_problems) if p.user else False,
                "user_number": p.user.user_number if p.user else None,
            },
            "solved": solved_count,
            "penalty": total_penalty,
            "detail": detail,
        })
    rows.sort(key=lambda r: (-r["solved"], r["penalty"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return {
        "aliases": [alias_by_pid.get(cp.problem_id, "?") for cp in cps],
        "rows": rows,
    }

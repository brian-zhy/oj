"""评测提交 API（提交 / 记录 / 详情 / 测试点管理）。"""

from __future__ import annotations

from typing import Optional

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.deps import get_current_user
from app.models.contest import Contest, ContestParticipant, ContestProblem
from app.models.problem import Problem
from app.models.submission import Submission, TestCase
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.submission import SubmissionCreate, TestCaseCreate
from app.services.judge import judge_submission
from app.utils.ratelimit import check

router = APIRouter(tags=["submissions"])


def _can_manage(user: User) -> bool:
    return bool(user.can_manage_problems)


def _require_problem_manage(user: User) -> None:
    if not _can_manage(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要题目管理权限"
        )


async def _is_team_admin(db: AsyncSession, team_id: int, user: User) -> bool:
    """当前用户是否为该团队的团主/团队管理员。"""
    if user.is_super_admin:
        return True
    is_owner = (await db.execute(
        select(Team.id).where(Team.id == team_id, Team.owner_id == user.id)
    )).scalar_one_or_none()
    if is_owner is not None:
        return True
    return (await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
            TeamMember.role == "admin",
        )
    )).scalar_one_or_none() is not None


async def _require_team_member_for_problem(
    db: AsyncSession, problem: Problem, user: User
) -> None:
    """团队私有题仅团队成员可见/可提交，非成员按不存在处理。"""
    if problem.team_id is None or _can_manage(user):
        return
    if await _is_team_admin(db, problem.team_id, user):
        return
    row = (await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == problem.team_id,
            TeamMember.user_id == user.id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )


async def _require_manage_for_problem(
    db: AsyncSession, problem: Problem, user: User
) -> None:
    """题目管理权：主题库题要题目管理权限；团队题团队管理员亦可。

    非团队成员按不存在处理（404 防探测）；成员但非管理员 403。
    """
    if problem.team_id is None:
        _require_problem_manage(user)
        return
    if _can_manage(user):
        return
    if await _is_team_admin(db, problem.team_id, user):
        return
    member = (await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == problem.team_id,
            TeamMember.user_id == user.id)
    )).scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="需要团队管理权限"
    )


def _is_staff(user: User) -> bool:
    return bool(user.can_manage_users or user.is_admin or user.is_super_admin)


def _user_brief(user: User | None) -> dict:
    if user is None:
        return {
            "user_id": None,
            "username": "已删除用户",
            "user_number": None,
            "avatar_url": "",
            "is_admin": False,
        }
    return {
        "user_id": user.id,
        "username": user.username,
        "user_number": user.user_number,
        "avatar_url": user.avatar_url or "",
        "is_admin": bool(user.is_admin),
    }


def _dict(
    sub: Submission,
    *,
    problem: Optional[Problem] = None,
    with_code: bool = False,
) -> dict:
    d = {
        "id": sub.id,
        "problem_id": sub.problem_id,
        "problem_number": f"P{1000 + sub.problem_id}",
        "problem_title": problem.title if problem else None,
        "user": _user_brief(sub.user),
        "language": sub.language,
        "status": sub.status,
        "score": sub.score,
        "time_used": sub.time_used,
        "memory_used": sub.memory_used,
        "error_message": sub.error_message,
        "test_results": sub.test_results or [],
        "judged_at": sub.judged_at.isoformat() if sub.judged_at else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }
    if with_code:
        d["code"] = sub.code
    return d


async def _load_submission(db: AsyncSession, submission_id: int) -> Optional[Submission]:
    result = await db.execute(
        select(Submission).options(selectinload(Submission.user)).where(
            Submission.id == submission_id)
    )
    return result.scalar_one_or_none()


async def _load_problem(db: AsyncSession, problem_id: int) -> Optional[Problem]:
    return (await db.execute(
        select(Problem).where(Problem.id == problem_id)
    )).scalar_one_or_none()


@router.post("/problems/{problem_id}/submissions", summary="提交代码")
async def create_submission(
    problem_id: int,
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    problem = await _load_problem(db, problem_id)
    if problem is None or (
        not problem.is_public and not _can_manage(current_user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    # 团队私有题仅成员可提交
    await _require_team_member_for_problem(db, problem, current_user)

    # 比赛内提交：进行中 + 已报名 + 题目属于该比赛
    contest_id = payload.contest_id
    if contest_id is not None:
        contest = (await db.execute(
            select(Contest).where(Contest.id == contest_id)
        )).scalar_one_or_none()
        if contest is None:
            raise HTTPException(status_code=404, detail="比赛不存在")
        now = datetime.now(timezone.utc)
        st_ = contest.start_time
        en = contest.end_time
        # SQLite 读回 naive datetime，统一按 UTC 处理
        if st_.tzinfo is None:
            st_ = st_.replace(tzinfo=timezone.utc)
        if en.tzinfo is None:
            en = en.replace(tzinfo=timezone.utc)
        if now < st_:
            raise HTTPException(status_code=400, detail="比赛尚未开始")
        if now > en:
            raise HTTPException(status_code=400, detail="比赛已结束，不计成绩")
        participant = (await db.execute(
            select(ContestParticipant.id).where(
                ContestParticipant.contest_id == contest_id,
                ContestParticipant.user_id == current_user.id)
        )).scalar_one_or_none()
        if participant is None:
            raise HTTPException(status_code=403, detail="请先报名比赛再提交")
        in_contest = (await db.execute(
            select(ContestProblem.id).where(
                ContestProblem.contest_id == contest_id,
                ContestProblem.problem_id == problem_id)
        )).scalar_one_or_none()
        if in_contest is None:
            raise HTTPException(status_code=400, detail="该题目不属于这场比赛")

    if current_user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="被封禁用户不能提交评测"
        )

    case_count = (await db.execute(
        select(sa_func.count()).select_from(TestCase).where(
            TestCase.problem_id == problem_id)
    )).scalar() or 0
    if case_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该题目暂无测试数据，无法提交评测",
        )

    # 5 分钟内最多 6 次提交
    ok, wait = check(f"submit:{current_user.user_number}", 6, 300)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"提交太频繁，请 {wait} 秒后再试",
        )

    sub = Submission(
        problem_id=problem_id,
        user_id=current_user.id,
        code=payload.code,
        language=payload.language,
        status="pending",
        contest_id=contest_id,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # 响应返回后后台评测
    background_tasks.add_task(judge_submission, sub.id)
    return _dict(sub, problem=problem, with_code=True)


@router.get("/problems/{problem_id}/submissions", summary="题目的提交记录")
async def list_problem_submissions(
    problem_id: int,
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    base = select(Submission).options(selectinload(Submission.user)).where(
        Submission.problem_id == problem_id)
    total = (await db.execute(
        select(sa_func.count()).select_from(base.subquery())
    )).scalar() or 0
    rows = (await db.execute(
        base.offset(page * page_size).limit(page_size)
        .order_by(Submission.id.desc())
    )).scalars().all()

    problem = await _load_problem(db, problem_id)
    staff = _is_staff(current_user)
    items = []
    for sub in rows:
        d = _dict(sub, problem=problem)
        d["code_visible"] = staff or sub.user_id == current_user.id
        if d["code_visible"]:
            d["code"] = sub.code
        items.append(d)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get(
    "/problems/{problem_id}/my-last-submission",
    summary="我在该题的最后一次提交（含代码）",
)
async def get_my_last_submission(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[dict]:
    """提交页回填用：返回当前用户在该题最近一次提交（含 code）。

    从未提交过时返回 ``null``（前端据此显示默认代码模板）。
    """
    problem = await _load_problem(db, problem_id)
    if problem is None or (
        not problem.is_public and not _can_manage(current_user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    # 团队私有题仅成员可见/可提交
    await _require_team_member_for_problem(db, problem, current_user)

    sub = (await db.execute(
        select(Submission)
        .where(
            Submission.problem_id == problem_id,
            Submission.user_id == current_user.id,
        )
        .order_by(Submission.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if sub is None:
        return None
    return _dict(sub, problem=problem, with_code=True)


@router.get("/submissions/mine", summary="我的提交记录")
async def list_my_submissions(
    problem_id: Optional[int] = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    base = select(Submission).options(selectinload(Submission.user)).where(
        Submission.user_id == current_user.id)
    if problem_id:
        base = base.where(Submission.problem_id == problem_id)
    total = (await db.execute(
        select(sa_func.count()).select_from(base.subquery())
    )).scalar() or 0
    rows = (await db.execute(
        base.offset(page * page_size).limit(page_size)
        .order_by(Submission.id.desc())
    )).scalars().all()

    items = []
    for sub in rows:
        problem = await _load_problem(db, sub.problem_id)
        items.append(_dict(sub, problem=problem, with_code=False))
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/submissions/{submission_id}", summary="提交详情")
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    sub = await _load_submission(db, submission_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交不存在")
    problem = await _load_problem(db, sub.problem_id)
    if problem is None or (
        not problem.is_public and not _can_manage(current_user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交不存在")

    code_visible = sub.user_id == current_user.id or _is_staff(current_user)
    d = _dict(sub, problem=problem, with_code=code_visible)
    d["code_visible"] = code_visible
    return d


# ==================== 测试点管理（题目管理权限） ====================

@router.get("/problems/{problem_id}/test-cases", summary="测试点列表")
async def list_test_cases(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    problem = await _load_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    await _require_manage_for_problem(db, problem, current_user)
    rows = (await db.execute(
        select(TestCase).where(TestCase.problem_id == problem_id)
        .order_by(TestCase.sort_order.asc(), TestCase.id.asc())
    )).scalars().all()
    return [
        {
            "id": tc.id,
            "input_data": tc.input_data,
            "expected_output": tc.expected_output,
            "sort_order": tc.sort_order,
        }
        for tc in rows
    ]


@router.post("/problems/{problem_id}/test-cases", summary="新增测试点")
async def create_test_case(
    problem_id: int,
    payload: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    problem = await _load_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    await _require_manage_for_problem(db, problem, current_user)
    count = (await db.execute(
        select(sa_func.count()).select_from(TestCase).where(
            TestCase.problem_id == problem_id)
    )).scalar() or 0
    if count >= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="测试点最多 100 个"
        )
    tc = TestCase(
        problem_id=problem_id,
        input_data=payload.input_data,
        expected_output=payload.expected_output,
        sort_order=count,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return {
        "id": tc.id,
        "input_data": tc.input_data,
        "expected_output": tc.expected_output,
        "sort_order": tc.sort_order,
    }


@router.delete("/problems/{problem_id}/test-cases/{case_id}", summary="删除测试点")
async def delete_test_case(
    problem_id: int,
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    problem = await _load_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    await _require_manage_for_problem(db, problem, current_user)
    tc = (await db.execute(
        select(TestCase).where(
            TestCase.id == case_id, TestCase.problem_id == problem_id)
    )).scalar_one_or_none()
    if tc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测试点不存在")
    await db.delete(tc)
    await db.commit()
    return {"success": True}

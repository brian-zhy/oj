"""评测提交 API（提交 / 记录 / 详情 / 测试点管理）。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.deps import get_current_user
from app.models.problem import Problem
from app.models.submission import Submission, TestCase
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
    _require_problem_manage(current_user)
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
    _require_problem_manage(current_user)
    problem = await _load_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
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
    _require_problem_manage(current_user)
    tc = (await db.execute(
        select(TestCase).where(
            TestCase.id == case_id, TestCase.problem_id == problem_id)
    )).scalar_one_or_none()
    if tc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测试点不存在")
    await db.delete(tc)
    await db.commit()
    return {"success": True}

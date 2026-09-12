"""题库 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.problem import Problem
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.problem import ProblemCreate, ProblemUpdate
from app.services.judge import adjust_experience_on_difficulty_change
from app.services.problem import ProblemService
from sqlalchemy import func as sa_func, select

router = APIRouter(prefix="/problems", tags=["problems"])


def _can_manage_problems(user: User) -> bool:
    # 严格只认题目管理权限（is_admin / is_super_admin 不放行）
    return bool(user.can_manage_problems)


def _require_problem_manage(user: User) -> None:
    if not _can_manage_problems(user):
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
    row = (await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
            TeamMember.role == "admin",
        )
    )).scalar_one_or_none()
    return row is not None


async def _is_team_member(db: AsyncSession, team_id: int, user: User) -> bool:
    """当前用户是否可见该团队私有题（成员 / 团队管理员 / 题目管理权限）。"""
    if _can_manage_problems(user) or user.is_super_admin:
        return True
    return await _is_team_admin(db, team_id, user) or bool((await db.execute(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )).scalar_one_or_none())


async def _resolve_team_problem_access(
    db: AsyncSession, problem: Problem, user: User
) -> None:
    """团队私有题的可见性：非团队成员按不存在处理（404 防探测）。"""
    if problem.team_id is None:
        return
    if await _is_team_member(db, problem.team_id, user):
        return
    # 区分 404（非成员）/403（成员但被下架等），当前仅成员可见
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
    )


@router.get("", summary="题目列表")
async def list_problems(
    difficulty: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, max_length=100),
    all: bool = Query(False, description="含未公开题目（需题目管理权限）"),
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """题库列表，支持难度 / 来源 / 标签 / 关键词筛选。"""
    include_private = False
    if all:
        _require_problem_manage(current_user)
        include_private = True
    return await ProblemService.list_problems(
        db,
        difficulty=difficulty,
        source=source,
        tag=tag,
        keyword=keyword,
        include_private=include_private,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get("/sources", summary="来源列表")
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    """去重后的题目来源（筛选下拉用）。"""
    return await ProblemService.list_sources(db)


@router.get("/by-code/{code}", summary="按题号访问题目（P1001 / T10）")
async def get_problem_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """统一题目入口：主题库 P{n}（id = n-1000），团队题 T{n}（全局 T 序号）。"""
    code = code.strip().upper()
    problem: Problem | None
    if code.startswith("T") and code[1:].isdigit():
        problem = (await db.execute(
            select(Problem).where(Problem.t_no == int(code[1:]))
        )).scalar_one_or_none()
    elif code.startswith("P") and code[1:].isdigit():
        problem = await ProblemService.get_by_id(db, int(code[1:]) - 1000)
    else:
        problem = None
    if problem is None or (
        problem.team_id is None
        and not problem.is_public
        and not _can_manage_problems(current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    await _resolve_team_problem_access(db, problem, current_user)
    return ProblemService._dict(problem, with_description=True)


@router.get("/{problem_id}", summary="题目详情")
async def get_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    problem = await ProblemService.get_by_id(db, problem_id)
    # 未公开题目 / 非本人团队私有题对无权限者按不存在处理（404，避免泄露存在性）
    if problem is None or (
        problem.team_id is None
        and not problem.is_public
        and not _can_manage_problems(current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    await _resolve_team_problem_access(db, problem, current_user)
    return ProblemService._dict(problem, with_description=True)


@router.post("", summary="创建题目")
async def create_problem(
    payload: ProblemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = payload.model_dump(exclude_unset=True)
    team_id = data.pop("team_id", None)
    if team_id is not None:
        # 团队私有题：团队管理员即可创建（无需题目管理权限），编号走全局 T 序列
        if not await _is_team_admin(db, team_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要团队管理权限",
            )
        data["team_id"] = team_id
        data.setdefault("is_public", False)
        data["author_id"] = current_user.id
        # T 编号跨团队全局递增：max+1，并发撞号由 unique 约束兜底后重试
        from sqlalchemy.exc import IntegrityError
        problem = None
        for _ in range(3):
            max_no = (await db.execute(
                select(sa_func.max(Problem.t_no))
            )).scalar() or 0
            data["t_no"] = max_no + 1
            try:
                problem = await ProblemService.create(db, data)
                break
            except IntegrityError:
                await db.rollback()
        if problem is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建失败（编号冲突），请重试",
            )
        return ProblemService._dict(problem, with_description=True)
    _require_problem_manage(current_user)
    data["author_id"] = current_user.id
    problem = await ProblemService.create(db, data)
    return ProblemService._dict(problem, with_description=True)


@router.put("/{problem_id}", summary="更新题目")
async def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    problem = await ProblemService.get_by_id(db, problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    # 主题库题要题目管理权限；团队私有题团队管理员即可编辑
    # （非成员按不存在处理 404；成员但非管理员 403）
    if problem.team_id is None:
        _require_problem_manage(current_user)
    elif not _can_manage_problems(current_user):
        if await _is_team_admin(db, problem.team_id, current_user):
            pass
        elif not await _is_team_member(db, problem.team_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="需要团队管理权限"
            )
    old_difficulty = problem.difficulty
    problem = await ProblemService.update(
        db, problem, payload.model_dump(exclude_unset=True)
    )
    # 难度变更：重算所有首次 AC 该题用户的经验（delta 增减）
    if (payload.difficulty is not None
            and payload.difficulty != old_difficulty):
        await adjust_experience_on_difficulty_change(
            db, problem.id, old_difficulty, payload.difficulty
        )
    return ProblemService._dict(problem, with_description=True)


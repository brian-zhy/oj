"""题库 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.problem import ProblemCreate, ProblemUpdate
from app.services.problem import ProblemService

router = APIRouter(prefix="/problems", tags=["problems"])


def _can_manage_problems(user: User) -> bool:
    return bool(
        user.can_manage_problems or user.is_admin or user.is_super_admin
    )


def _require_problem_manage(user: User) -> None:
    if not _can_manage_problems(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要题目管理权限"
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


@router.get("/{problem_id}", summary="题目详情")
async def get_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    problem = await ProblemService.get_by_id(db, problem_id)
    # 未公开题目对无权限者按不存在处理（404，避免泄露存在性）
    if problem is None or (
        not problem.is_public and not _can_manage_problems(current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    return ProblemService._dict(problem, with_description=True)


@router.post("", summary="创建题目")
async def create_problem(
    payload: ProblemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _require_problem_manage(current_user)
    problem = await ProblemService.create(
        db, payload.model_dump(exclude_unset=True)
    )
    return ProblemService._dict(problem, with_description=True)


@router.put("/{problem_id}", summary="更新题目")
async def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _require_problem_manage(current_user)
    problem = await ProblemService.get_by_id(db, problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    problem = await ProblemService.update(
        db, problem, payload.model_dump(exclude_unset=True)
    )
    return ProblemService._dict(problem, with_description=True)


@router.delete("/{problem_id}", summary="删除题目")
async def delete_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _require_problem_manage(current_user)
    problem = await ProblemService.get_by_id(db, problem_id)
    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在"
        )
    await ProblemService.delete(db, problem)
    return {"success": True}

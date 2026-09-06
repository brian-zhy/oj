"""题目服务。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.problem import Problem


class ProblemService:
    """题库查询与增删改（静态方法，仿 TicketService）。"""

    @staticmethod
    def _dict(p: Problem, *, with_description: bool = False) -> dict[str, Any]:
        d = {
            "id": p.id,
            "problem_number": p.problem_number,
            "title": p.title,
            "difficulty": p.difficulty,
            "source": p.source,
            "tags": p.tags or [],
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
            "submit_count": p.submit_count,
            "solved_count": p.solved_count,
            # 通过率（0-100），无提交时为 None → 前端显示「暂无」
            "pass_rate": (
                round(p.solved_count / p.submit_count * 100, 1)
                if p.submit_count
                else None
            ),
            "is_public": p.is_public,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        if with_description:
            d["description"] = p.description
        return d

    @staticmethod
    async def get_by_id(db: AsyncSession, problem_id: int) -> Optional[Problem]:
        result = await db.execute(select(Problem).where(Problem.id == problem_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_problems(
        db: AsyncSession,
        *,
        difficulty: Optional[str] = None,
        source: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        include_private: bool = False,
        page: int = 0,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """题目列表：筛选 → 计数 → 分页（按题号升序，洛谷习惯）。"""
        query = select(Problem)
        if not include_private:
            query = query.where(Problem.is_public.is_(True))

        if difficulty:
            query = query.where(Problem.difficulty == difficulty)
        if source:
            query = query.where(Problem.source == source)
        if tag:
            # 跨库写法：SQLite 中 JSON 即 TEXT，PG 上 CAST 合法；
            # 引号定界避免「DP」误命中「DP优化」
            query = query.where(cast(Problem.tags, String).ilike(f'%"{tag}"%'))
        if keyword:
            kw = keyword.strip()
            cond = Problem.title.ilike(f"%{kw}%")
            # 支持 P1001 / 1001 两种搜法定位题号（题号 = 1000 + id）
            digits = kw[1:] if kw.upper().startswith("P") else kw
            if digits.isdigit():
                ids = {int(digits), int(digits) - 1000}
                cond = or_(cond, Problem.id.in_({i for i in ids if i > 0}))
            query = query.where(cond)

        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar() or 0

        result = await db.execute(
            query.order_by(Problem.id.asc())
            .offset(page * page_size)
            .limit(page_size)
        )
        problems = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [ProblemService._dict(p) for p in problems],
        }

    @staticmethod
    async def list_sources(db: AsyncSession) -> list[str]:
        """去重后的非空来源列表（筛选下拉用）。"""
        result = await db.execute(
            select(Problem.source)
            .where(Problem.source.isnot(None), Problem.source != "")
            .distinct()
            .order_by(Problem.source.asc())
        )
        return [s for s in result.scalars().all() if s]

    @staticmethod
    async def create(db: AsyncSession, data: dict[str, Any]) -> Problem:
        problem = Problem(**data)
        db.add(problem)
        await db.commit()
        await db.refresh(problem)
        return problem

    @staticmethod
    async def update(
        db: AsyncSession, problem: Problem, data: dict[str, Any]
    ) -> Problem:
        for field, value in data.items():
            setattr(problem, field, value)
        await db.commit()
        await db.refresh(problem)
        return problem

    @staticmethod
    async def delete(db: AsyncSession, problem: Problem) -> None:
        await db.delete(problem)
        await db.commit()

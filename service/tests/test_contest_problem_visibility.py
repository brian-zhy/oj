"""比赛题目的可见性规则。

规则：**比赛结束前，未报名的人不能查看比赛题目。**

比赛详情页本来就会对未报名者隐藏题目列表，但比赛题目通常同时公开在
题库里，直接访问 /problems/{id} 或 /problems/by-code/{code} 就能读到
题面，那把锁就形同虚设。这里覆盖补在题库入口上的那条规则。

边界：
  - 未开始 → 也要挡住（否则可以提前审题）
  - 进行中 → 挡住
  - 已结束 → 放行，题目回归普通题库内容
  - 不在任何比赛里的题 → 完全不受影响
  - 比赛创建者 / 已报名者 → 放行
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _register_and_login(ac: AsyncClient) -> tuple[dict[str, str], int]:
    suffix = uuid.uuid4().hex[:8]
    username = f"pv_{suffix}"
    password = "supersecret1"
    r = await ac.post(
        "/users",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    assert r.status_code == 201, r.text
    r = await ac.post("/tokens", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = (await ac.get("/auth/me", headers=headers)).json()
    return headers, me["id"]


async def _seed_problem(owner_id: int, *, window: str) -> tuple[int, str, int, int]:
    """建一道题 + 一场比赛，返回 (problem_id, problem_number, contest_id, 任意其他题 id)。

    window: "pending" / "running" / "ended" / "none"（none = 不放进任何比赛）
    """
    from app.core.database import AsyncSessionLocal
    from app.models.contest import Contest, ContestProblem
    from app.models.problem import Problem

    now = datetime.now(timezone.utc)
    spans = {
        "pending": (now + timedelta(hours=1), now + timedelta(hours=4)),
        "running": (now - timedelta(hours=1), now + timedelta(hours=3)),
        "ended": (now - timedelta(days=2), now - timedelta(days=1)),
    }

    async with AsyncSessionLocal() as db:
        prob = Problem(title="A+B", difficulty="入门", description="求和", is_public=True)
        free = Problem(title="自由题", difficulty="入门", description="自由", is_public=True)
        db.add_all([prob, free])
        await db.flush()

        contest_id = 0
        if window != "none":
            start, end = spans[window]
            contest = Contest(title=f"测试赛-{window}", visibility="public",
                              start_time=start, end_time=end, owner_id=owner_id)
            db.add(contest)
            await db.flush()
            db.add(ContestProblem(contest_id=contest.id, problem_id=prob.id, sort_order=0))
            contest_id = contest.id

        await db.commit()
        await db.refresh(prob)
        return prob.id, prob.problem_number, contest_id, free.id


@pytest.mark.asyncio
@pytest.mark.parametrize("window", ["pending", "running"])
async def test_unregistered_cannot_read_problem_before_contest_ends(window: str):
    """未开始 / 进行中：未报名者读不到题面（含按题号访问）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        owner, owner_id = await _register_and_login(ac)
        outsider, _ = await _register_and_login(ac)
        pid, pno, cid, _free = await _seed_problem(owner_id, window=window)

        r = await ac.get(f"/problems/{pid}", headers=outsider)
        assert r.status_code == 403, r.text
        assert "报名" in r.json()["detail"]

        # 按题号绕进来同样挡住
        r = await ac.get(f"/problems/by-code/{pno}", headers=outsider)
        assert r.status_code == 403, r.text

        # 比赛详情页也不下发题目
        d = (await ac.get(f"/contests/{cid}", headers=outsider)).json()
        assert d["can_view_problems"] is False
        assert d["problems"] == []

        # 创建者不受影响
        assert (await ac.get(f"/problems/{pid}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_registering_unlocks_problem():
    """报名后立刻可见。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        owner, owner_id = await _register_and_login(ac)
        outsider, _ = await _register_and_login(ac)
        pid, _pno, cid, _free = await _seed_problem(owner_id, window="running")

        assert (await ac.get(f"/problems/{pid}", headers=outsider)).status_code == 403

        r = await ac.post(f"/contests/{cid}/register", headers=outsider, json={})
        assert r.status_code == 200, r.text

        r = await ac.get(f"/problems/{pid}", headers=outsider)
        assert r.status_code == 200, r.text
        assert r.json()["description"] == "求和"


@pytest.mark.asyncio
async def test_ended_contest_problem_is_public_again():
    """已结束：题目回归普通题库内容，未报名者也能看。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        owner, owner_id = await _register_and_login(ac)
        outsider, _ = await _register_and_login(ac)
        pid, _pno, cid, _free = await _seed_problem(owner_id, window="ended")

        assert (await ac.get(f"/problems/{pid}", headers=outsider)).status_code == 200

        d = (await ac.get(f"/contests/{cid}", headers=outsider)).json()
        assert d["can_view_problems"] is True
        assert len(d["problems"]) == 1


@pytest.mark.asyncio
async def test_free_problem_unaffected():
    """不参与任何比赛的题目完全不受影响。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        owner, owner_id = await _register_and_login(ac)
        outsider, _ = await _register_and_login(ac)
        _pid, _pno, _cid, free_id = await _seed_problem(owner_id, window="running")

        assert (await ac.get(f"/problems/{free_id}", headers=outsider)).status_code == 200


@pytest.mark.asyncio
async def test_participant_of_another_live_contest_still_reads():
    """同一道题挂在两场比赛上时，报名其中任意一场即可读题。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        owner, owner_id = await _register_and_login(ac)
        outsider, _ = await _register_and_login(ac)
        pid, _pno, cid, _free = await _seed_problem(owner_id, window="running")

        # 另外再挂一场未开始的比赛（未报名）
        from app.core.database import AsyncSessionLocal
        from app.models.contest import Contest, ContestProblem

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            extra = Contest(title="后续场次", visibility="public",
                            start_time=now + timedelta(days=1),
                            end_time=now + timedelta(days=2), owner_id=owner_id)
            db.add(extra)
            await db.flush()
            db.add(ContestProblem(contest_id=extra.id, problem_id=pid, sort_order=0))
            await db.commit()

        # 报名了正在进行的那场 → 可以读
        assert (await ac.post(f"/contests/{cid}/register", headers=outsider, json={})).status_code == 200
        assert (await ac.get(f"/problems/{pid}", headers=outsider)).status_code == 200

        # 没报名的那场不影响「比赛详情」的可见性判断
        d = (await ac.get(f"/contests/{cid}", headers=outsider)).json()
        assert d["can_view_problems"] is True

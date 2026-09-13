"""比赛期间的代码可见性规则。

规则：
  1. 别人的代码：任何时候都不给看（原有行为）
  2. 比赛进行中：**本人的代码也只有「属于这场比赛的提交」才给看** ——
     比赛题目都取自题库，赛前写好的题解在题库里本来就能翻到，
     再让提交页把它回填进编辑器，等于直接把答案送到选手眼前
  3. 比赛结束后恢复正常

提交记录本身（谁、什么时候、什么状态）不受影响，藏掉的只有代码。
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _register_and_login(ac: AsyncClient) -> tuple[dict[str, str], int]:
    suffix = uuid.uuid4().hex[:8]
    username = f"cd_{suffix}"
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


async def _seed(
    owner_id: int, *, contest_running: bool, participants: list[int]
) -> tuple[int, int]:
    """建一道带测试点的题 + 一场比赛，返回 (problem_id, contest_id)。"""
    from app.core.database import AsyncSessionLocal
    from app.models.contest import Contest, ContestParticipant, ContestProblem
    from app.models.problem import Problem
    from app.models.submission import TestCase

    now = datetime.now(timezone.utc)
    if contest_running:
        start, end = now - timedelta(hours=1), now + timedelta(hours=3)
    else:
        start, end = now - timedelta(days=2), now - timedelta(days=1)

    async with AsyncSessionLocal() as db:
        prob = Problem(title="A+B", difficulty="入门", description="求和", is_public=True)
        db.add(prob)
        await db.flush()
        db.add(TestCase(problem_id=prob.id, input_data="1 2\n",
                        expected_output="3\n", sort_order=0))

        contest = Contest(title="测试赛", visibility="public",
                          start_time=start, end_time=end, owner_id=owner_id)
        db.add(contest)
        await db.flush()
        db.add(ContestProblem(contest_id=contest.id, problem_id=prob.id, sort_order=0))
        for uid in participants:
            db.add(ContestParticipant(contest_id=contest.id, user_id=uid))
        await db.commit()
        return prob.id, contest.id


async def _add_submission(user_id: int, problem_id: int, contest_id: int | None) -> int:
    from app.core.database import AsyncSessionLocal
    from app.models.submission import Submission

    async with AsyncSessionLocal() as db:
        sub = Submission(problem_id=problem_id, user_id=user_id,
                         code=f"// contest_id={contest_id}", language="cpp",
                         status="accepted", score=100, contest_id=contest_id)
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub.id


@pytest.mark.asyncio
async def test_pre_contest_code_hidden_while_contest_running():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers, uid = await _register_and_login(ac)
        pid, cid = await _seed(uid, contest_running=True, participants=[uid])

        pre = await _add_submission(uid, pid, None)          # 赛前提交
        during = await _add_submission(uid, pid, cid)        # 比赛内提交

        # 赛前那条：藏代码，但记录本身照常返回
        d = (await ac.get(f"/submissions/{pre}", headers=headers)).json()
        assert d["code_visible"] is False
        assert "code" not in d
        assert d["code_hidden_reason"] == "比赛进行中，赛前提交的代码暂不公开"
        assert d["status"] == "accepted"                     # 记录本身不受影响

        # 比赛内那条：正常给代码
        d = (await ac.get(f"/submissions/{during}", headers=headers)).json()
        assert d["code_visible"] is True
        assert d["code"] == f"// contest_id={cid}"


@pytest.mark.asyncio
async def test_my_last_submission_does_not_prefill_pre_contest_code():
    """提交页的自动回填不能把赛前题解送出去。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers, uid = await _register_and_login(ac)
        pid, cid = await _seed(uid, contest_running=True, participants=[uid])

        await _add_submission(uid, pid, None)
        # 最近一次是赛前的 → 不回填（返回 null，前端用默认模板）
        assert (await ac.get(f"/problems/{pid}/my-last-submission",
                             headers=headers)).json() is None

        # 比赛内提交过之后 → 回填比赛内的那份
        during = await _add_submission(uid, pid, cid)
        last = (await ac.get(f"/problems/{pid}/my-last-submission", headers=headers)).json()
        assert last is not None and last["id"] == during


@pytest.mark.asyncio
async def test_others_code_never_visible():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        mine, uid = await _register_and_login(ac)
        other, other_id = await _register_and_login(ac)
        pid, cid = await _seed(uid, contest_running=True, participants=[uid, other_id])

        sub = await _add_submission(uid, pid, cid)

        d = (await ac.get(f"/submissions/{sub}", headers=other)).json()
        assert d["code_visible"] is False
        assert "code" not in d
        assert d["code_hidden_reason"] == "比赛进行中，其他人的代码暂不公开"

        # 列表里同样拿不到
        items = (await ac.get(f"/problems/{pid}/submissions",
                              headers=other)).json()["items"]
        assert items[0]["code_visible"] is False
        assert "code" not in items[0]


@pytest.mark.asyncio
async def test_code_visible_again_after_contest_ends():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers, uid = await _register_and_login(ac)
        pid, _ = await _seed(uid, contest_running=False, participants=[uid])

        sub = await _add_submission(uid, pid, None)

        d = (await ac.get(f"/submissions/{sub}", headers=headers)).json()
        assert d["code_visible"] is True
        assert d["code"] == "// contest_id=None"
        assert "code_hidden_reason" not in d

        # 没有进行中的比赛时，「我的上次提交」照常回填（比赛之外不影响刷题）
        last = (await ac.get(f"/problems/{pid}/my-last-submission", headers=headers)).json()
        assert last is not None and last["id"] == sub


@pytest.mark.asyncio
async def test_list_mixes_visible_and_hidden():
    """同一页里比赛内/赛外的提交要各自判定。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers, uid = await _register_and_login(ac)
        pid, cid = await _seed(uid, contest_running=True, participants=[uid])

        pre = await _add_submission(uid, pid, None)
        during = await _add_submission(uid, pid, cid)

        items = (await ac.get(f"/problems/{pid}/submissions",
                              headers=headers)).json()["items"]
        by_id = {i["id"]: i for i in items}
        assert by_id[during]["code_visible"] is True
        assert by_id[pre]["code_visible"] is False
        assert by_id[pre]["code_hidden_reason"]

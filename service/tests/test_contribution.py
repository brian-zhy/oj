"""贡献值与贡献商店回归测试。

- 创建主题库题 → 创建者按难度获得贡献（经验表 ×5）
- 更新题目改出题人 → 旧出题人扣回、新出题人获得
- 难度变化 → 出题人贡献按差值调整（出题人不变时）
- 团队题 → 不计贡献（防自建团刷分）
- 贡献商店：链式解锁 + 余额校验 + 兑换
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.services.judge import CONTRIBUTION_BY_DIFFICULTY


async def _contribution_of(username: str) -> int:
    async with AsyncSessionLocal() as db:
        u = (await db.execute(
            select(User).where(User.username == username))).scalar_one()
        return u.contribution or 0


@pytest.mark.asyncio
async def test_create_problem_grants_contribution():
    suffix = uuid.uuid4().hex[:8]
    admin, pwd = f"c_{suffix}", "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/users", json={
            "username": admin, "email": f"{admin}@example.com", "password": pwd})
        assert r.status_code == 201, r.text
        async with AsyncSessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.username == admin))).scalar_one()
            u.can_manage_problems = True
            await db.commit()

        r = await ac.post("/tokens", data={"username": admin, "password": pwd})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await ac.post("/problems", json={
            "title": f"题_{suffix}", "difficulty": "普及",
        }, headers=h)
        assert r.status_code in (200, 201), r.text
        assert await _contribution_of(admin) == CONTRIBUTION_BY_DIFFICULTY["普及"]

        # 难度变更 → 出题人贡献按差值调整（创建拿的普及 50 + 补差 950 = 提高档全额）
        pid = r.json()["id"]
        r = await ac.put(f"/problems/{pid}", json={"difficulty": "提高"}, headers=h)
        assert r.status_code == 200, r.text
        assert await _contribution_of(admin) == CONTRIBUTION_BY_DIFFICULTY["提高"]


@pytest.mark.asyncio
async def test_author_change_settles_both_sides():
    suffix = uuid.uuid4().hex[:8]
    admin, old_a, new_a = f"c_{suffix}", f"o_{suffix}", f"n_{suffix}"
    pwd = "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for name in (admin, old_a, new_a):
            r = await ac.post("/users", json={
                "username": name, "email": f"{name}@example.com", "password": pwd})
            assert r.status_code == 201, r.text
        async with AsyncSessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.username == admin))).scalar_one()
            u.can_manage_problems = True
            await db.commit()

        r = await ac.post("/tokens", data={"username": admin, "password": pwd})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await ac.post("/problems", json={
            "title": f"题_{suffix}", "difficulty": "普及",
        }, headers=h)
        pid = r.json()["id"]

        # 创建者先拿了普及的贡献
        assert await _contribution_of(admin) == CONTRIBUTION_BY_DIFFICULTY["普及"]

        # 指派新出题人（按用户名），难度同时提到「提高」：
        # 管理员扣普及的，新出题人拿提高的
        r = await ac.put(f"/problems/{pid}", json={
            "author": new_a, "difficulty": "提高",
        }, headers=h)
        assert r.status_code == 200, r.text
        assert await _contribution_of(admin) == 0
        assert await _contribution_of(new_a) == CONTRIBUTION_BY_DIFFICULTY["提高"]

        # 清除出题人 → 扣回
        r = await ac.put(f"/problems/{pid}", json={"author": ""}, headers=h)
        assert r.status_code == 200, r.text
        assert await _contribution_of(new_a) == 0


@pytest.mark.asyncio
async def test_team_problem_grants_no_contribution():
    suffix = uuid.uuid4().hex[:8]
    owner, team_name = f"t_{suffix}", f"团_{suffix}"
    pwd = "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/users", json={
            "username": owner, "email": f"{owner}@example.com", "password": pwd})
        assert r.status_code == 201, r.text

        r = await ac.post("/tokens", data={"username": owner, "password": pwd})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await ac.post("/teams", json={"name": team_name}, headers=h)
        assert r.status_code == 201, r.text
        team_id = r.json()["id"]

        # 团队题创建者即出题人，但不计贡献
        r = await ac.post("/problems", json={
            "title": f"团题_{suffix}", "difficulty": "提高", "team_id": team_id,
        }, headers=h)
        assert r.status_code in (200, 201), r.text
        assert await _contribution_of(owner) == 0


@pytest.mark.asyncio
async def test_contribution_shop_chain_and_redeem():
    suffix = uuid.uuid4().hex[:8]
    user = f"s_{suffix}"
    pwd = "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/users", json={
            "username": user, "email": f"{user}@example.com", "password": pwd})
        assert r.status_code == 201, r.text

        r = await ac.post("/tokens", data={"username": user, "password": pwd})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # 链式：第一件可兑，第二件被前置锁住
        r = await ac.get("/shop/contribution/items", headers=h)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert r.json()["contribution"] == 0
        assert items[0]["can_redeem"] is False  # 余额 0
        assert items[1]["locked_by"] == items[0]["name"]

        # 给贡献值：直接置余额
        async with AsyncSessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.username == user))).scalar_one()
            u.contribution = 500
            await db.commit()

        r = await ac.get("/shop/contribution/items", headers=h)
        items = r.json()["items"]
        assert r.json()["contribution"] == 500
        assert items[0]["can_redeem"] is True

        # 余额不够第二件
        r = await ac.post("/shop/contribution/redeem",
                          json={"item_id": items[1]["id"]}, headers=h)
        assert r.status_code == 400, r.text
        assert "前置" in r.json()["detail"]

        # 兑换第一件 → 余额扣减 + Tag 卡到账
        r = await ac.post("/shop/contribution/redeem",
                          json={"item_id": items[0]["id"]}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["contribution"] == 500 - items[0]["price"]

        r = await ac.get("/shop/contribution/items", headers=h)
        owned = [i for i in r.json()["items"] if i["owned"]]
        assert len(owned) == 1 and owned[0]["name"] == items[0]["name"]

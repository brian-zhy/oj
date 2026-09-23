"""题库列表可见性回归测试。

有题目管理权限的人默认可见未公开题（徽章标注），其他人只看公开题。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_problem_manager_sees_unpublished_by_default():
    suffix = uuid.uuid4().hex[:8]
    admin, normal, pwd = f"pa_{suffix}", "pn_" + suffix, "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for name in (admin, normal):
            r = await ac.post("/users", json={
                "username": name, "email": f"{name}@example.com", "password": pwd})
            assert r.status_code == 201, r.text
        async with AsyncSessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.username == admin))).scalar_one()
            u.can_manage_problems = True
            await db.commit()

        r = await ac.post("/tokens", data={"username": admin, "password": pwd})
        admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await ac.post("/tokens", data={"username": normal, "password": pwd})
        normal_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # 管理员建一道未公开题（默认 is_public=false）
        r = await ac.post("/problems", json={
            "title": f"隐藏题_{suffix}", "difficulty": "入门", "is_public": False,
        }, headers=admin_h)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]

        # 管理员列表默认可见该题
        r = await ac.get("/problems", headers=admin_h)
        assert r.status_code == 200, r.text
        mine = [p for p in r.json()["items"] if p["id"] == pid]
        assert len(mine) == 1 and mine[0]["is_public"] is False

        # 普通用户列表看不到
        r = await ac.get("/problems", headers=normal_h)
        assert r.status_code == 200, r.text
        assert all(p["id"] != pid for p in r.json()["items"])

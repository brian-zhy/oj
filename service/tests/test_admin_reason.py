"""权限操作强制填写理由的回归测试。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.user import User


async def _make_user(ac: AsyncClient, tag: str, **perms):
    uname = f"rs_{tag}_{uuid.uuid4().hex[:6]}"
    un = None
    r = await ac.post("/users", json={
        "username": uname, "email": f"{uname}@example.com", "password": "supersecret1"})
    assert r.status_code == 201, r.text
    async with AsyncSessionLocal() as db:
        u = (await db.execute(
            select(User).where(User.username == uname))).scalar_one()
        for k, v in perms.items():
            setattr(u, k, v)
        await db.commit()
        un = u.user_number
    return uname, un


async def _login(ac: AsyncClient, username: str):
    r = await ac.post("/tokens", data={"username": username, "password": "supersecret1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_permission_change_requires_reason():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        admin, admin_un = await _make_user(ac, "a", can_manage_users=True)
        target, target_un = await _make_user(ac, "t")
        h = await _login(ac, admin)

        # 无理由 → 400（三个端点）
        r = await ac.post(f"/admin/users/{target_un}/permissions",
                          json={"changes": {"can_speak": False}}, headers=h)
        assert r.status_code == 400 and "理由" in r.json()["detail"], r.text

        r = await ac.put(f"/admin/users/{target_un}",
                         json={"can_speak": False}, headers=h)
        assert r.status_code == 400 and "理由" in r.json()["detail"], r.text

        r = await ac.post(f"/admin/users/{target_un}/permissions", headers=h)
        assert r.status_code in (400, 422), r.text  # 无 body 被 FastAPI 422 拦下

        r = await ac.post("/admin/users/batch",
                          json={"user_numbers": [target_un], "updates": {"is_banned": True}},
                          headers=h)
        assert r.status_code == 400 and "理由" in r.json()["detail"], r.text

        # 带理由 → 成功
        r = await ac.post(f"/admin/users/{target_un}/permissions",
                          json={"changes": {"can_speak": False}, "reason": "测试禁言"},
                          headers=h)
        assert r.status_code == 200, r.text

        # 资料类更新（非权限字段）不需要理由
        r = await ac.put(f"/admin/users/{target_un}",
                         json={"bio": "更新简介"}, headers=h)
        assert r.status_code == 200, r.text

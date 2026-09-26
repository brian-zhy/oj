"""管理名单公示接口回归测试（参考站 /judgement/admins 的口径：任意管理权限）。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_admins_lists_only_permitted_and_is_public():
    suffix = uuid.uuid4().hex[:8]
    pwd = "supersecret1"
    names = {
        "usermgmt": {"can_manage_users": True},
        "postmgmt": {"can_manage_posts": True},
        "tagmgmt": {"can_manage_tags": True},
        "super": {"is_super_admin": True},
        "plain": {},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for name, perms in names.items():
            uname = f"{name}_{suffix}"
            r = await ac.post("/users", json={
                "username": uname, "email": f"{uname}@example.com", "password": pwd})
            assert r.status_code == 201, r.text
            async with AsyncSessionLocal() as db:
                u = (await db.execute(
                    select(User).where(User.username == uname))).scalar_one()
                for field, val in perms.items():
                    setattr(u, field, val)
                await db.commit()

        # 无需登录即可访问
        r = await ac.get("/judgement/admins")
        assert r.status_code == 200, r.text
        data = {a["username"]: a for a in r.json()["admins"]}

        # 持有任何管理权限的都上榜
        for key in ("usermgmt", "postmgmt", "tagmgmt", "super"):
            assert f"{key}_{suffix}" in data, f"{key} 应在名单中"
        # 无任何管理权限的普通用户不上榜
        assert f"plain_{suffix}" not in data

        # 公开字段里不泄露权限以外的敏感信息
        sample = next(iter(data.values()))
        assert "hashed_password" not in sample and "email" not in sample

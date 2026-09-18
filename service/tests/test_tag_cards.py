"""Tag 卡授予/删除流程回归测试。

背景：路由曾写成双重前缀（prefix=/users 加上路径里的 /users/...），
实际挂在 /users/users/{id}/tag-cards，前端调 /users/{id}/tag-cards 直接 404。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.core.database import engine
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_grant_and_delete_tag_card():
    suffix = uuid.uuid4().hex[:8]
    granter, target = f"g_{suffix}", f"t_{suffix}"
    pwd = "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for name in (granter, target):
            r = await ac.post("/users", json={
                "username": name, "email": f"{name}@example.com", "password": pwd})
            assert r.status_code == 201, r.text

        # 授予者需要 Tag 管理权限：直接升为超管
        r = await ac.post("/tokens", data={"username": granter, "password": pwd})
        granter_at = r.json()["access_token"]
        r = await ac.get("/users/me", headers={"Authorization": f"Bearer {granter_at}"})
        granter_id = r.json()["id"]
        async with engine.begin() as conn:
            await conn.execute(
                update(User).where(User.id == granter_id).values(is_super_admin=True))

        r = await ac.post("/tokens", data={"username": target, "password": pwd})
        target_at = r.json()["access_token"]
        r = await ac.get("/users/me", headers={"Authorization": f"Bearer {target_at}"})
        target_id = r.json()["id"]

        # 普通用户无权授予
        r = await ac.post(f"/users/{target_id}/tag-cards",
                          json={"name": "内鬼"},
                          headers={"Authorization": f"Bearer {target_at}"})
        assert r.status_code == 403, r.text

        # 超管授予 → 201
        r = await ac.post(f"/users/{target_id}/tag-cards",
                          json={"name": "内鬼"},
                          headers={"Authorization": f"Bearer {granter_at}"})
        assert r.status_code == 201, r.text
        card_id = r.json()["id"]

        # 重复授予同名 → 400
        r = await ac.post(f"/users/{target_id}/tag-cards",
                          json={"name": "内鬼"},
                          headers={"Authorization": f"Bearer {granter_at}"})
        assert r.status_code == 400, r.text

        # 目标用户能看到自己的 Tag 卡
        r = await ac.get("/users/me/tag-cards",
                         headers={"Authorization": f"Bearer {target_at}"})
        assert r.status_code == 200, r.text
        assert [c["name"] for c in r.json()["items"]] == ["内鬼"]

        # 删除 → 204，列表清空
        r = await ac.delete(f"/users/{target_id}/tag-cards/{card_id}",
                            headers={"Authorization": f"Bearer {granter_at}"})
        assert r.status_code == 204, r.text
        r = await ac.get("/users/me/tag-cards",
                         headers={"Authorization": f"Bearer {target_at}"})
        assert r.json()["items"] == []

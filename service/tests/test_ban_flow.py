"""封禁闭环回归测试：封禁必须同时挡住旧会话、刷新续命、重新登录与进团路径。

背景：曾出现「被封禁用户仍能加入团队」——封禁只挡了 /auth/login 新登录，
已登录会话（refresh token 未吊销）与 teams 各口子均不查 is_banned。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.team import TeamJoinRequest
from app.models.user import User
from app.services.auth import issue_token_pair, revoke_user_tokens


@pytest.mark.asyncio
async def test_ban_kicks_session_and_blocks_team_join():
    suffix = uuid.uuid4().hex[:8]
    victim, owner, pwd = f"vb_{suffix}", f"ob_{suffix}", "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for name in (victim, owner):
            r = await ac.post("/users", json={
                "username": name, "email": f"{name}@example.com", "password": pwd})
            assert r.status_code == 201, r.text

        # 封禁前：受害者登录拿到会话，团主建团
        r = await ac.post("/tokens", data={"username": victim, "password": pwd})
        assert r.status_code == 200, r.text
        access, refresh = r.json()["access_token"], r.json()["refresh_token"]

        r = await ac.post("/tokens", data={"username": owner, "password": pwd})
        owner_at = r.json()["access_token"]
        r = await ac.post("/teams", json={"name": f"team_{suffix}"},
                          headers={"Authorization": f"Bearer {owner_at}"})
        assert r.status_code == 201, r.text
        team_id = r.json()["id"]

        # 封禁动作（与 admin 端点一致：置位 is_banned + 吊销全部刷新令牌）
        async with AsyncSessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.username == victim))).scalar_one()
            u.is_banned = True
            await db.commit()
            uid = u.id
            assert await revoke_user_tokens(db, uid) >= 1

        # 旧会话下一请求即失效（无 live 刷新令牌 → 401）
        r = await ac.get("/users/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 401

        # 已吊销的刷新令牌不能续命
        r = await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401

        # 防御纵深：若仍有存活的刷新令牌，刷新时查封禁 → 403 且令牌被吊销
        _, live_refresh = await issue_token_pair(AsyncSessionLocal(), uid)
        r = await ac.post("/tokens/refresh", json={"refresh_token": live_refresh})
        assert r.status_code == 403, r.text
        r = await ac.post("/tokens/refresh", json={"refresh_token": live_refresh})
        assert r.status_code == 401

        # 备用登录口 /tokens 也查封禁 → 403
        r = await ac.post("/tokens", data={"username": victim, "password": pwd})
        assert r.status_code == 403

        # 模拟「封禁瞬间已在途的令牌」：加入团队 → 403
        access2, _ = await issue_token_pair(AsyncSessionLocal(), uid)
        r = await ac.post(f"/teams/{team_id}/join",
                          headers={"Authorization": f"Bearer {access2}"})
        assert r.status_code == 403, r.text

        # 申请在审核期间被封禁：团主通过申请 → 403 且申请被清除
        async with AsyncSessionLocal() as db:
            db.add(TeamJoinRequest(team_id=team_id, user_id=uid))
            await db.commit()
        r = await ac.post(f"/teams/{team_id}/requests/{uid}/approve",
                          headers={"Authorization": f"Bearer {owner_at}"})
        assert r.status_code == 403, r.text
        async with AsyncSessionLocal() as db:
            left = (await db.execute(select(TeamJoinRequest).where(
                TeamJoinRequest.user_id == uid))).scalars().all()
        assert not left

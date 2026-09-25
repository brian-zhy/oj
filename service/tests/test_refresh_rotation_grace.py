"""刷新令牌轮换宽限期的回归测试。

背景：站点出现「每隔两三分钟被退出登录」。日志显示同一秒内 refresh 先 200 再 401——
多个标签页并发提交同一个已轮换的 refresh 令牌，输掉的一方收到 401，前端于是清空
整个会话并把所有人踢回登录页。

修复：轮换作废的令牌在极短窗口（REFRESH_ROTATION_GRACE_SECONDS）内仍可用于重放；
主动吊销（改密、封禁、超出数量上限）不写 rotated_at，因此立即失效。
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_token
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth import issue_token_pair, revoke_user_tokens

PASSWORD = "supersecret1"


async def _make_user(ac: AsyncClient, prefix: str) -> str:
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    r = await ac.post(
        "/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
    )
    assert r.status_code == 201, r.text
    return username


async def _login(ac: AsyncClient, username: str) -> tuple[str, str]:
    r = await ac.post("/tokens", data={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"], r.json()["refresh_token"]


async def _user_id(username: str) -> int:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(select(User.id).where(User.username == username))
        ).scalar_one()


async def _backdate_rotated(raw_refresh: str, seconds_ago: int) -> None:
    """把某个令牌的轮换时刻改到过去，用来模拟「宽限期已过」。"""
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(raw_refresh))
            .values(rotated_at=datetime.now(timezone.utc) - timedelta(seconds=seconds_ago))
        )
        await db.commit()


async def _rotated_at(raw_refresh: str) -> datetime | None:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(RefreshToken.rotated_at).where(
                    RefreshToken.token_hash == hash_token(raw_refresh)
                )
            )
        ).scalar_one()


async def _live_count(user_id: int) -> int:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(func.count())
                .select_from(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False,  # noqa: E712
                    RefreshToken.expires_at > func.now(),
                )
            )
        ).scalar_one()


@pytest.mark.asyncio
async def test_concurrent_replay_within_grace_both_succeed():
    """同一令牌被并发提交两次（多标签页竞态的真实形状）时，两次都必须成功。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        username = await _make_user(ac, "race")
        _, refresh = await _login(ac, username)

        first, second = await asyncio.gather(
            ac.post("/tokens/refresh", json={"refresh_token": refresh}),
            ac.post("/tokens/refresh", json={"refresh_token": refresh}),
        )
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text

        # 两次各自换到独立的、可用的新令牌（不是把同一个令牌重复返回）
        token_a = first.json()["refresh_token"]
        token_b = second.json()["refresh_token"]
        assert token_a != token_b
        for token in (token_a, token_b):
            r = await ac.post("/tokens/refresh", json={"refresh_token": token})
            assert r.status_code == 200, r.text
            me = await ac.get(
                "/users/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}
            )
            assert me.status_code == 200, me.text


@pytest.mark.asyncio
async def test_replay_outside_grace_is_rejected():
    """超出宽限期的旧令牌一律 401，否则重放窗口等于永久有效。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        username = await _make_user(ac, "grace")
        _, refresh = await _login(ac, username)

        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200, "首次轮换应成功"
        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200, "宽限期内的重放应被放行"

        # 把轮换时刻推到窗口之外：拒绝
        await _backdate_rotated(refresh, settings.REFRESH_ROTATION_GRACE_SECONDS + 60)
        r = await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_replay_does_not_extend_grace_window():
    """重放不得把宽限窗口重新推后，否则循环重放可无限续命。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        username = await _make_user(ac, "extend")
        _, refresh = await _login(ac, username)

        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200
        original = await _rotated_at(refresh)
        assert original is not None, "轮换应写下 rotated_at"

        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200, "宽限期内的重放仍应成功"
        assert await _rotated_at(refresh) == original, "重放不应把宽限窗口重新推后"


@pytest.mark.asyncio
async def test_deliberate_revocation_is_immediate():
    """改密/登出这类主动吊销不受宽限期放行：吊销后旧令牌立刻 401。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        username = await _make_user(ac, "revoke")
        _, refresh = await _login(ac, username)

        # 先正常轮换一次，让该令牌进入「已作废但在宽限期内」的状态
        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200
        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200

        uid = await _user_id(username)
        async with AsyncSessionLocal() as db:
            assert await revoke_user_tokens(db, uid) >= 1

        # 主动吊销立即生效：宽限期救不了它
        r = await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401, r.text
        assert await _rotated_at(refresh) is not None  # 轮换写下的值未被改写


@pytest.mark.asyncio
async def test_banned_user_cannot_replay_in_grace():
    """封禁用户即使在宽限期内重放，也只能拿到 403，不能续命。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        username = await _make_user(ac, "ban")
        _, refresh = await _login(ac, username)

        assert (
            await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        ).status_code == 200

        uid = await _user_id(username)
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
            user.is_banned = True
            await db.commit()

        # 轮换作废但仍在宽限期内的那枚令牌，被封禁拦截
        r = await ac.post("/tokens/refresh", json={"refresh_token": refresh})
        assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_live_tokens_are_capped():
    """有效令牌数量有上限，防止靠重放无限堆积。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        username = await _make_user(ac, "cap")
        uid = await _user_id(username)

        async with AsyncSessionLocal() as db:
            for _ in range(settings.MAX_LIVE_REFRESH_TOKENS + 5):
                await issue_token_pair(db, uid)

        assert await _live_count(uid) == settings.MAX_LIVE_REFRESH_TOKENS

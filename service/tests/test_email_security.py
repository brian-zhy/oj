"""邮件相关接口的两道安全防线。

1. `POST /auth/send-verification` 是公开接口且会真发邮件，必须限流，
   否则等于对外提供了一个免费的邮件发送工具，SMTP 账号会被封。
2. `GET /auth/email-config-test` 会返回 SMTP 主机/端口/发件邮箱，
   必须限超管（曾经是无鉴权的）。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.utils import ratelimit


@pytest.fixture(autouse=True)
def _clean_buckets():
    """限流桶是进程级全局状态，用例之间要互相隔离。"""
    ratelimit._buckets.clear()
    yield
    ratelimit._buckets.clear()


def _fresh_email() -> str:
    return f"mail_{uuid.uuid4().hex[:10]}@example.com"


async def _register_and_login(ac: AsyncClient) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"mail_{suffix}"
    password = "supersecret1"
    r = await ac.post(
        "/users",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    assert r.status_code == 201, r.text
    r = await ac.post("/tokens", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_send_verification_has_per_email_cooldown():
    """同一邮箱 60 秒内只能发一次（测试环境没配 SMTP，走演示模式直接返回成功）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        email = _fresh_email()

        first = await ac.post("/auth/send-verification", json={"email": email})
        assert first.status_code == 200, first.text
        assert first.json()["token"]

        second = await ac.post("/auth/send-verification", json={"email": email})
        assert second.status_code == 429, second.text
        assert "刚刚发送过" in second.json()["detail"]

        # 冷却按邮箱算，换个邮箱不受影响
        other = await ac.post("/auth/send-verification", json={"email": _fresh_email()})
        assert other.status_code == 200, other.text


@pytest.mark.asyncio
async def test_send_verification_email_case_insensitive():
    """大小写不同不能绕过冷却（A@x.com 与 a@x.com 是同一个收件箱）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        base = f"Case_{uuid.uuid4().hex[:8]}@Example.com"

        assert (await ac.post("/auth/send-verification", json={"email": base})).status_code == 200
        again = await ac.post("/auth/send-verification", json={"email": base.lower()})
        assert again.status_code == 429, again.text


@pytest.mark.asyncio
async def test_send_verification_caps_daily_per_email(monkeypatch):
    """同一邮箱每天有上限，防止拿一个收件箱反复轰炸。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "EMAIL_SEND_PER_EMAIL_DAY", 2)
    monkeypatch.setattr(
        "app.api.extended_auth._SEND_EMAIL_COOLDOWN_SECONDS", 0, raising=True
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        email = _fresh_email()
        for _ in range(2):
            r = await ac.post("/auth/send-verification", json={"email": email})
            assert r.status_code == 200, r.text

        r = await ac.post("/auth/send-verification", json={"email": email})
        assert r.status_code == 429, r.text
        assert "今日发送次数已达上限" in r.json()["detail"]


@pytest.mark.asyncio
async def test_send_verification_has_global_cap(monkeypatch):
    """全站总额度 —— 换多少邮箱都拦得住，这是保护 SMTP 账号的最后一道闸。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "EMAIL_SEND_GLOBAL_PER_HOUR", 3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for _ in range(3):
            r = await ac.post("/auth/send-verification", json={"email": _fresh_email()})
            assert r.status_code == 200, r.text

        r = await ac.post("/auth/send-verification", json={"email": _fresh_email()})
        assert r.status_code == 429, r.text
        assert "系统发信繁忙" in r.json()["detail"]


@pytest.mark.asyncio
async def test_send_verification_rejects_bad_input_before_limiting():
    """格式不对直接 400，不该消耗额度。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/auth/send-verification", json={"email": "not-an-email"})
        assert r.status_code == 400

        r = await ac.post("/auth/send-verification", json={})
        assert r.status_code == 400

        # 没被垃圾请求占用额度
        assert (await ac.post("/auth/send-verification", json={"email": _fresh_email()})).status_code == 200


@pytest.mark.asyncio
async def test_email_config_test_requires_super_admin():
    """邮箱配置诊断接口不再对公网开放。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        # 匿名 → 401
        r = await ac.get("/auth/email-config-test")
        assert r.status_code == 401

        # 普通用户 → 403（以前这里是 200，会把 SMTP 主机和发件邮箱全吐出来）
        headers = await _register_and_login(ac)
        r = await ac.get("/auth/email-config-test", headers=headers)
        assert r.status_code == 403
        assert "超级管理员" in r.json()["detail"]


@pytest.mark.asyncio
async def test_email_config_test_ok_for_super_admin():
    """超管仍然可以正常用它排查配置。"""
    from sqlalchemy import update

    from app.core.database import engine
    from app.models.user import User

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        me = (await ac.get("/auth/me", headers=headers)).json()

        async with engine.begin() as conn:
            await conn.execute(
                update(User).where(User.id == me["id"]).values(is_super_admin=True)
            )

        r = await ac.get("/auth/email-config-test", headers=headers)
        assert r.status_code == 200, r.text
        assert "configured" in r.json()

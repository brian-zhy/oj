"""按 IP 限流的回归测试（防代理池刷匿名接口）。

背景：站点曾遭「几千虚拟 IP + 批量邮箱」的脚本访问。匿名接口（注册/登录/
发验证码/忘记密码）原先没有按 IP 的限流，批量造小号无成本。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.utils.ip import get_client_ip


def _email() -> str:
    return f"ip_{uuid.uuid4().hex[:10]}@example.com"


async def _post(ac: AsyncClient, url: str, ip: str, **kwargs):
    return await ac.post(url, headers={"X-Real-IP": ip}, **kwargs)


@pytest.mark.asyncio
async def test_get_client_ip_prefers_x_real_ip():
    """X-Real-IP 优先（宝塔覆盖写入，不可伪造），缺失时回退对端地址。"""
    from fastapi import Request

    async def receive():  # pragma: no cover - 不涉及请求体
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-real-ip", b"1.2.3.4")],
        "client": ("172.18.0.5", 40000),
        "query_string": b"",
    }
    assert get_client_ip(Request(scope, receive)) == "1.2.3.4"

    empty_scope = dict(scope, headers=[])
    assert get_client_ip(Request(empty_scope, receive)) == "172.18.0.5"


@pytest.mark.asyncio
async def test_register_ip_limit_blocks_bulk_signup():
    """同一 IP 一天最多 5 次注册尝试，第 6 次 429 —— 批量造号被卡死。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for _ in range(5):
            r = await _post(ac, "/auth/register", "203.0.113.7", json={
                "username": f"u_{uuid.uuid4().hex[:8]}",
                "email": _email(),
                "password": "supersecret1",
            })
            assert r.status_code in (200, 400, 409), r.text  # 未触发 IP 限流

        r = await _post(ac, "/auth/register", "203.0.113.7", json={
            "username": f"u_{uuid.uuid4().hex[:8]}",
            "email": _email(),
            "password": "supersecret1",
        })
        assert r.status_code == 429, r.text
        assert "请求过于频繁" in r.json()["detail"]


@pytest.mark.asyncio
async def test_different_ips_have_independent_buckets():
    """IP 桶相互独立，换 IP 不受影响。"""
    body = {"username": "abc", "password": "supersecret1"}  # 形状合法，业务层 400
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for _ in range(5):
            r = await _post(ac, "/auth/register", "198.51.100.9", json=body)
            assert r.status_code == 400, r.text
        # 换 IP 不受前一个 IP 的计数影响
        r = await _post(ac, "/auth/register", "198.51.100.10", json=body)
        assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_phone_registration_is_disabled():
    """手机注册无短信验证能力，是免验证造号通道，必须拒绝。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await _post(ac, "/auth/register", "203.0.113.99", json={
            "username": f"p_{uuid.uuid4().hex[:8]}",
            "phone": "13800138000",
            "password": "supersecret1",
        })
        assert r.status_code == 400, r.text
        assert "手机号注册" in r.json()["detail"]


@pytest.mark.asyncio
async def test_send_verification_ip_limit():
    """换着邮箱刷发信也会被按 IP 的限制拦住。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        for _ in range(5):
            r = await _post(ac, "/auth/send-verification", "192.0.2.66",
                            json={"email": _email()})
            assert r.status_code == 200, r.text

        r = await _post(ac, "/auth/send-verification", "192.0.2.66",
                        json={"email": _email()})
        assert r.status_code == 429, r.text
        assert "请求过于频繁" in r.json()["detail"]


@pytest.mark.asyncio
async def test_login_ip_limit():
    """登录按 IP 限流（防撞库）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        payload = {"identifier": "nobody", "password": "x",
                   "captcha_id": "x", "captcha": "x"}
        for _ in range(10):
            r = await _post(ac, "/auth/login", "192.0.2.77", json=payload)
            assert r.status_code in (400, 401), r.text  # 未触发 IP 限流

        r = await _post(ac, "/auth/login", "192.0.2.77", json=payload)
        assert r.status_code == 429, r.text

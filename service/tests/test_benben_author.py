"""犇犇按作者筛选 —— 用户主页的「动态」标签页依赖这个能力。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _register_and_login(ac: AsyncClient) -> tuple[dict[str, str], int, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"bb_{suffix}"
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
    return headers, me["user_number"], username


async def _post(ac: AsyncClient, headers: dict[str, str], content: str) -> dict:
    r = await ac.post("/benben", headers=headers, json={"content": content})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_benben_filtered_by_author():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers_a, number_a, _ = await _register_and_login(ac)
        headers_b, number_b, _ = await _register_and_login(ac)

        await _post(ac, headers_a, "A 的动态")
        await _post(ac, headers_b, "B 的动态")

        # 不筛选：两条都在
        all_items = (await ac.get("/benben", params={"limit": 50})).json()
        assert len(all_items) == 2

        # 只看 A
        only_a = (
            await ac.get("/benben", params={"limit": 50, "user_number": number_a})
        ).json()
        assert [i["content"] for i in only_a] == ["A 的动态"]

        # 只看 B
        only_b = (
            await ac.get("/benben", params={"limit": 50, "user_number": number_b})
        ).json()
        assert [i["content"] for i in only_b] == ["B 的动态"]


@pytest.mark.asyncio
async def test_is_owner_only_for_own_posts():
    """前端据此决定要不要显示「删除」按钮，必须由后端判定。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers_a, number_a, _ = await _register_and_login(ac)
        headers_b, _, _ = await _register_and_login(ac)

        await _post(ac, headers_a, "只有 A 发过")

        # A 看自己的主页 → is_owner 为真（能删）
        as_a = (
            await ac.get(
                "/benben", params={"limit": 50, "user_number": number_a}, headers=headers_a
            )
        ).json()
        assert as_a[0]["is_owner"] is True

        # B 看 A 的主页 → is_owner 为假（不给删）
        as_b = (
            await ac.get(
                "/benben", params={"limit": 50, "user_number": number_a}, headers=headers_b
            )
        ).json()
        assert as_b[0]["is_owner"] is False

        # 未登录看 A 的主页 → 同样为假
        anon = (
            await ac.get("/benben", params={"limit": 50, "user_number": number_a})
        ).json()
        assert anon[0]["is_owner"] is False


@pytest.mark.asyncio
async def test_benben_filter_paginates():
    """按作者筛选时 before_id 分页仍要生效。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers, number, _ = await _register_and_login(ac)
        first = await _post(ac, headers, "第一条")

        page = (
            await ac.get(
                "/benben",
                params={"limit": 50, "user_number": number, "before_id": first["id"]},
            )
        ).json()
        assert page == []

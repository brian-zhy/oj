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


@pytest.mark.asyncio
async def test_benben_incremental_after_id():
    """自动刷新用的增量拉取：只回比 after_id 新的，没有新的就回空数组。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers_a, number_a, _ = await _register_and_login(ac)
        headers_b, number_b, _ = await _register_and_login(ac)

        old = await _post(ac, headers_a, "旧动态")

        # 拿最新的 id 当游标：此刻没有更新的东西
        assert (await ac.get("/benben", params={"after_id": old["id"]})).json() == []

        # 别人发了新的 → 只回这一条
        new = await _post(ac, headers_b, "新动态")
        fresh = (await ac.get("/benben", params={"after_id": old["id"]})).json()
        assert [i["content"] for i in fresh] == ["新动态"]
        assert [i["id"] for i in fresh] == [new["id"]]

        # 游标推到最新 → 又空了（前端每轮轮询就是这样判「没有新内容」的）
        assert (await ac.get("/benben", params={"after_id": new["id"]})).json() == []

        # 增量拉取也能跟作者筛选叠加
        only_a = (
            await ac.get(
                "/benben", params={"after_id": old["id"], "user_number": number_a}
            )
        ).json()
        assert only_a == []
        only_b = (
            await ac.get(
                "/benben", params={"after_id": old["id"], "user_number": number_b}
            )
        ).json()
        assert [i["content"] for i in only_b] == ["新动态"]


async def _seed_benben(user_number: int, content: str) -> int:
    """直接建库，绕开「每人 10 秒只能发一条」的频率限制。"""
    from app.core.database import AsyncSessionLocal
    from app.models.benben import Benben

    async with AsyncSessionLocal() as db:
        item = Benben(user_number=user_number, content=content)
        db.add(item)
        await db.flush()
        await db.commit()
        return item.id


@pytest.mark.asyncio
async def test_existing_ids_check_detects_deletion():
    """自动刷新靠这个接口发现「别人把犇犇删了」。

    增量刷新只按 after_id 拉新增，删除是没有信号的，页面不刷新那条就一直挂着。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers, number, _ = await _register_and_login(ac)
        first = await _seed_benben(number, "待会儿要删掉的")
        second = await _seed_benben(number, "保留的")

        # 两条都还在
        r = await ac.get("/benben/existing", params={"ids": f"{first},{second}"})
        assert r.status_code == 200, r.text
        assert sorted(r.json()["ids"]) == sorted([first, second])

        # 删掉第一条后，核对结果里就不该再有它
        assert (await ac.delete(f"/benben/{first}", headers=headers)).status_code == 204
        r = await ac.get("/benben/existing", params={"ids": f"{first},{second}"})
        assert r.json()["ids"] == [second]

        # 不存在的 id 不会凭空冒出来
        r = await ac.get("/benben/existing", params={"ids": "999999"})
        assert r.json()["ids"] == []


@pytest.mark.asyncio
async def test_existing_ids_param_hygiene():
    """参数里混进垃圾 / 重复 / 空值时不能 500，也不能被超长 URL 拖垮。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        _headers, number, _ = await _register_and_login(ac)
        item = await _seed_benben(number, "拿来当靶子的")

        # 重复 + 空白 + 非法片段：只按去重后的合法 id 查
        r = await ac.get(
            "/benben/existing",
            params={"ids": f" {item}, {item} ,abc,, -3 ,{item}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ids"] == [item]

        # 全是垃圾 → 空结果，不报错
        assert (await ac.get("/benben/existing", params={"ids": "abc,,"})).json()["ids"] == []

        # 超量输入被截断，不会把查询拖死
        many = ",".join(str(i) for i in range(1, 500))
        r = await ac.get("/benben/existing", params={"ids": many})
        assert r.status_code == 200, r.text

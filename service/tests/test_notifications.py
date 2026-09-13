"""通知中心：帖子/工单被回复有消息，@提及 另有消息。

规则要点：
  1. 回复你的帖子/工单 → type='reply'
  2. 正文里 @ 了你 → type='mention'。**被 @ 只代表提及，不代表被回复**，
     所以两者分开成不同的 type，前端分「@我的」「回复我的」两个标签页
  3. 自己 @ 自己、自己回复自己 → 不发通知
  4. 邮箱 a@b.com、以及链接地址里的 @ 都不算提及
  5. @提及 的落点是用户主页：/user/{用户名} 也能打开（见 by-username 用例）
"""

import re
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _register_and_login(ac: AsyncClient) -> tuple[dict[str, str], str, int]:
    suffix = uuid.uuid4().hex[:8]
    username = f"nt_{suffix}"
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
    return headers, username, me["id"]


async def _notifications(ac: AsyncClient, headers: dict[str, str], **params) -> list[dict]:
    r = await ac.get("/notifications", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()["notifications"]


async def _new_post(ac: AsyncClient, headers: dict[str, str], title: str = "测试帖子") -> int:
    # 站务版仅秩序管理可发帖，测试用普通用户能发帖的灌水区
    r = await ac.post(
        "/forum/posts",
        headers=headers,
        json={"title": title, "content": "正文", "forum": "relevantaffairs"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_reply_to_post_notifies_author_only():
    """回复帖子 → 楼主收到 reply 通知；回复者自己什么都没有。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        author, author_name, _ = await _register_and_login(ac)
        replier, replier_name, _ = await _register_and_login(ac)
        post_id = await _new_post(ac, author, "复活啦")

        r = await ac.post(
            f"/forum/posts/{post_id}/comments",
            headers=replier,
            json={"content": "欢迎回来"},
        )
        assert r.status_code == 201, r.text

        items = await _notifications(ac, author)
        assert len(items) == 1
        n = items[0]
        assert n["type"] == "reply"
        assert n["link"] == f"/discuss/{post_id}"
        # 文案里的 @ 用户名由前端渲染成主页链接，这里确认后端写进去了
        assert n["content"].startswith(f"@{replier_name}")
        assert "复活啦" in n["content"]

        assert await _notifications(ac, replier) == []


@pytest.mark.asyncio
async def test_mention_is_separate_type_from_reply():
    """被 @ 收到的通知是 mention，不是 reply；而且楼主同时会收到 reply。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        author, _author_name, _ = await _register_and_login(ac)
        third, third_name, _ = await _register_and_login(ac)
        replier, _replier_name, _ = await _register_and_login(ac)
        post_id = await _new_post(ac, author, "请教一个问题")

        r = await ac.post(
            f"/forum/posts/{post_id}/comments",
            headers=replier,
            json={"content": f"@Nobody1 不存在的人 顺便 @{third_name} 来看下"},
        )
        assert r.status_code == 201, r.text

        # 被 @ 的人：只有提及通知，且正文里那个不存在的用户不该产生任何东西
        items = await _notifications(ac, third)
        assert len(items) == 1
        assert items[0]["type"] == "mention"
        assert items[0]["link"] == f"/discuss/{post_id}"

        # 楼主：只有「被回复」，没有被 @
        author_types = [n["type"] for n in await _notifications(ac, author)]
        assert author_types == ["reply"]


@pytest.mark.asyncio
async def test_mention_not_notified_for_email_or_self():
    """邮箱/链接里的 @ 不算提及；自己 @ 自己也不发。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        author, author_name, _ = await _register_and_login(ac)
        post_id = await _new_post(ac, author, "自娱自乐")

        # 自己是楼主：回复自己既不发 reply 也不发 mention
        r = await ac.post(
            f"/forum/posts/{post_id}/comments",
            headers=author,
            json={"content": f"@{author_name} 自己回自己，顺便留个邮箱 a@b.com"},
        )
        assert r.status_code == 201, r.text
        assert await _notifications(ac, author) == []


@pytest.mark.asyncio
async def test_mention_parsing_rules():
    """直接覆盖提及解析：边界、去重、邮箱与链接排除。"""
    from app.services.notification import extract_mentions

    assert extract_mentions("@alice @bob @alice") == ["alice", "bob"]
    assert extract_mentions("邮箱 a@b.com 不是提及") == []
    assert extract_mentions("看看 https://x.com/@foo 也不是") == []
    assert extract_mentions("@ab 太短不算") == []


@pytest.mark.asyncio
async def test_group_filter_and_unread_breakdown():
    """标签页过滤 + 分组未读数。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        author, author_name, _ = await _register_and_login(ac)
        actor, _actor_name, _ = await _register_and_login(ac)
        post_id = await _new_post(ac, author, "分组测试")

        # 两条：一条 @ 楼主、一条纯回复
        await ac.post(f"/forum/posts/{post_id}/comments", headers=actor,
                      json={"content": f"@{author_name} 提一下"})
        await ac.post(f"/forum/posts/{post_id}/comments", headers=actor,
                      json={"content": "普通回复"})

        mentions = await _notifications(ac, author, group="mention")
        replies = await _notifications(ac, author, group="reply")
        assert [n["type"] for n in mentions] == ["mention"]
        assert [n["type"] for n in replies] == ["reply"]
        assert await _notifications(ac, author, group="system") == []

        counts = (await ac.get("/notifications/unread-count", headers=author)).json()
        assert counts["count"] == 2
        assert counts["by_group"] == {"mention": 1, "reply": 1, "system": 0}


@pytest.mark.asyncio
async def test_ticket_reply_and_mention_notifications():
    """工单：被回复 → reply，被 @ → mention，各自带 /tickets/{id}。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        creator, _creator_name, _ = await _register_and_login(ac)
        third, third_name, _ = await _register_and_login(ac)
        staff, _staff_name, _ = await _register_and_login(ac)

        r = await ac.post("/tickets", headers=creator, json={
            "title": "登录不上", "category": "bug",
            "content": "点登录按钮没反应", "priority": "normal",
        })
        assert r.status_code == 200, r.text
        ticket_id = r.json()["id"]

        r = await ac.post(f"/tickets/{ticket_id}/replies", headers=staff,
                          json={"content": f"看一下 @{third_name} 遇到过吗"})
        assert r.status_code == 200, r.text

        creator_types = [n["type"] for n in await _notifications(ac, creator)]
        assert creator_types == ["reply"]
        assert (await _notifications(ac, creator))[0]["link"] == f"/tickets/{ticket_id}"

        third_items = await _notifications(ac, third)
        assert [n["type"] for n in third_items] == ["mention"]
        assert third_items[0]["link"] == f"/tickets/{ticket_id}"


@pytest.mark.asyncio
async def test_benben_mention_and_linkified_username_route():
    """犇犇里的 @ 也发通知；@ 生成的链接要能打开，所以按用户名也能查用户。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        speaker, _speaker_name, _ = await _register_and_login(ac)
        target, target_name, target_id = await _register_and_login(ac)

        r = await ac.post("/benben", headers=speaker,
                          json={"content": f"@solver 试一下 @{target_name}"})
        assert r.status_code == 201, r.text

        items = await _notifications(ac, target)
        assert [n["type"] for n in items] == ["mention"]
        assert items[0]["link"] == "/"

        # @提及 渲染出的 /user/{用户名} 要能打开
        r = await ac.get(f"/users/by-username/{target_name}")
        assert r.status_code == 200, r.text
        assert r.json()["id"] == target_id

        # 非法用户名 / 不存在的用户名都是 404，不能 500
        assert (await ac.get("/users/by-username/ab")).status_code == 404
        assert (await ac.get("/users/by-username/%20")).status_code == 404
        assert (await ac.get("/users/by-username/nobody_here")).status_code == 404


@pytest.mark.asyncio
async def test_notification_content_fits_column():
    """content 列是 String(200)，超长标题不能把写入搞崩。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        author, _author_name, _ = await _register_and_login(ac)
        actor, _actor_name, _ = await _register_and_login(ac)
        post_id = await _new_post(ac, author, "长标题" * 25)  # 100 字上限

        assert (await ac.post(f"/forum/posts/{post_id}/comments", headers=actor,
                              json={"content": "顶"})).status_code == 201
        items = await _notifications(ac, author)
        assert len(items) == 1
        assert len(items[0]["content"]) <= 200

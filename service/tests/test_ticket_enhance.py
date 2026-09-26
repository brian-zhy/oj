"""工单增强回归测试：改标题、附件上传/删除与权限边界。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.ticket import Ticket
from app.models.user import User

TXT = b"attachment content"


async def _make_user(ac: AsyncClient, tag: str, **perms) -> str:
    uname = f"tk_{tag}_{uuid.uuid4().hex[:6]}"
    r = await ac.post("/users", json={
        "username": uname, "email": f"{uname}@example.com", "password": "supersecret1"})
    assert r.status_code == 201, r.text
    if perms:
        async with AsyncSessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.username == uname))).scalar_one()
            for k, v in perms.items():
                setattr(u, k, v)
            await db.commit()
    return uname


async def _login(ac: AsyncClient, username: str):
    r = await ac.post("/tokens", data={"username": username, "password": "supersecret1"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_ticket_title_edit_and_attachments():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        creator = await _make_user(ac, "c")
        staff = await _make_user(ac, "s", can_manage_users=True)
        other = await _make_user(ac, "o")
        ch = await _login(ac, creator)
        sh = await _login(ac, staff)
        oh = await _login(ac, other)

        # 创建工单
        r = await ac.post("/tickets", json={
            "title": "原始标题哦", "category": "consult", "content": "问题描述内容"}, headers=ch)
        assert r.status_code in (200, 201), r.text
        tid = r.json()["id"]

        # 旁观者不能改标题
        r = await ac.put(f"/tickets/{tid}/title", json={"title": "路人改标题"}, headers=oh)
        assert r.status_code == 403, r.text

        # 创建者改标题
        r = await ac.put(f"/tickets/{tid}/title", json={"title": "创建者改的新标题"}, headers=ch)
        assert r.status_code == 200, r.text

        # 标题过短 → 400
        r = await ac.put(f"/tickets/{tid}/title", json={"title": "短"}, headers=ch)
        assert r.status_code == 400, r.text

        # 标题与内容修改要留下动作记录（时间线横幅）
        r = await ac.put(f"/tickets/{tid}/description", json={"content": "更新后的问题描述"}, headers=ch)
        assert r.status_code == 200, r.text
        r = await ac.get(f"/tickets/{tid}", headers=ch)
        actions = [x["action_text"] for x in r.json()["replies"] if x["action_text"]]
        assert any(t.startswith("将标题从「原始标题哦」修改为") for t in actions), actions
        assert "修改了工单内容" in actions, actions

        # 描述附件（缺省挂到首条回复）
        r = await ac.post(f"/tickets/{tid}/attachments",
                          files={"file": (f"desc_{uuid.uuid4().hex[:4]}.txt", TXT, "text/plain")},
                          headers=ch)
        assert r.status_code == 200, r.text

        # 回复并挂附件
        r = await ac.post(f"/tickets/{tid}/replies", json={"content": "补充回复"}, headers=ch)
        assert r.status_code == 200, r.text
        reply_id = r.json()["reply_id"]
        r = await ac.post(f"/tickets/{tid}/attachments?reply_id={reply_id}",
                          files={"file": (f"reply_{uuid.uuid4().hex[:4]}.txt", TXT, "text/plain")},
                          headers=ch)
        assert r.status_code == 200, r.text
        att_id = r.json()["attachment"]["id"]

        # 禁传可执行文件
        r = await ac.post(f"/tickets/{tid}/attachments",
                          files={"file": ("evil.exe", b"MZ", "application/x-msdownload")},
                          headers=ch)
        assert r.status_code == 400, r.text

        # 详情里附件齐全
        r = await ac.get(f"/tickets/{tid}", headers=oh)
        assert r.status_code == 200, r.text
        detail = r.json()
        assert len(detail["description_attachments"]) == 1
        assert detail["replies"][0]["attachments"]
        target = next(x for x in detail["replies"] if x["id"] == reply_id)
        assert len(target["attachments"]) == 1

        # 旁观者不能删附件；管理员可以
        r = await ac.delete(f"/tickets/{tid}/attachments/{att_id}", headers=oh)
        assert r.status_code == 403, r.text
        r = await ac.delete(f"/tickets/{tid}/attachments/{att_id}", headers=sh)
        assert r.status_code == 200, r.text

        # 详情中该附件消失
        r = await ac.get(f"/tickets/{tid}", headers=oh)
        target = next(x for x in r.json()["replies"] if x["id"] == reply_id)
        assert all(a["id"] != att_id for a in target["attachments"])

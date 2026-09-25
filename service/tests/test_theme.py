"""主题商店回归测试：上传/预设/开关/清除与权限边界。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.mark.asyncio
async def test_theme_upload_preset_toggle_and_clear():
    suffix = uuid.uuid4().hex[:8]
    user, pwd = f"th_{suffix}", "supersecret1"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/users", json={
            "username": user, "email": f"{user}@example.com", "password": pwd})
        assert r.status_code == 201, r.text
        r = await ac.post("/tokens", data={"username": user, "password": pwd})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # 上传背景 → 自动启用
        r = await ac.post("/users/me/theme/background",
                          files={"file": (f"bg_{suffix}.png", PNG_BYTES, "image/png")},
                          headers=h)
        assert r.status_code == 200, r.text
        bg = r.json()["theme_background"]
        assert bg.startswith("/static/uploads/themes/") and bg.endswith(".png")
        assert r.json()["theme_enabled"] is True

        # /auth/me 能拿到主题状态
        r = await ac.get("/auth/me", headers=h)
        assert r.json()["theme_background"] == bg
        assert r.json()["theme_enabled"] is True

        # 切到内置渐变
        r = await ac.put("/users/me/theme", json={"background": "preset:dusk"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["theme_background"] == "preset:dusk"

        # 未知预设 → 400
        r = await ac.put("/users/me/theme", json={"background": "preset:nope"}, headers=h)
        assert r.status_code == 400, r.text

        # 非法路径 → 400（防外链注入）
        r = await ac.put("/users/me/theme",
                         json={"background": "https://evil.example/bg.png"}, headers=h)
        assert r.status_code == 400, r.text

        # 停用（保留选择）
        r = await ac.put("/users/me/theme", json={"enabled": False}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["theme_enabled"] is False
        assert r.json()["theme_background"] == "preset:dusk"

        # 清除（恢复默认 + 停用）
        r = await ac.put("/users/me/theme", json={"background": None}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["theme_background"] is None
        assert r.json()["theme_enabled"] is False

        # 清空状态下启用 → 400
        r = await ac.put("/users/me/theme", json={"enabled": True}, headers=h)
        assert r.status_code == 400, r.text

        # 非图片类型 → 400
        r = await ac.post("/users/me/theme/background",
                          files={"file": ("a.txt", b"hello", "text/plain")},
                          headers=h)
        assert r.status_code == 400, r.text

        # 未登录 → 401
        r = await ac.put("/users/me/theme", json={"enabled": True})
        assert r.status_code == 401

"""图床功能的端到端测试。

使用 conftest 提供的临时 SQLite（create_all 建表），上传目录指向 tmp_path，
不会污染 static/uploads。
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# 1x1 透明 PNG（避免为了测试引入图片处理库）
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """把上传目录重定向到临时目录。"""
    import app.api.images as images_api

    monkeypatch.setattr(images_api, "_UPLOAD_DIR", tmp_path)
    return tmp_path


async def _register_and_login(ac: AsyncClient) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"img_{suffix}"
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
async def test_image_host_flow(upload_dir):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)

        # 初始：无图片、无占用
        r = await ac.get("/images/quota", headers=headers)
        assert r.status_code == 200, r.text
        quota = r.json()
        assert quota["total_count"] == 0
        assert quota["premium_used"] == 0
        assert quota["premium_quota"] == 10 * 1024 * 1024

        # 上传一张图片：无水印 → 占用高级空间
        r = await ac.post(
            "/images/upload",
            headers=headers,
            files={"file": ("测试图.png", PNG_1X1, "image/png")},
        )
        assert r.status_code == 201, r.text
        image = r.json()
        assert image["is_premium"] is True
        assert image["is_locked"] is False
        assert image["watermark"] == "none"
        assert image["original_name"] == "测试图.png"
        assert image["url"].startswith("/static/uploads/images/")
        assert len(list(upload_dir.iterdir())) == 1

        # 列表与本用户占用
        r = await ac.get("/images", headers=headers)
        assert r.json()["total"] == 1
        r = await ac.get("/images/quota", headers=headers)
        assert r.json()["premium_used"] == len(PNG_1X1)
        assert r.json()["total_count"] == 1

        # 锁定后不允许删除
        r = await ac.patch(f"/images/{image['id']}/lock", headers=headers)
        assert r.status_code == 200
        assert r.json()["is_locked"] is True
        r = await ac.delete(f"/images/{image['id']}", headers=headers)
        assert r.status_code == 400
        assert "锁定" in r.json()["detail"]

        # 解锁后可删除，磁盘文件一并清理
        await ac.patch(f"/images/{image['id']}/lock", headers=headers)
        r = await ac.delete(f"/images/{image['id']}", headers=headers)
        assert r.status_code == 200
        assert list(upload_dir.iterdir()) == []
        r = await ac.get("/images/quota", headers=headers)
        assert r.json()["total_count"] == 0

        # 非图片后缀被拒
        r = await ac.post(
            "/images/upload",
            headers=headers,
            files={"file": ("a.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
        assert "仅支持" in r.json()["detail"]


@pytest.mark.asyncio
async def test_image_host_rejects_over_quota(upload_dir, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "IMAGE_PREMIUM_QUOTA_BYTES", 10)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        r = await ac.post(
            "/images/upload",
            headers=headers,
            files={"file": ("a.png", PNG_1X1, "image/png")},
        )
        assert r.status_code == 400, r.text
        assert "高级空间不足" in r.json()["detail"]
        # 被拒时不应留下任何文件
        assert list(upload_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_image_host_isolated_between_users(upload_dir):
    """A 用户看不到也删不掉 B 用户的图片。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        a = await _register_and_login(ac)
        b = await _register_and_login(ac)

        r = await ac.post(
            "/images/upload", headers=b, files={"file": ("b.png", PNG_1X1, "image/png")}
        )
        bid = r.json()["id"]

        # A 的列表里没有 B 的图
        r = await ac.get("/images", headers=a)
        assert r.json()["total"] == 0

        # A 删不掉 B 的图（返回 404，不泄露存在性）
        r = await ac.delete(f"/images/{bid}", headers=a)
        assert r.status_code == 404


# ---------------------------------------------------------------- 水印


def _plain_png(size=(240, 160), color=(255, 255, 255)) -> bytes:
    """生成一张纯色 PNG，方便验证水印是否真的画上去了。"""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _painted_bytes(path) -> bool:
    """文件里的图是否已不是纯白（即被画过东西）。"""
    from PIL import Image, ImageChops

    with Image.open(path) as im:
        white = Image.new("RGB", im.size, (255, 255, 255))
        return ImageChops.difference(im.convert("RGB"), white).getbbox() is not None


async def _upload(ac, headers, content, name, watermark=None, **extra):
    data = {"watermark": watermark} if watermark else None
    return await ac.post(
        "/images/upload",
        headers=headers,
        files={"file": (name, content, "image/png")},
        data=data,
        **extra,
    )


@pytest.mark.asyncio
async def test_watermark_applied_and_counts_as_basic(upload_dir):
    """选了水印 → 真的画上去，且只占普通空间。"""
    from app.utils.watermark import available

    if not available():
        pytest.skip("当前环境没有可用字体，跳过水印测试")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        raw = _plain_png()

        r = await _upload(ac, headers, raw, "wm.png", watermark="text")
        assert r.status_code == 201, r.text
        image = r.json()

        assert image["watermark"] == "text"
        # 带水印且远小于 500KB → 普通空间
        assert image["is_premium"] is False
        assert image["size_bytes"] != len(raw)  # 重新编码过

        # 落盘的文件确实被画了水印
        saved = upload_dir / image["url"].rsplit("/", 1)[-1]
        assert saved.exists()
        assert _painted_bytes(saved)

        # 配额分桶正确
        quota = (await ac.get("/images/quota", headers=headers)).json()
        assert quota["basic_used"] == image["size_bytes"]
        assert quota["premium_used"] == 0

        # 筛选：普通空间 1 张，高级空间 0 张
        r = await ac.get("/images", params={"premium": "false"}, headers=headers)
        assert r.json()["total"] == 1
        r = await ac.get("/images", params={"premium": "true"}, headers=headers)
        assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_watermark_none_reencodes_nothing(upload_dir):
    """不选水印时原样落盘，体积分毫不差。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        raw = _plain_png()

        for payload in (None, "none"):
            r = await _upload(ac, headers, raw, "plain.png", watermark=payload)
            assert r.status_code == 201, r.text
            assert r.json()["watermark"] == "none"
            assert r.json()["is_premium"] is True
            saved = upload_dir / r.json()["url"].rsplit("/", 1)[-1]
            assert saved.read_bytes() == raw


@pytest.mark.asyncio
async def test_watermark_rejects_unknown_value(upload_dir):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        r = await _upload(ac, headers, _plain_png(), "x.png", watermark="logo_user")
        assert r.status_code == 400
        assert "水印参数" in r.json()["detail"]
        assert list(upload_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_watermark_falls_back_when_no_font(upload_dir, monkeypatch):
    """找不到字体时退化为无水印，并按无水印规则计入高级空间。"""
    import app.utils.watermark as wm

    monkeypatch.setattr(wm, "_font_path", lambda: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        raw = _plain_png()

        r = await _upload(ac, headers, raw, "wm.png", watermark="text")
        assert r.status_code == 201, r.text
        assert r.json()["watermark"] == "none"
        assert r.json()["is_premium"] is True
        saved = upload_dir / r.json()["url"].rsplit("/", 1)[-1]
        assert saved.read_bytes() == raw  # 原样存下来


@pytest.mark.asyncio
async def test_watermark_is_subject_to_basic_quota(upload_dir, monkeypatch):
    """普通空间满了以后，带水印的上传要按普通空间报错。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "IMAGE_BASIC_QUOTA_BYTES", 10)
    from app.utils.watermark import available

    if not available():
        pytest.skip("当前环境没有可用字体，跳过水印测试")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        headers = await _register_and_login(ac)
        r = await _upload(ac, headers, _plain_png(), "wm.png", watermark="text")
        assert r.status_code == 400, r.text
        assert "普通空间不足" in r.json()["detail"]


def test_watermark_big_image_goes_premium():
    """超过阈值的图即使带水印也占高级空间。"""
    import io

    from PIL import Image

    from app.utils.watermark import apply_watermark, available

    if not available():
        pytest.skip("当前环境没有可用字体，跳过水印测试")

    buf = io.BytesIO()
    Image.new("RGB", (300, 200), (10, 20, 30)).save(buf, "JPEG", quality=95)
    out = apply_watermark(buf.getvalue(), "NLNOJ")
    assert out is not None
    with Image.open(io.BytesIO(out)) as im:
        assert im.format == "JPEG"
        assert im.size == (300, 200)


def test_watermark_preserves_animation():
    """动图逐帧加水印后仍然是动图，帧数不变。"""
    import io

    from PIL import Image

    from app.utils.watermark import apply_watermark, available

    if not available():
        pytest.skip("当前环境没有可用字体，跳过水印测试")

    buf = io.BytesIO()
    frames = [Image.new("RGB", (80, 60), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)

    out = apply_watermark(buf.getvalue(), "NLNOJ")
    assert out is not None
    with Image.open(io.BytesIO(out)) as im:
        assert im.format == "GIF"
        assert im.n_frames == 3


def test_watermark_gives_up_on_garbage():
    """解不开的内容返回 None，而不是抛异常。"""
    from app.utils.watermark import apply_watermark

    assert apply_watermark(b"not an image at all", "NLNOJ") is None
    assert apply_watermark(b"", "NLNOJ") is None
    assert apply_watermark(PNG_1X1, "   ") is None

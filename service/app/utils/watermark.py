"""图床水印 —— 把站点名斜向平铺盖在图上。

参照洛谷的做法：水印不是 logo，就是站点名那几个字，
所以这里也只画文字、不依赖任何图片素材（省得维护一张 logo 图）。

字体查找顺序：
  1. 配置项 ``IMAGE_WATERMARK_FONT`` 指定的字体文件
  2. 项目自带 ``static/fonts/`` 目录下的第一个字体
  3. 系统常见字体（Docker 镜像里装的是 fonts-wqy-microhei）

设计原则：**水印失败绝不能让上传失败**。任何环节出问题（没装 Pillow、
找不到字体、图片解不开、帧数过多、像素过大）都返回 ``None``，
调用方按「无水印」处理 —— 无水印按规则占用高级空间，不会让用户白蹭配额。
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:  # pragma: no cover - 仅为类型标注，运行时不需要 Pillow
    from PIL import Image as PILImage
    from PIL.ImageFont import FreeTypeFont

logger = logging.getLogger(__name__)

# 可叠加水印的格式（与 api/images.py 的 _ALLOWED_EXT 对应）
_SUPPORTED_FORMATS = ("PNG", "JPEG", "WEBP", "GIF")

# 水印文字旋转角度（度）
ANGLE = -30
# 平铺间距 = 平铺块宽/高 × 系数
GAP_RATIO = 0.6
# 字号 = 图片短边 × 系数
FONT_RATIO = 1 / 12
MIN_FONT_SIZE = 14
MAX_FONT_SIZE = 72
# 动图帧数 / 像素数上限，超了就跳过水印，避免把内存打爆
MAX_FRAMES = 120
MAX_PIXELS = 40_000_000

# 系统字体候选（按优先级）
_FONT_CANDIDATES = (
    # Debian/Ubuntu: fonts-wqy-microhei
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    # Noto CJK
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    # 纯西文字体兜底（站点名是 ASCII 时够用）
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # 开发机（macOS / Windows）
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msyh.ttc",
)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _pillow():
    """延迟导入 Pillow，未安装时让调用方自己处理。"""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    return Image, ImageDraw, ImageFont


def _font_path() -> Path | None:
    """按优先级找第一个可用的字体文件。"""
    configured = (settings.IMAGE_WATERMARK_FONT or "").strip()
    if configured:
        path = Path(configured)
        if path.is_file():
            return path
        logger.warning("IMAGE_WATERMARK_FONT 指向的文件不存在：%s", path)

    bundled_dir = _BASE_DIR / "static" / "fonts"
    if bundled_dir.is_dir():
        bundled = sorted(
            p for p in bundled_dir.iterdir() if p.suffix.lower() in {".ttf", ".ttc", ".otf"}
        )
        if bundled:
            return bundled[0]

    for candidate in _FONT_CANDIDATES:
        if Path(candidate).is_file():
            return Path(candidate)
    return None


@lru_cache(maxsize=32)
def _load_font(path: str, size: int) -> "FreeTypeFont":
    _, _, ImageFont = _pillow()
    return ImageFont.truetype(path, size)


def available() -> bool:
    """当前环境能否生成水印（没装 Pillow 或没字体时为 False）。"""
    try:
        _pillow()
    except ImportError:
        return False
    return _font_path() is not None


def _font_size(short_side: int) -> int:
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(short_side * FONT_RATIO)))


def _make_tile(text: str, font: "FreeTypeFont") -> "PILImage.Image":
    """把水印文字画到一个带留白的透明块上，再整体旋转。"""
    Image, ImageDraw, _ = _pillow()

    bbox = font.getbbox(text)
    text_w = max(1, bbox[2] - bbox[0])
    text_h = max(1, bbox[3] - bbox[1])
    pad = max(10, font.size // 2)

    tile = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    draw.text(
        (pad - bbox[0], pad - bbox[1]),
        text,
        font=font,
        # 白色字 + 半透明黑描边：浅色底靠描边、深色底靠白字，两边都看得见
        fill=(255, 255, 255, settings.IMAGE_WATERMARK_OPACITY),
        stroke_width=max(1, font.size // 16),
        stroke_fill=(0, 0, 0, settings.IMAGE_WATERMARK_OPACITY // 2),
    )
    return tile.rotate(ANGLE, expand=True, resample=Image.BICUBIC)


def _stamp(frame: "PILImage.Image", tile: "PILImage.Image") -> "PILImage.Image":
    """把水印块平铺到单帧上。"""
    Image, _, _ = _pillow()

    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    step_x = max(1, int(tile.width * (1 + GAP_RATIO)))
    step_y = max(1, int(tile.height * (1 + GAP_RATIO)))
    for y in range(-tile.height // 2, frame.height + step_y, step_y):
        for x in range(-tile.width // 2, frame.width + step_x, step_x):
            layer.alpha_composite(tile, (x, y))
    return Image.alpha_composite(frame, layer)


def _load_frames(im: "PILImage.Image") -> list["PILImage.Image"] | None:
    """取出所有帧（统一转 RGBA）。帧数过多时返回 None。"""
    from PIL import ImageOps, ImageSequence  # noqa: PLC0415

    n_frames = getattr(im, "n_frames", 1)
    if n_frames > MAX_FRAMES:
        logger.warning("动图 %d 帧，超过上限 %d，跳过水印", n_frames, MAX_FRAMES)
        return None
    return [ImageOps.exif_transpose(frame).convert("RGBA") for frame in ImageSequence.Iterator(im)]


def _encode(frames: list["PILImage.Image"], fmt: str, info: dict) -> bytes:
    """把加了水印的帧重新编码。"""
    Image, _, _ = _pillow()

    head, tail = frames[0], frames[1:]
    buf = io.BytesIO()

    if fmt == "JPEG":
        head.convert("RGB").save(buf, "JPEG", quality=95, optimize=True, progressive=True)
    elif fmt == "PNG":
        head.save(buf, "PNG", optimize=True)
    elif fmt == "WEBP":
        if tail:
            head.save(
                buf,
                "WEBP",
                save_all=True,
                append_images=[f.convert("RGB") for f in tail],
                quality=95,
                duration=info.get("duration", 100),
                loop=info.get("loop", 0),
            )
        else:
            head.save(buf, "WEBP", quality=95)
    elif fmt == "GIF":
        if tail:
            head.save(
                buf,
                "GIF",
                save_all=True,
                append_images=tail,
                duration=info.get("duration", 100),
                loop=info.get("loop", 0),
                disposal=2,
            )
        else:
            head.save(buf, "GIF", disposal=2)
    else:  # pragma: no cover - 上游已按格式白名单拦过
        raise ValueError(f"不支持的格式：{fmt}")

    return buf.getvalue()


def apply_watermark(content: bytes, text: str) -> bytes | None:
    """给图片叠加平铺文字水印。

    Args:
        content: 原始图片字节。
        text: 水印文字（一般为站点名）。

    Returns:
        加水印后的字节；任何原因失败都返回 ``None``（调用方按无水印处理）。
    """
    if not text.strip():
        return None

    try:
        Image, _, _ = _pillow()
    except ImportError:
        logger.error("未安装 Pillow，无法生成水印（请执行 uv sync）")
        return None

    font_path = _font_path()
    if font_path is None:
        logger.error("找不到可用字体，无法生成水印；请在镜像内安装 fonts-wqy-microhei")
        return None

    try:
        with Image.open(io.BytesIO(content)) as im:
            fmt = (im.format or "").upper()
            if fmt not in _SUPPORTED_FORMATS:
                logger.warning("格式 %s 不支持水印，跳过", fmt)
                return None

            width, height = im.size
            if width * height > MAX_PIXELS:
                logger.warning("图片 %dx%d 过大，跳过水印", width, height)
                return None

            info = {k: im.info.get(k) for k in ("duration", "loop") if k in im.info}
            frames = _load_frames(im)
            if frames is None:
                return None

            font = _load_font(str(font_path), _font_size(min(width, height)))
            tile = _make_tile(text.strip(), font)
            stamped = [_stamp(frame, tile) for frame in frames]
            return _encode(stamped, fmt, info)

    except Exception:  # noqa: BLE001 - 水印只是锦上添花，绝不能影响上传
        logger.exception("水印生成失败，本次上传按无水印处理")
        return None

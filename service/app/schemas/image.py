"""图床的 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageItem(BaseModel):
    """单张图片的信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    original_name: str | None = None
    size_bytes: int
    content_type: str | None = None
    # none = 无水印 / text = 站点文字水印
    watermark: str = "none"
    is_premium: bool
    is_locked: bool
    created_at: datetime


class ImageListResponse(BaseModel):
    items: list[ImageItem]
    total: int
    page: int
    page_size: int


class ImageQuotaResponse(BaseModel):
    """空间占用情况（前端进度条用）。"""

    total_count: int
    premium_used: int
    premium_quota: int
    basic_used: int
    basic_quota: int
    # 超过该体积的图片强制占用高级空间（前端提示用）
    premium_threshold: int

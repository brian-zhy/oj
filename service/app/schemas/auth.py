"""认证相关 Pydantic 模型（令牌响应、刷新请求）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str = Field(description="访问令牌（短期，置于 Authorization: Bearer 头）")
    refresh_token: str = Field(description="刷新令牌（长期，用于换取新令牌）")
    token_type: Literal["bearer"] = Field(default="bearer", description="令牌类型")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(description="此前签发的刷新令牌")

"""犇犇相关的数据模式。"""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BenbenCreate(BaseModel):
    """创建犇犇的请求模式"""
    content: str = Field(..., min_length=1, max_length=5000, description="犇犇内容")
    reply_to: Optional[int] = Field(None, description="回复的犇犇ID")


class BenbenResponse(BaseModel):
    """犇犇响应模式"""
    id: int
    user_number: int
    username: str
    avatar_url: Optional[str] = None
    is_admin: bool = False
    is_cheater: bool = False
    username_color: Optional[str] = None
    user_tag: Optional[str] = None
    content: str
    reply_to: Optional[int] = None
    reply_to_username: Optional[str] = None
    created_at: datetime
    is_owner: bool = False

    class Config:
        from_attributes = True
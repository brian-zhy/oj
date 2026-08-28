"""工单系统 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field

# 类别
TICKET_CATEGORIES = {
    "consult": "一般咨询",
    "suggestion": "建议反馈",
    "bug": "Bug反馈",
    "appeal": "账号申诉",
}

# 状态
TICKET_STATUSES = {
    "pending": "待处理",
    "replied": "待补充",
    "processing": "处理中",
    "suspended": "挂起",
    "resolved": "已完成",
    "closed": "已关闭",
    "deleted": "已删除",
}


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100, description="标题（一事一单，明确具体）")
    category: str = Field(pattern="^(consult|suggestion|bug|appeal)$")
    content: str = Field(min_length=5, max_length=5000)


class TicketReplyCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class TicketStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|replied|processing|suspended|resolved|closed|deleted)$")


class TicketOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    category: str
    status: str
    creator_id: int
    is_public: bool
    last_reply_at: str | None = None
    last_reply_by: str | None = None
    created_at: str
    updated_at: str


class TicketReplyOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    ticket_id: int
    user_id: int
    content: str
    is_staff: bool
    created_at: str

"""站内通知的统一写入与 @提及 解析。

@提及 的语义：**被 @ 只代表「提及」，不等于被回复**，所以单开
type='mention'，与 type='reply'（你的帖子/工单被回复）分开，
前端据此分「@我的」「回复我的」两个标签页。

提及是靠解析正文里的 @username 得到的，不依赖编辑器传结构化数据 ——
这样「回复某条回复」只要在正文里 @ 一下对方就能生效（扁平结构，不做树状）。
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User

# 用户名规则见 schemas/user.py：^[A-Za-z0-9_]{3,50}$
# 前面不能是单词字符、点或斜杠：
#   - 单词字符/点：避开邮箱（a@b.com）
#   - 斜杠：避开链接路径（https://x.com/@foo）
# 前端 utils/markdown.ts 用的是同一条规则，两边要保持一致
MENTION_RE = re.compile(r"(?<![\w./])@([A-Za-z0-9_]{3,50})")

CONTENT_MAX = 200
TITLE_MAX = 40


def clip(text: str, limit: int = CONTENT_MAX) -> str:
    """db 列是 String(200)，标题过长的帖子会让通知写入失败。"""
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def extract_mentions(content: str | None) -> list[str]:
    """按出现顺序去重提取被 @ 的用户名。"""
    seen: set[str] = set()
    result: list[str] = []
    for name in MENTION_RE.findall(content or ""):
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def add_notification(
    db: AsyncSession,
    *,
    user_id: int,
    ntype: str,
    content: str,
    actor_id: int | None = None,
    link: str | None = None,
    ticket_id: int | None = None,
    force: bool = False,
) -> bool:
    """写入一条通知。默认不给自己发；force=True 时强制（如指派给自己）。

    返回是否真的写入了（调用方需要计数时用）。
    """
    if actor_id is not None and user_id == actor_id and not force:
        return False
    db.add(Notification(
        user_id=user_id,
        type=ntype,
        content=clip(content),
        actor_id=actor_id,
        link=link,
        ticket_id=ticket_id,
    ))
    return True


async def notify_mentions(
    db: AsyncSession,
    content: str | None,
    *,
    actor: User,
    link: str,
    where: str,
) -> list[str]:
    """给正文里被 @ 的人发「提及」通知，返回实际被通知的用户名。

    where 是场景描述，如「帖子「复活」」「犇犇」「工单「登录不上」」，
    拼出的文案与站点原有风格一致：@xxx 在帖子「复活」中提到了你，快去看看吧。
    """
    names = extract_mentions(content)
    if not names:
        return []

    users = (await db.execute(
        select(User).where(User.username.in_(names))
    )).scalars().all()

    notified: list[str] = []
    for user in users:
        # 自己 @ 自己不发通知，也不给被封禁/停用的账号发
        if user.id == actor.id or user.is_banned or not user.is_active:
            continue
        add_notification(
            db,
            user_id=user.id,
            ntype="mention",
            content=f"@{actor.username} 在{where}中提到了你，快去看看吧",
            actor_id=actor.id,
            link=link,
        )
        notified.append(user.username)
    return notified

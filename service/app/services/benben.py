"""犇犇业务逻辑服务。"""

from __future__ import annotations

import re
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.benben import Benben
from app.models.user import User
from app.schemas.benben import BenbenCreate, BenbenResponse


class BenbenService:
    """犇犇业务服务"""

    MAX_LENGTH_NORMAL = 500  # 普通用户最大字数
    MAX_LENGTH_ADMIN = 5000  # 管理员最大字数

    @staticmethod
    async def create_benben(
        db: AsyncSession,
        user_number: int,
        content: str,
        reply_to: Optional[int] = None,
        is_admin: bool = False
    ) -> Benben:
        """创建新的犇犇"""
        # 检查用户权限
        user = await db.execute(
            select(User).where(User.user_number == user_number)
        )
        user_obj = user.scalar_one_or_none()

        if not user_obj:
            raise ValueError("用户不存在")

        if user_obj.can_speak is False:
            raise PermissionError("你已被禁言，无法发布动态")

        # 字数限制
        max_length = BenbenService.MAX_LENGTH_ADMIN if is_admin else BenbenService.MAX_LENGTH_NORMAL
        if len(content) > max_length:
            content = content[:max_length]

        # 如果是回复，检查原犇犇是否存在
        if reply_to:
            original = await db.execute(
                select(Benben).where(Benben.id == reply_to)
            )
            if not original.scalar_one_or_none():
                raise ValueError("回复的犇犇不存在")

        # 创建犇犇
        benben = Benben(
            user_number=user_number,
            content=content,
            reply_to=reply_to
        )
        db.add(benben)
        await db.commit()
        await db.refresh(benben)

        return benben

    @staticmethod
    async def get_benben_list(
        db: AsyncSession,
        limit: int = 20,
        before_id: Optional[int] = None,
        mode: str = "all",
        user_number: Optional[int] = None
    ) -> list[Benben]:
        """获取犇犇列表"""
        query = select(Benben).options(selectinload(Benben.user)).order_by(desc(Benben.created_at))

        # 分页查询
        if before_id:
            query = query.where(Benben.id < before_id)

        # 只看自己的动态
        if mode == "my" and user_number:
            query = query.where(Benben.user_number == user_number)

        query = query.limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_benben(
        db: AsyncSession,
        benben_id: int,
        user_number: int,
        is_admin: bool = False
    ) -> bool:
        """删除犇犇"""
        # 查询犇犇
        result = await db.execute(
            select(Benben).where(Benben.id == benben_id)
        )
        benben = result.scalar_one_or_none()

        if not benben:
            raise ValueError("犇犇不存在")

        # 权限检查：只有作者或管理员可以删除
        if not is_admin and benben.user_number != user_number:
            raise PermissionError("你无权删除这条动态")

        await db.delete(benben)
        await db.commit()

        return True

    @staticmethod
    async def process_mentions(content: str) -> list[str]:
        """提取@提及的用户名"""
        pattern = r'@([一-龥a-zA-Z0-9_.-]+)'
        matches = re.findall(pattern, content)
        # 去重
        return list(set(matches))

    @staticmethod
    def enrich_benben_with_user_info(benben_list: list[Benben], current_user_number: Optional[int] = None) -> list[dict]:
        """为犇犇添加用户信息"""
        result = []
        for benben in benben_list:
            # 获取用户信息
            user = benben.user
            username = user.username if user else '未知用户'

            # 构建响应数据
            benben_dict = {
                "id": benben.id,
                "user_number": benben.user_number,
                "content": benben.content,
                "reply_to": benben.reply_to,
                "created_at": benben.created_at,
                "username": username,
                "avatar_url": user.avatar_url if user else None,
                "is_admin": user.is_admin if user else False,
                "is_cheater": user.is_cheater if user else False,
                "username_color": user.username_color if user else None,
                "user_tag": user.user_tag if user else None,
                "is_owner": current_user_number == benben.user_number if current_user_number else False
            }

            # 添加回复信息
            if benben.reply_to:
                # 这里可以查询被回复的犇犇信息，暂时设为None
                benben_dict["reply_to_username"] = None

            result.append(benben_dict)

        return result


# 服务实例
benben_service = BenbenService()
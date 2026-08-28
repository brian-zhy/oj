"""创建超级管理员用户脚本"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.security import hash_password
from app.models.user import User
from app.models.base import Base
from dotenv import load_dotenv
import os

async def create_super_admin():
    """创建超级管理员用户"""

    # 加载环境变量
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误: DATABASE_URL 环境变量未设置")
        sys.exit(1)

    print(f"连接数据库: {database_url[:50]}...")

    # 创建数据库引擎
    engine = create_async_engine(database_url, echo=True)

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建会话
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # 检查用户是否已存在
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.username == "Jason227")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("用户 Jason227 已存在，升级为超级管理员...")
            existing_user.is_super_admin = True
            existing_user.is_admin = True
            existing_user.is_banned = False
            existing_user.is_active = True
            existing_user.can_manage_users = True
            existing_user.can_manage_posts = True
            existing_user.can_assign_admin = True
            existing_user.can_speak = True

            # 如果密码需要更新
            # existing_user.hashed_password = hash_password("123456")

            await session.commit()
            print("用户已升级为超级管理员!")

        else:
            print("创建新的超级管理员用户...")

            # 获取下一个用户编号
            result = await session.execute(select(User.id))
            existing_users = result.scalars().all()
            user_number = len(existing_users) + 1

            # 创建超级管理员用户
            super_admin = User(
                username="Jason227",
                email="jason227@superadmin.com",
                hashed_password=hash_password("123456"),
                user_number=user_number,
                phone=None,

                # 状态设置
                is_active=True,
                is_banned=False,
                is_cheater=False,

                # 管理员权限
                is_super_admin=True,  # 超级管理员标识
                is_admin=True,       # 管理员标识
                can_speak=True,      # 可以发言
                can_manage_users=True,  # 可以管理用户
                can_manage_posts=True,  # 可以管理帖子
                can_assign_admin=True,  # 可以指定管理员

                # 个性化信息
                avatar_url=None,
                user_tag="超级管理员",
                username_color="#FF0000",
                bio="系统超级管理员，拥有最高权限"
            )

            session.add(super_admin)
            await session.commit()
            await session.refresh(super_admin)

            print(f"超级管理员用户创建成功!")
            print(f"用户ID: {super_admin.id}")
            print(f"用户名: {super_admin.username}")
            print(f"邮箱: {super_admin.email}")
            print(f"用户编号: {super_admin.user_number}")
            print(f"超级管理员权限: {super_admin.is_super_admin}")

    await engine.dispose()

if __name__ == "__main__":
    print("开始创建超级管理员用户...")
    asyncio.run(create_super_admin())
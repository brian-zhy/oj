#!/usr/bin/env python3
"""详细的登录调试 - 逐步测试每个环节"""

import sys
import asyncio
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_db
from app.services.extended_auth import get_email_by_identifier
from app.services import auth as auth_service
from app.models.user import User
from sqlalchemy import select


async def test_login_steps():
    """逐步测试登录流程"""

    print("=== 开始逐步测试登录流程 ===\n")

    # 获取数据库会话
    async for db in get_db():
        try:
            # 测试用户标识符
            identifier = "brian_zheng"
            test_password = "test123"  # 替换为你的实际密码

            print(f"1️⃣ 测试标识符: {identifier}")

            # 步骤1: 获取邮箱
            print("2️⃣ 调用 get_email_by_identifier...")
            try:
                email = await get_email_by_identifier(db, identifier)
                print(f"   ✅ 获取到邮箱: {email}")
            except Exception as e:
                print(f"   ❌ get_email_by_identifier 失败: {e}")
                import traceback
                traceback.print_exc()
                return

            if not email:
                print(f"   ❌ 未找到用户: {identifier}")
                return

            # 步骤2: 验证用户凭据
            print(f"3️⃣ 调用 authenticate_user (邮箱: {email})...")
            try:
                user = await auth_service.authenticate_user(db, email, test_password)
                if user:
                    print(f"   ✅ 用户认证成功: {user.username}")
                else:
                    print(f"   ❌ 用户认证失败 - 用户名或密码错误")
                    print(f"   提示: 请将脚本中的 test_password 替换为你的实际密码")
                    return
            except Exception as e:
                print(f"   ❌ authenticate_user 异常: {e}")
                import traceback
                traceback.print_exc()
                return

            # 步骤3: 检查封禁状态
            print("4️⃣ 检查用户封禁状态...")
            try:
                from app.services.extended_auth import check_user_banned
                is_banned = await check_user_banned(db, user.id)
                if is_banned:
                    print(f"   ❌ 用户已被封禁")
                    return
                else:
                    print(f"   ✅ 用户未被封禁")
            except Exception as e:
                print(f"   ❌ check_user_banned 异常: {e}")
                import traceback
                traceback.print_exc()
                return

            # 步骤4: 签发令牌
            print("5️⃣ 签发访问令牌和刷新令牌...")
            try:
                access, refresh = await auth_service.issue_token_pair(db, user.id)
                print(f"   ✅ 令牌签发成功")
                print(f"   Access Token (前50字符): {access[:50]}...")
                print(f"   Refresh Token (前50字符): {refresh[:50]}...")

                print(f"\n✅✅✅ 登录流程完全成功！✅✅✅")

            except Exception as e:
                print(f"   ❌ issue_token_pair 异常: {e}")
                import traceback
                traceback.print_exc()
                return

        finally:
            break


if __name__ == "__main__":
    print("提示: 请将脚本中的 test_password 变量改为你的实际密码")
    print("运行: uv run python debug_login_detailed.py\n")
    asyncio.run(test_login_steps())
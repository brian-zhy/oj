"""手动创建用户脚本（给运维/管理员用，绕过注册接口的邮箱验证流程）。

用法：
    uv run python scripts/create_user.py <用户名> <手机号> <密码> [邮箱]

邮箱缺省时自动生成占位地址（<用户名>@placeholder.local），之后可在
管理后台修改。用户编号（UID）按最小未占用号自动分配。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.services.extended_auth import create_user_with_number


async def main() -> None:
    if len(sys.argv) < 4:
        print("用法: uv run python scripts/create_user.py <用户名> <手机号> <密码> [邮箱]")
        sys.exit(1)
    username, phone, password = sys.argv[1:4]
    email = sys.argv[4] if len(sys.argv) > 4 else f"{username}@placeholder.local"

    async with AsyncSessionLocal() as db:
        for field, value in (("username", username), ("phone", phone), ("email", email)):
            exists = (await db.execute(
                select(User.id).where(getattr(User, field) == value)
            )).scalar_one_or_none()
            if exists is not None:
                print(f"创建失败：{field} {value} 已存在（用户 id={exists}）")
                sys.exit(1)

        user = await create_user_with_number(
            db, username, email, hash_password(password), phone=phone,
        )
        print("用户创建成功")
        print(f"  用户名: {user.username}")
        print(f"  UID: {user.user_number}")
        print(f"  手机号: {user.phone}")
        print(f"  邮箱: {user.email}")


if __name__ == "__main__":
    asyncio.run(main())

"""按 UID（user_number）授予用户全套管理权限（与 add_super_admin.py 同款）。

用法：
    uv run python scripts/grant_admin.py <UID>
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User

# 全套管理权限（与 add_super_admin.py 升级分支一致）
ADMIN_FIELDS = [
    "is_super_admin", "is_admin", "can_speak",
    "can_manage_users", "can_manage_posts", "can_manage_problems",
    "can_assign_admin", "can_manage_tags",
]


async def main() -> None:
    if len(sys.argv) < 2:
        print("用法: uv run python scripts/grant_admin.py <UID>")
        sys.exit(1)
    uid = int(sys.argv[1])

    async with AsyncSessionLocal() as db:
        user = (await db.execute(
            select(User).where(User.user_number == uid)
        )).scalar_one_or_none()
        if user is None:
            print(f"操作失败：UID {uid} 不存在")
            sys.exit(1)

        for field in ADMIN_FIELDS:
            setattr(user, field, True)
        # 管理员不该是封禁/停用状态
        user.is_active = True
        user.is_banned = False
        await db.commit()

        print(f"UID {uid}（{user.username}）已授予全套管理权限")
        for field in ADMIN_FIELDS:
            print(f"  {field} = True")


if __name__ == "__main__":
    asyncio.run(main())

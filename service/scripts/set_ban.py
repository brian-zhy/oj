"""按 UID（user_number）设置用户封禁状态，绕过管理后台直接操作数据库。

用法：
    uv run python scripts/set_ban.py <UID> unban   # 解封
    uv run python scripts/set_ban.py <UID> ban     # 封禁（同时吊销其全部刷新令牌，立即踢下线）
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth import revoke_user_tokens


async def main() -> None:
    if len(sys.argv) < 3 or sys.argv[2] not in ("ban", "unban"):
        print("用法: uv run python scripts/set_ban.py <UID> ban|unban")
        sys.exit(1)
    uid = int(sys.argv[1])
    ban = sys.argv[2] == "ban"

    async with AsyncSessionLocal() as db:
        user = (await db.execute(
            select(User).where(User.user_number == uid)
        )).scalar_one_or_none()
        if user is None:
            print(f"操作失败：UID {uid} 不存在")
            sys.exit(1)

        user.is_banned = ban
        await db.commit()
        print(f"UID {uid}（{user.username}）已{'封禁' if ban else '解封'}")

        if ban:
            # 与管理后台一致：封禁即吊销全部刷新令牌，现有会话下一请求失效
            n = await revoke_user_tokens(db, user.id)
            print(f"已吊销 {n} 个刷新令牌（在线会话立即失效）")


if __name__ == "__main__":
    asyncio.run(main())

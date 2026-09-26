"""一次性:回填贡献值 dry-run 预览。用完即删。"""

import asyncio
import re
from collections import defaultdict

import asyncpg


def load_env(path: str) -> dict:
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v.strip()
    return env

# 与 service/app/services/judge.py 的 CONTRIBUTION_BY_DIFFICULTY 一致
CONTRIB = {
    "入门": 5, "普及-": 25, "普及": 50, "普及+/提高": 500,
    "提高": 1000, "提高+/省选-": 2500, "省选/NOI-": 4500,
    "NOI/NOI+/CTSC": 7500, "暂无评定": 0,
}


async def main() -> None:
    env = load_env(".env")
    pg = re.sub(r"^postgresql\+asyncpg", "postgresql", env["DATABASE_URL"])
    conn = await asyncpg.connect(pg, ssl="require")

    rows = await conn.fetch(
        "SELECT author_id, difficulty, count(*) AS n FROM problems "
        "WHERE team_id IS NULL AND author_id IS NOT NULL "
        "GROUP BY author_id, difficulty")
    per_user: dict[int, int] = defaultdict(int)
    total_problems = 0
    for r in rows:
        pts = CONTRIB.get(r["difficulty"], 0) * r["n"]
        per_user[r["author_id"]] += pts
        total_problems += r["n"]

    users = await conn.fetch(
        "SELECT id, username FROM users WHERE id = ANY($1::int[])",
        list(per_user.keys()))
    name_of = {u["id"]: u["username"] for u in users}

    nonzero = await conn.fetchval(
        "SELECT count(*) FROM users WHERE contribution <> 0")

    print(f"有出题人的主题库题: {total_problems} 道,涉及 {len(per_user)} 人")
    print(f"当前 contribution 非 0 的用户: {nonzero} 人")
    print("\n回填预览(按当前题目归属):")
    for uid, pts in sorted(per_user.items(), key=lambda x: -x[1]):
        print(f"  {name_of.get(uid, uid)}(id={uid}): +{pts}")
    await conn.close()


asyncio.run(main())

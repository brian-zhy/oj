"""测试全局配置：隔离数据库，避免测试读写真实 DATABASE_URL 指向的库。

必须在任何 app 模块导入之前改写环境变量（conftest 先于测试模块收集执行）。
测试库用临时 SQLite 文件，session 开始前 create_all，结束后删除。
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_test.db"
os.environ["ENV"] = "dev"

import asyncio  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    from app.core.database import engine
    from app.models.base import Base

    async def _create():
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)

    asyncio.run(_create())
    yield
    asyncio.run(engine.dispose())

    import contextlib

    with contextlib.suppress(OSError):
        os.remove("./_test.db")

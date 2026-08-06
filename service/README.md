# OJ Service

Online judge 后端服务，基于 [FastAPI](https://fastapi.tiangolo.com/)，使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

## 功能

- 用户认证：注册 / 登录（签发 token）/ 刷新（轮换）/ 获取当前用户
- JWT（access + refresh 双 token），refresh token 存库可吊销、用一次即轮换
- 登录支持用户名或邮箱
- **本地用 SQLite 零配置开发/测试，生产用 PostgreSQL**（同一套 Alembic 迁移）

## API（REST 资源式）

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| POST | `/users` | 创建用户（注册），返回用户信息（201） | 否 |
| GET  | `/users/me` | 返回当前用户 | 是（Bearer） |
| POST | `/tokens` | 用凭据创建 token 对（登录）；`username` 可填邮箱 | 否 |
| POST | `/tokens/refresh` | 用 refresh token 换新一对，旧 refresh 作废 | 否 |

交互式文档：http://127.0.0.1:8000/docs （用 Authorize 按钮登录后即可调试受保护接口，token 端点为 `/tokens`）。

## 目录结构

```
service/
├── app/
│   ├── main.py              # FastAPI 应用入口、CORS、挂载路由
│   ├── deps.py              # get_current_user / get_current_active_user
│   ├── core/
│   │   ├── config.py        # pydantic-settings 配置（读 .env）
│   │   ├── database.py      # async engine / session / get_db（SQLite/PG 自适应）
│   │   └── security.py      # bcrypt 密码哈希 + JWT 编解码
│   ├── models/              # User、RefreshToken（SQLAlchemy 2.x）
│   ├── schemas/             # 请求/响应 Pydantic 模型
│   ├── services/            # 用户 CRUD + 认证流程
│   └── api/                 # users.py / tokens.py 资源路由 + 聚合 router
├── alembic/                 # 迁移脚本（env.py 异步、SQLite/PG 通用）
├── alembic.ini
├── tests/                   # 冒烟测试
├── .env.example             # 生产配置模板（本地开发无需）
└── pyproject.toml
```

## 快速开始（本地，SQLite）

本地开发**无需** Postgres，也无需 `.env`——默认用当前目录下的 SQLite 文件：

```bash
uv sync                                       # 装依赖
uv run python -m alembic upgrade head         # 在 SQLite 上建表（生成 oj.db）
uv run uvicorn app.main:app --reload          # 启动开发服务器
```

> 注：本机应用控制策略会拦截 `.venv` 里的 `alembic.exe`、`pytest.exe` 等控制台脚本
> （报 os error 4551）。用 `uv run python -m alembic ...` / `uv run python -m pytest` 即可绕过。

示例：

```bash
# 注册（创建用户）
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"supersecret1"}'

# 登录（创建 token，表单）
curl -X POST http://127.0.0.1:8000/tokens -d "username=alice&password=supersecret1"

# 受保护接口
curl http://127.0.0.1:8000/users/me -H "Authorization: Bearer <access_token>"
```

## 切换到 PostgreSQL（生产）

```bash
cp .env.example .env
# 编辑 .env，设置 DATABASE_URL 为 PostgreSQL，并填 JWT_SECRET，ENV=prod
uv run python -m alembic upgrade head         # 在 PG 上建同一套表
```

`ENV=prod` 时，应用会在启动阶段校验：`JWT_SECRET` 必须设置、`DATABASE_URL` 不得是 SQLite。

## 配置项（.env / 环境变量）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./oj.db` | 本地默认 SQLite；生产用 `postgresql+asyncpg://...` |
| `JWT_SECRET` | （dev 下自动随机） | JWT 签名密钥；`ENV=prod` 时必须显式设置 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | access token 有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | refresh token 有效期（天） |
| `ENV` | dev | `dev` / `prod` |

## 测试

```bash
uv run python -m pytest      # 默认打本地 SQLite（自动建表/迁移后）
```

## 数据库迁移常用命令

```bash
uv run python -m alembic revision --autogenerate -m "描述"   # 生成迁移
uv run python -m alembic upgrade head                        # 应用到最新
uv run python -m alembic current                             # 查看当前版本
uv run python -m alembic downgrade -1                        # 回退一版
```

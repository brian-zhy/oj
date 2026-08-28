# Supabase 数据库配置指南

本项目数据库层由 SQLAlchemy ORM + Alembic 迁移管理，所有表结构已提取为
[`supabase_schema.sql`](./supabase_schema.sql)，可直接在 Supabase（PostgreSQL）上一键建表。

## 数据库表清单（4 张）

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `users` | 用户 | 用户名/邮箱/UID 唯一索引、管理员权限组、个性资料、时间戳 |
| `refresh_tokens` | 登录令牌 | token_hash 唯一、级联删除（随用户删除） |
| `benben` | 犇犇动态 | 外键 → users.user_number，自引用 reply_to |
| `judgement_logs` | 陶片放逐日志 | 操作者/目标用户外键、JSONB 操作详情 |

## 配置步骤

### 1. 创建 Supabase 项目

在 [supabase.com](https://supabase.com) 创建项目，记下：
- Project REF（如 `abcdefghijklmnop`）
- 数据库密码（Database Settings → Database）

### 2. 执行建表脚本

Supabase Dashboard → **SQL Editor** → New query → 粘贴
`service/supabase_schema.sql` 全部内容 → **Run**。

成功后会创建 4 张表、全部索引和 `updated_at` 自动更新触发器。

### 3. 配置后端连接串

编辑 `service/.env`，将 `DATABASE_URL` 指向 Supabase（注意驱动前缀是 `postgresql+asyncpg`）：

```env
# 方式一（推荐）：Session Pooler —— 走 IPv4，本地网络都能连
DATABASE_URL=postgresql+asyncpg://postgres.{PROJECT_REF}:{密码}@aws-0-{区域}.pooler.supabase.com:5432/postgres

# 方式二：直连 —— 需要 IPv6 网络支持
DATABASE_URL=postgresql+asyncpg://postgres:{密码}@db.{PROJECT_REF}.supabase.co:5432/postgres
```

> ⚠️ 不要用 Transaction Pooler（端口 6543）：asyncpg 使用预编译语句，
> 与 transaction 模式连接池不兼容，除非额外配置 `statement_cache_size=0`。

连接串中的区域和主机名可在 Supabase 的
**Project Settings → Database → Connection string → URI** 中直接复制，只需把驱动部分改成 `postgresql+asyncpg`。

### 4. 对齐 Alembic 迁移状态

表已由 SQL 脚本建好，需要告诉 Alembic「迁移已到最新」，避免它重复建表：

```bash
cd service
uv run python -m alembic stamp head
```

> 备选方案：不执行 schema.sql，直接 `uv run python -m alembic upgrade head`
> 由迁移链建表。但该方式没有 JSONB/触发器优化，推荐用 schema.sql + stamp。

### 5. 创建第一个管理员

```bash
uv run python add_super_admin.py
```

或直接在 SQL Editor 中插入：

```sql
INSERT INTO users (username, email, hashed_password, user_number, is_admin, is_super_admin, can_manage_users, user_tag)
VALUES ('admin', 'admin@example.com', '<bcrypt哈希>', 1, true, true, true, '管理员');
```

### 6. 验证连接

```bash
uv run python -m uvicorn app.main:app --reload
```

启动后访问 `/docs`，注册/登录一次，再到 Supabase 的 Table Editor 中确认 `users` 表有新记录。

## 常见问题

| 现象 | 原因 / 处理 |
|------|-------------|
| 连接超时 | 本地网络无 IPv6 → 改用 Session Pooler 地址 |
| `prepared statement ... already exists` | 用了 6543 端口的 Transaction Pooler → 换 5432 |
| 密码含特殊字符 | URL 编码，如 `@` → `%40` |
| Table Editor 里表是空的但后端正常 | 正常现象，确认查询走的是同一 schema（public） |

## 重新生成 schema

以后修改了 `app/models/` 下的 ORM 模型，可重新导出 DDL 基线：

```bash
cd service
uv run python dump_ddl.py
```

注意其输出为通用类型（DATETIME/JSON），需参照 `supabase_schema.sql`
中的转换规则（TIMESTAMPTZ/JSONB/IDENTITY）手工调整后再执行。


## 迁移现有本地数据（可选）

本地 `sqlite` 的 `oj.db` 中已有数据时，可先用任意工具导出 CSV，
再通过 Supabase Table Editor（每张表 → Insert → Import CSV）导入；
导入后执行下面语句校正自增起点：

```sql
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT COALESCE(MAX(id), 1) FROM users));
SELECT setval(pg_get_serial_sequence('benben', 'id'), (SELECT COALESCE(MAX(id), 1) FROM benben));
SELECT setval(pg_get_serial_sequence('refresh_tokens', 'id'), (SELECT COALESCE(MAX(id), 1) FROM refresh_tokens));
SELECT setval(pg_get_serial_sequence('judgement_logs', 'id'), (SELECT COALESCE(MAX(id), 1) FROM judgement_logs));
```

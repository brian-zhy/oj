# 服务器部署步骤（Linux 裸机 → Docker）

架构：**nginx 容器**（80 端口，托管前端 + 反代 API）→ **FastAPI 容器**（8000，仅内网）→ **Supabase**（云端数据库）

```
浏览器 ──> http://服务器IP/
              │ nginx (oj-web 容器)
              ├── /api/*        → oj-service:8000/*（去掉 /api 前缀）
              ├── /auth|users|benben|tokens/* → oj-service:8000（透传）
              └── 其余路径       → 前端静态文件（SPA 回退 index.html）
```

## 一、服务器初始化（一次性）

```bash
# 1. 安装 Docker（官方脚本，Ubuntu/Debian/CentOS 通用）
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker

# 2. 让当前用户免 sudo 用 docker（重新登录后生效）
sudo usermod -aG docker $USER

# 3. 防火墙放行 80 端口（按需）
sudo ufw allow 80/tcp    # Ubuntu
```

## 二、上传代码

方式任选其一：

```bash
# 方式A：git（推荐）
git clone <你的仓库地址> /opt/oj && cd /opt/oj

# 方式B：本地打包上传（排除依赖目录）
# 本机执行：
tar --exclude=node_modules --exclude=.git --exclude=.venv --exclude=dist -czf oj.tar.gz .
scp oj.tar.gz user@服务器IP:/opt/ && ssh user@服务器IP "cd /opt && mkdir oj && tar xzf oj.tar.gz -C oj"
```

> ⚠️ `service/.env` 被 git 忽略，用 git 方式时服务器上不会有它 —— 按下面第三步创建。

## 三、配置环境变量

```bash
cd /opt/oj/service
cp .env.production .env
vi .env   # 确认三项：DATABASE_URL（Supabase）、JWT_SECRET（已填）、ENV=prod
```

前端 `web/.env.production` 已配置为同域反代（`VITE_API_BASE_URL=` 留空），无需修改。
构建时 Docker 会自动读取它。

## 四、启动

```bash
cd /opt/oj
docker compose up -d --build     # 首次构建约 3~5 分钟
docker compose ps                # 两个容器应为 running（healthy）
docker compose logs -f oj-service  # 看后端日志，确认 "Application startup complete"
```

## 五、验证

```bash
# 服务器本机
curl -s http://localhost/                       # 应返回 index.html
curl -s http://localhost/api/admin/users -o /dev/null -w "%{http_code}\n"   # 401/403 = 通了（未带token）
curl -s http://localhost/users/number/1 | head -c 200                        # 应返回用户 JSON

# 外部浏览器
# http://服务器IP/        → 主页（打卡卡片/犇犇/近期讨论）
# http://服务器IP/login   → 登录（用 Supabase 库里的账号）
# http://服务器IP/admin   → 管理后台
```

## 常见问题

| 现象 | 处理 |
|------|------|
| `oj-web` 起不来，报 nginx 配置错 | `docker compose logs oj-web`；多为 nginx.conf 语法问题 |
| 后端启动报 `ENV=prod requires JWT_SECRET` | `service/.env` 里 JWT_SECRET 没填 |
| 页面能开但接口 502 | `docker compose ps` 看 oj-service 是否 healthy；`docker compose restart oj-service` |
| Supabase 连接超时 | 服务器网络是否禁 IPv6/出网；改用 Session Pooler 连接串（5432） |
| 登录后 401 循环 | 服务器时间偏差过大导致 JWT 校验失败：`timedatectl` 检查并开启 NTP |
| 修改前端代码后更新 | `docker compose up -d --build oj-web`（只需重建前端容器） |

## 后续增强（可选）

- **HTTPS**：有域名后，在 oj-web 前面加一层 Caddy/Traefik 自动签证书，或用 certbot + 挂载证书到 nginx
- **日志轮转**：compose 中加 `logging: {driver: json-file, options: {max-size: "10m", max-file: "3"}}`
- **数据备份**：Supabase Dashboard 自带每日备份（付费版）；免费版可定期 pg_dump

#!/usr/bin/env bash
# 本地冒烟测试（SQLite，完全隔离）。用法：在 service/ 目录下执行  bash scripts/smoke.sh
# 特点：用专用库 oj_smoke.db、独立端口（默认 8011，避开开发服务），不影响你的 oj.db / .env。
set -u

cd "$(dirname "$0")/.."   # 切到 service/

PORT="${PORT:-8011}"
BASE="http://127.0.0.1:${PORT}"
LOG=/tmp/oj_uvicorn.log
SMOKE_DB="oj_smoke.db"
# 强制走 SQLite 测试库（环境变量优先级高于 .env）
export DATABASE_URL="sqlite+aiosqlite:///./${SMOKE_DB}"
# 若裸命令 python 不可用，改成  PY="uv run python"
PY=python

echo "==> 0. 清理：占用 ${PORT} 的残留进程 + 旧测试库"
PID_ON_PORT=$(netstat -ano 2>/dev/null | grep "LISTENING" | grep ":${PORT} " | awk '{print $5}' | head -1)
[ -n "${PID_ON_PORT:-}" ] && taskkill //F //PID "${PID_ON_PORT}" >/dev/null 2>&1 && echo "    killed pid ${PID_ON_PORT}"
rm -f "${SMOKE_DB}"

echo "==> 1. 建表（在 ${SMOKE_DB}）"
uv run python -m alembic upgrade head >/dev/null 2>&1 || { echo "    alembic upgrade 失败"; exit 1; }
echo "    ok"

echo "==> 2. 启动服务 (端口 ${PORT}, 库 ${SMOKE_DB})"
uv run uvicorn app.main:app --port "${PORT}" >"${LOG}" 2>&1 &
SERVER_PID=$!
cleanup() { kill "${SERVER_PID}" 2>/dev/null; }
trap cleanup EXIT
for _ in $(seq 1 40); do curl -s "${BASE}/" >/dev/null 2>&1 && break; sleep 0.25; done
curl -s "${BASE}/" >/dev/null 2>&1 || { echo "    服务未就绪，见 ${LOG}"; exit 1; }
echo "    ok (pid ${SERVER_PID})"

pass=0; fail=0
check() {  # check <说明> <期望状态码> <实际状态码>
  if [ "$2" = "$3" ]; then echo "    PASS  $1  (HTTP $3)"; pass=$((pass+1));
  else echo "    FAIL  $1  (期望 $2，实际 $3)"; fail=$((fail+1)); fi
}
# req ...  -> 设置全局 CODE 和 BODY（一次 curl 拿到响应体+状态码，不用临时文件）
req() {
  local out
  out=$(curl -s -w $'\n''___HTTP_%{http_code}' "$@")
  CODE="${out##*___HTTP_}"
  BODY="${out%%___HTTP_*}"
}

U="alice_$$"; E="${U}@example.com"; P="supersecret1"

echo "==> 3. POST /users （注册）"
req -X POST "${BASE}/users" -H "Content-Type: application/json" \
  -d "{\"username\":\"${U}\",\"email\":\"${E}\",\"password\":\"${P}\"}"
check "注册 alice" 201 "$CODE"; echo "        响应: ${BODY}"

echo "==> 4. POST /users （重复注册 → 409）"
req -X POST "${BASE}/users" -H "Content-Type: application/json" \
  -d "{\"username\":\"${U}\",\"email\":\"${E}\",\"password\":\"${P}\"}"
check "重复注册" 409 "$CODE"

echo "==> 5. POST /tokens （用户名登录）"
req -X POST "${BASE}/tokens" -d "username=${U}&password=${P}"
check "用户名登录" 200 "$CODE"
ACCESS=$(printf '%s' "${BODY}" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
REFRESH=$(printf '%s' "${BODY}" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")
echo "        access 载荷:"
"$PY" -c "import base64,json,sys;p=sys.argv[1].split('.')[1];p+='='*(-len(p)%4);print(json.dumps(json.loads(base64.urlsafe_b64decode(p)),indent=2))" "$ACCESS" | sed 's/^/          /'

echo "==> 6. POST /tokens （邮箱登录 → 200）"
req -X POST "${BASE}/tokens" -d "username=${E}&password=${P}"
check "邮箱登录" 200 "$CODE"

echo "==> 7. POST /tokens （密码错误 → 401）"
req -X POST "${BASE}/tokens" -d "username=${U}&password=wrongpass1"
check "密码错误" 401 "$CODE"

echo "==> 8. GET /users/me （带 token → 200）"
req "${BASE}/users/me" -H "Authorization: Bearer ${ACCESS}"
check "带 token 访问" 200 "$CODE"; echo "        响应: ${BODY}"

echo "==> 9. GET /users/me （不带 token → 401）"
req "${BASE}/users/me"
check "不带 token" 401 "$CODE"

echo "==> 10. GET /users/me （拿 refresh 当 access → 401）"
req "${BASE}/users/me" -H "Authorization: Bearer ${REFRESH}"
check "refresh 不能当 access" 401 "$CODE"

echo "==> 11. POST /tokens/refresh （轮换 → 200）"
req -X POST "${BASE}/tokens/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"${REFRESH}\"}"
check "刷新轮换" 200 "$CODE"
NEW_REFRESH=$(printf '%s' "${BODY}" | "$PY" -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")

echo "==> 12. POST /tokens/refresh （旧 refresh → 401）"
req -X POST "${BASE}/tokens/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"${REFRESH}\"}"
check "旧 refresh 已作废" 401 "$CODE"

echo "==> 13. POST /tokens/refresh （新 refresh → 200）"
req -X POST "${BASE}/tokens/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"${NEW_REFRESH}\"}"
check "新 refresh 仍有效" 200 "$CODE"

echo "==> 14. 连库查看 refresh_tokens（应见多行，旧的全 revoked=1）"
PYTHONUTF8=1 uv run python - <<'PY'
import sqlite3
con = sqlite3.connect("oj_smoke.db")
for row in con.execute(
    "SELECT id, user_id, substr(token_hash,1,10) AS hash, revoked, expires_at "
    "FROM refresh_tokens ORDER BY id"
):
    print("        ", row)
print("         users count:", con.execute("SELECT count(*) FROM users").fetchone()[0])
PY

echo
echo "==================================="
echo "  结果： ${pass} 通过， ${fail} 失败"
[ "$fail" -eq 0 ] && echo "  ALL GREEN ✅" || echo "  存在失败 ❌"
echo "==================================="
exit "$fail"

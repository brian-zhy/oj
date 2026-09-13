#!/usr/bin/env bash
# NLNOJ 一键部署。
#
# 用法：在服务器的 ~/.bashrc 里加一行（路径就是本文件所在位置）
#     source /www/wwwroot/api.gr3yph4ntom.cn/oj/oj/service/scripts/oj-up.sh
# 之后敲 `oj-up` 即可。
#
# 为什么做成「仓库里的文件 + .bashrc 里一行 source」而不是直接写进 .bashrc：
#   1. 不用往 .bashrc 里粘一大段多行脚本 —— 粘贴很容易被终端/编辑器搞坏
#      （这个项目上已经踩过两次：一次是行被合并，一次是后面几行被塞进函数体）
#   2. 脚本改进后跟着 git pull 一起下发，不用再去改服务器的 .bashrc
#
# 部署目录是从本文件自身位置倒推出来的（service/scripts/xxx.sh 上两级 = 仓库根），
# 换服务器、换路径都不用改这里的任何一行。

# ⚠️ 必须放在函数定义之前。
# alias 的展开会劫持函数定义：如果环境里存在旧版 `alias oj-up=...`，
# bash 读到 `oj-up() {` 时会先把 oj-up 展开成 alias 的内容，于是变成
#     cd /xxx && docker compose up -d --build () {
# 直接报 "syntax error near unexpected token `('"。
# 先清掉同名 alias，保证函数一定能定义成功。
unalias oj-up 2>/dev/null || true

oj-up() {
    local dir
    dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd) || {
        echo "❌ 推导部署目录失败"
        return 1
    }

    cd "$dir" || { echo "❌ 进不去部署目录：$dir"; return 1; }

    # 服务器上出现「已跟踪文件的改动」通常意味着有人手改过代码。
    # 这时硬拉很可能冲突，先停下让人看一眼，别把服务搞进半吊子状态。
    # （未跟踪的新文件不算 —— 上传的图、日志都在 .gitignore 里，不影响。）
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "❌ 工作区有未提交的改动，先确认这些是什么："
        git status --short
        echo "   确认无用可以执行： git checkout -- ."
        return 1
    fi

    echo "▶ 1/4 拉取代码"
    echo "   当前 HEAD: $(git log --oneline -1)"
    git pull --ff-only || { echo "❌ git pull 失败（有冲突或历史分叉），先手工处理"; return 1; }
    echo "   更新后 HEAD: $(git log --oneline -1)"

    echo "▶ 2/4 重建并重启容器"
    docker compose up -d --build \
        || { echo "❌ 构建或启动失败，看日志： docker compose logs --tail=50"; return 1; }

    echo "▶ 3/4 对齐数据库（没有新迁移时会空转，可以无脑跑）"
    docker compose exec -T oj-service uv run alembic upgrade head \
        || { echo "❌ 迁移失败！先别用站点，把上面的报错发给我"; return 1; }

    echo "▶ 4/4 确认状态"
    docker compose exec -T oj-service uv run alembic current
    docker compose ps --format 'table {{.Name}}\t{{.Status}}'
    echo "✅ 部署完成 —— 上面 alembic 那行要以 (head) 结尾，容器要是 Up/healthy"
}

# 顺手给个看日志的，排障时比 oj-up 用得还多
oj-log() {
    local dir
    dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd) || return 1
    cd "$dir" || return 1
    docker compose logs -f --tail=100 oj-service
}

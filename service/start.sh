#!/bin/bash

# ===============================================
# OJ 在线判题系统 - 生产环境启动脚本
# ===============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要命令是否存在
check_commands() {
    log_info "检查必要的命令..."

    if ! command -v uv &> /dev/null; then
        log_error "uv 命令未找到"
        log_info "安装 uv: pip install uv"
        exit 1
    fi

    log_success "所有必要命令都已安装"
}

# 检查环境变量配置
check_env_config() {
    log_info "检查环境变量配置..."

    if [ ! -f ".env" ]; then
        log_error ".env 文件不存在"
        log_info "创建 .env 文件..."

        if [ -f ".env.production" ]; then
            cp .env.production .env
            log_warning ".env 文件已从 .env.production 创建"
            log_warning "请编辑 .env 文件，填入正确的配置"
            log_info "编辑命令: nano .env"
            read -p "按 Enter 编辑 .env 文件..."
            ${EDITOR:-nano} .env
        else
            log_error ".env.production 文件不存在，无法创建配置文件"
            exit 1
        fi
    fi

    # 检查关键配置项
    source .env

    if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"YOUR_PASSWORD"* ]]; then
        log_error "DATABASE_URL 未正确配置"
        log_info "请在 .env 中设置正确的数据库连接字符串"
        exit 1
    fi

    if [ "$ENV" = "prod" ] && [ -z "$JWT_SECRET" ]; then
        log_error "生产环境必须设置 JWT_SECRET"
        log_info "生成新密钥: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        exit 1
    fi

    if [ "$ENV" = "prod" ] && [[ "$DATABASE_URL" == *"sqlite"* ]]; then
        log_error "生产环境不能使用 SQLite"
        log_info "请在 .env 中设置 PostgreSQL 连接字符串"
        exit 1
    fi

    log_success "环境变量配置检查通过"
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."

    # 使用 Python 脚本测试数据库连接
    python3 << 'EOF'
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import os

async def test_connection():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("错误: DATABASE_URL 未设置")
        sys.exit(1)

    try:
        engine = create_async_engine(db_url, pool_pre_ping=True)
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        print("数据库连接成功")
        await engine.dispose()
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        sys.exit(1)

asyncio.run(test_connection())
EOF

    if [ $? -eq 0 ]; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        log_info "请检查 DATABASE_URL 配置和数据库状态"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_info "检查并安装依赖..."

    if [ ! -d ".venv" ]; then
        log_info "创建虚拟环境..."
        uv venv
    fi

    log_info "同步依赖..."
    uv sync

    log_success "依赖安装完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    mkdir -p logs
    mkdir -p static/uploads

    log_success "目录创建完成"
}

# 检查端口是否可用
check_port() {
    local port=${1:-8000}
    log_info "检查端口 $port 是否可用..."

    if netstat -tuln | grep -q ":$port "; then
        log_warning "端口 $port 已被占用"
        read -p "是否继续? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "启动已取消"
            exit 0
        fi
    else
        log_success "端口 $port 可用"
    fi
}

# 启动服务
start_service() {
    local port=${PORT:-8000}
    local host=${HOST:-0.0.0.0}
    local workers=${WORKERS:-1}

    log_info "启动 OJ 服务..."
    log_info "监听地址: $host:$port"
    log_info "工作进程数: $workers"
    log_info "环境模式: $ENV"

    # 检查是否以生产模式运行
    if [ "$ENV" = "prod" ]; then
        log_warning "生产模式启动"
        log_info "日志文件: logs/oj-service.log"

        # 使用 gunicorn 启动（推荐生产环境）
        if command -v gunicorn &> /dev/null; then
            log_info "使用 Gunicorn 启动服务..."
            gunicorn app.main:app \
                --workers $workers \
                --worker-class uvicorn.workers.UvicornWorker \
                --bind $host:$port \
                --access-logfile logs/access.log \
                --error-logfile logs/error.log \
                --log-level info \
                --timeout 120
        else
            log_info "Gunicorn 未安装，使用 uvicorn 启动..."
            nohup uv run uvicorn app.main:app \
                --host $host \
                --port $port \
                --log-level info \
                > logs/oj-service.log 2>&1 &

            local pid=$!
            echo $pid > logs/oj-service.pid
            log_success "服务已启动，PID: $pid"
            log_info "查看日志: tail -f logs/oj-service.log"
        fi
    else
        log_info "开发模式启动..."
        uv run uvicorn app.main:app --host $host --port $port --reload
    fi
}

# 显示状态信息
show_status() {
    log_info "==================================="
    log_info "OJ 在线判题系统 - 服务信息"
    log_info "==================================="
    log_info "环境模式: ${ENV:-dev}"
    log_info "数据库: ${DATABASE_URL:0:50}..."
    log_info "监听地址: ${HOST:-0.0.0.0}:${PORT:-8000}"
    log_info "日志目录: logs/"
    log_info "==================================="
    log_info "API 文档: http://${HOST:-localhost}:${PORT:-8000}/docs"
    log_info "健康检查: http://${HOST:-localhost}:${PORT:-8000}/"
    log_info "==================================="
}

# 主函数
main() {
    echo -e "${BLUE}==================================="
    echo -e "OJ 在线判题系统 - 启动脚本"
    echo -e "===================================${NC}"
    echo ""

    # 解析命令行参数
    case "${1:-start}" in
        start)
            check_commands
            check_env_config
            install_dependencies
            create_directories
            check_port ${PORT:-8000}
            show_status
            echo ""
            read -p "按 Enter 启动服务..." -r
            echo ""
            start_service
            ;;
        check)
            log_info "运行系统检查..."
            check_commands
            check_env_config
            check_database_connection
            log_success "所有检查通过"
            ;;
        dev)
            export ENV=dev
            log_info "开发模式启动..."
            uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
            ;;
        stop)
            log_info "停止服务..."
            if [ -f "logs/oj-service.pid" ]; then
                pid=$(cat logs/oj-service.pid)
                kill $pid 2>/dev/null && log_success "服务已停止" || log_warning "服务未运行"
                rm -f logs/oj-service.pid
            else
                log_warning "未找到 PID 文件"
            fi
            ;;
        restart)
            $0 stop
            sleep 2
            $0 start
            ;;
        *)
            echo "使用方法: $0 {start|stop|restart|check|dev}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动生产服务"
            echo "  stop    - 停止服务"
            echo "  restart - 重启服务"
            echo "  check   - 运行系统检查"
            echo "  dev     - 启动开发服务"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
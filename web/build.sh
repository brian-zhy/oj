#!/bin/bash

# ===============================================
# OJ 在线判题系统 - 前端构建脚本 (Linux/Mac)
# ===============================================

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

echo -e "${BLUE}==================================="
echo "OJ 前端 - 构建部署脚本"
echo -e "===================================${NC}"
echo ""

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    log_info "安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        log_error "依赖安装失败"
        exit 1
    fi
fi

# 读取当前配置
API_URL="http://localhost:8000"
if [ -f ".env" ]; then
    log_info "读取 .env 配置..."
    API_URL=$(grep VITE_API_BASE_URL .env | cut -d '=' -f2)
fi

log_info "API 地址: $API_URL"
echo ""

# 构建选项
echo "请选择构建模式:"
echo "1. 生产构建 (使用 .env.production)"
echo "2. 开发构建 (使用当前 .env)"
echo "3. 本地测试构建"
read -p "请输入选项 (1/2/3): " choice

case $choice in
    1)
        log_info "生产环境构建..."
        cp .env.production .env.build
        ENV_FILE=".env.build"
        ;;
    2)
        log_info "开发环境构建..."
        ENV_FILE=".env"
        ;;
    3)
        log_info "本地测试构建..."
        echo "VITE_API_BASE_URL=http://localhost:8000" > .env.build
        ENV_FILE=".env.build"
        ;;
    *)
        log_error "无效的选项"
        exit 1
        ;;
esac

echo ""
log_info "开始构建..."
echo ""

# 构建项目
npm run build

if [ $? -ne 0 ]; then
    log_error "构建失败"
    rm -f .env.build
    exit 1
fi

echo ""
log_success "构建完成!"
log_info "输出目录: dist/"
echo ""

# 清理临时文件
rm -f .env.build

# 部署选项
echo "是否现在部署到服务器?"
echo "1. 是 - 复制到服务器"
echo "2. 否 - 仅构建完成"
read -p "请选择 (1/2): " deploy

if [ "$deploy" = "1" ]; then
    echo ""
    log_info "部署到服务器..."
    echo ""

    # 读取服务器配置
    if [ -f "deploy.config" ]; then
        source deploy.config
        log_info "使用配置文件: deploy.config"
    else
        # 交互式输入
        read -p "服务器地址 (user@host): " server
        read -p "部署路径 (/var/www/oj/web): " deploy_path
    fi

    if [ -n "$server" ] && [ -n "$deploy_path" ]; then
        log_info "上传文件到服务器..."
        scp -r dist/ "$server:$deploy_path"

        if [ $? -eq 0 ]; then
            log_success "部署完成!"
        else
            log_error "部署失败"
        fi
    else
        log_warning "未配置服务器信息，请手动部署"
        echo "示例命令:"
        echo "scp -r dist/ user@server:/var/www/oj/web/"
    fi
fi

echo ""
echo -e "${BLUE}==================================="
echo "构建完成!"
echo -e "===================================${NC}"
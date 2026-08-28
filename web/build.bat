@echo off
REM ===============================================
REM OJ 在线判题系统 - 前端构建脚本 (Windows)
REM ===============================================

echo ===================================
echo OJ 前端 - 构建部署脚本
echo ===================================
echo.

REM 检查 node_modules 是否存在
if not exist "node_modules" (
    echo [INFO] 安装依赖...
    call npm install
)

REM 读取环境变量
set "API_URL=http://localhost:8000"

if exist ".env" (
    echo [INFO] 读取 .env 配置...
    for /f "tokens=1,2 delims==" %%a in ('type .env ^| findstr "VITE_API_BASE_URL"') do (
        set "API_URL=%%b"
    )
)

echo [INFO] API 地址: %API_URL%
echo.

REM 构建选项
echo 请选择构建模式:
echo 1. 生产构建 (使用 .env.production)
echo 2. 开发构建 (使用当前 .env)
echo 3. 本地测试构建
set /p choice="请输入选项 (1/2/3): "

if "%choice%"=="1" (
    echo [INFO] 生产环境构建...
    copy .env.production .env.build /Y >nul
    set "ENV_FILE=.env.build"
) else if "%choice%"=="2" (
    echo [INFO] 开发环境构建...
    set "ENV_FILE=.env"
) else if "%choice%"=="3" (
    echo [INFO] 本地测试构建...
    echo VITE_API_BASE_URL=http://localhost:8000 > .env.build
    set "ENV_FILE=.env.build"
) else (
    echo [ERROR] 无效的选项
    exit /b 1
)

echo.
echo [INFO] 开始构建...
echo.

REM 执行构建
call npm run build

if errorlevel 1 (
    echo [ERROR] 构建失败
    exit /b 1
)

echo.
echo [SUCCESS] 构建完成!
echo [INFO] 输出目录: dist\
echo.

REM 清理临时文件
if exist ".env.build" del .env.build

REM 部署选项
echo 是否现在部署到服务器?
echo 1. 是 - 复制到服务器 (需要配置)
echo 2. 否 - 仅构建完成
set /p deploy="请选择 (1/2): "

if "%deploy%"=="1" (
    echo.
    echo [INFO] 部署到服务器...
    echo [WARNING] 需要配置服务器连接信息
    echo.
    echo 示例命令:
    echo scp -r dist\ user@server:/path/to/web/
    echo.
    echo 请手动执行上述命令，或修改此脚本添加自动部署功能
)

echo.
echo ===================================
echo 构建完成!
echo ===================================
pause
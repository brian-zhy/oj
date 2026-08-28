@echo off
REM ===============================================
REM OJ 在线判道系统 - 生产环境启动脚本 (Windows)
REM ===============================================

setlocal enabledelayedexpansion

REM 颜色设置 (Windows 10+)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

REM 日志函数
:log_info
echo %INFO% %~1
goto :eof

:log_success
echo %SUCCESS% %~1
goto :eof

:log_warning
echo %WARNING% %~1
goto :eof

:log_error
echo %ERROR% %~1
goto :eof

REM 检查必要命令
:check_commands
echo %INFO% 检查必要的命令...

where uv >nul 2>&1
if errorlevel 1 (
    echo %ERROR% uv 命令未找到
    echo %INFO% 安装 uv: pip install uv
    exit /b 1
)

echo %SUCCESS% 所有必要命令都已安装
goto :eof

REM 检查环境变量配置
:check_env_config
echo %INFO% 检查环境变量配置...

if not exist ".env" (
    echo %ERROR% .env 文件不存在
    echo %INFO% 创建 .env 文件...

    if exist ".env.production" (
        copy .env.production .env >nul
        echo %WARNING% .env 文件已从 .env.production 创建
        echo %WARNING% 请编辑 .env 文件，填入正确的配置
        echo %INFO% 编辑命令: notepad .env
        pause
        notepad .env
    ) else (
        echo %ERROR% .env.production 文件不存在
        exit /b 1
    )
)

REM 读取环境变量进行基本检查
findstr /C:"YOUR_PASSWORD" .env >nul
if not errorlevel 1 (
    echo %ERROR% DATABASE_URL 包含占位符，请正确配置
    echo %INFO% 请编辑 .env 文件，填入正确的数据库连接字符串
    pause
    notepad .env
)

echo %SUCCESS% 环境变量配置检查通过
goto :eof

REM 安装依赖
:install_dependencies
echo %INFO% 检查并安装依赖...

if not exist ".venv" (
    echo %INFO% 创建虚拟环境...
    uv venv
)

echo %INFO% 同步依赖...
uv sync

echo %SUCCESS% 依赖安装完成
goto :eof

REM 创建必要的目录
:create_directories
echo %INFO% 创建必要的目录...

if not exist "logs" mkdir logs
if not exist "static\uploads" mkdir static\uploads

echo %SUCCESS% 目录创建完成
goto :eof

REM 显示状态信息
:show_status
echo %INFO% ===================================
echo %INFO% OJ 在线判道系统 - 服务信息
echo %INFO% ===================================
echo %INFO% 日志目录: logs\
echo %INFO% ===================================
echo %INFO% API 文档: http://localhost:8000/docs
echo %INFO% 健康检查: http://localhost:8000/
echo %INFO% ===================================
goto :eof

REM 启动服务
:start_service
echo %INFO% 启动 OJ 服务...

REM 检查是否是生产模式
findstr /C:"ENV=prod" .env >nul
if not errorlevel 1 (
    echo %WARNING% 生产模式启动
    echo %INFO% 日志文件: logs\oj-service.log

    start /B uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info > logs\oj-service.log 2>&1

    echo %SUCCESS% 服务已启动
    echo %INFO% 查看日志: type logs\oj-service.log
) else (
    echo %INFO% 开发模式启动...
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)
goto :eof

REM 停止服务
:stop_service
echo %INFO% 停止服务...

REM 查找并终止 uvicorn 进程
for /f "tokens=2" %%a in ('tasklist ^| findstr uvicorn') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo %SUCCESS% 服务已停止
goto :eof

REM 主函数
:main
echo ===================================
echo OJ 在线判道系统 - 启动脚本
echo ===================================
echo.

if "%1"=="" goto :start
if /i "%1"=="start" goto :start
if /i "%1"=="check" goto :check
if /i "%1"=="dev" goto :dev
if /i "%1"=="stop" goto :stop
if /i "%1"=="restart" goto :restart
goto :usage

:start
call :check_commands
call :check_env_config
call :install_dependencies
call :create_directories
call :show_status
echo.
pause
call :start_service
goto :eof

:check
echo %INFO% 运行系统检查...
call :check_commands
call :check_env_config
echo %SUCCESS% 所有检查通过
goto :eof

:dev
set ENV=dev
echo %INFO% 开发模式启动...
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
goto :eof

:stop
call :stop_service
goto :eof

:restart
call :stop_service
timeout /t 2 /nobreak >nul
call :start_service
goto :eof

:usage
echo 使用方法: %0 {start^|stop^|restart^|check^|dev}
echo.
echo 命令说明:
echo   start   - 启动生产服务
echo   stop    - 停止服务
echo   restart - 重启服务
echo   check   - 运行系统检查
echo   dev     - 启动开发服务
exit /b 1

REM 运行主函数
call :main %*
# 使用官方 Python 镜像作为基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv (更快的 Python 包管理器)
RUN pip install --no-cache-dir uv

# 复制项目文件
COPY pyproject.toml uv.lock ./

# 使用 uv 安装依赖
RUN uv sync --frozen --no-dev

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs static/uploads

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 启动命令
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
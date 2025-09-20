# 使用官方的 Python 3.11 slim 镜像
FROM python:3.11-slim

# 设置环境变量，防止 Python 写入 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
# 确保 Python 输出是无缓冲的，便于日志查看
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (如果你的项目确实使用PostgreSQL，则保留此行)
# 如果不使用，可以注释掉以减小镜像体积
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# 更新 pip
RUN pip install --no-cache-dir --upgrade pip

# 复制依赖文件并安装
# 使用阿里云镜像加速
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制你的所有项目代码到容器中
COPY . /app/

# 暴露容器的端口 (Gunicorn 将在这个端口上运行)
EXPOSE 8000

# 最终运行命令：使用 Gunicorn 启动 Uvicorn workers
# -w 3: 启动 3 个工作进程 (可以根据你的服务器CPU核心数调整)
# -k uvicorn.workers.UvicornWorker: 指定使用 uvicorn 作为工作进程类
# backend.main:app: 你的应用入口
CMD ["gunicorn", "-w", "3", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "backend.main:app"]

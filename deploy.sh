#!/bin/bash

# deploy.sh - 服务器端一键部署脚本
#
# 该脚本应该在服务器的项目根目录中运行。
# 它会自动完成从拉取代码到重启服务的完整流程。

# 遇到任何错误则立即终止脚本的执行
set -e

# --- 定义变量 ---
# 定义镜像名称和容器名称，方便统一管理
IMAGE_NAME="rebirth_game_image"
CONTAINER_NAME="rebirth_game_container"

# --- 部署流程开始 ---

echo "====== [步骤 1/5] 从 GitHub 拉取最新代码 ======"
# 拉取 main 分支的最新代码
# --rebase: 使用变基而不是合并，保持提交历史的整洁
git pull origin main --rebase

echo "
====== [步骤 2/5] 构建最新的 Docker 镜像 ======"
# 使用项目中的 Dockerfile 在本地构建镜像
# -t 参数为镜像打上标签 (tag)
docker build -t ${IMAGE_NAME}:latest .

echo "
====== [步骤 3/5] 停止并删除旧的容器 ======"
# 检查具有指定名称的容器是否正在运行
if [ "$(docker ps -q -f name=${CONTAINER_NAME})" ]; then
    echo "正在停止旧容器..."
    docker stop ${CONTAINER_NAME}
    echo "旧容器已停止。"
fi

# 检查是否存在具有指定名称的容器（无论是否运行）
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    echo "正在删除旧容器..."
    docker rm ${CONTAINER_NAME}
    echo "旧容器已删除。"
fi

echo "
====== [步骤 4/5] 启动新的容器 ======"
# -d: 后台运行容器
# --name: 为容器指定一个固定的名称
# -p: 将服务器的端口映射到容器的端口。127.0.0.1:8000 表示只允许来自服务器本地的访问（由Nginx转发），更安全。
# --restart always: 容器退出时总是自动重启，保证服务高可用。
docker run -d --name ${CONTAINER_NAME} -p 127.0.0.1:8000:8000 --restart always ${IMAGE_NAME}:latest

echo "
====== [步骤 5/5] 清理无用的旧镜像 ======"
# 'docker image prune -af' 会强制删除所有悬空（dangling）的镜像
# 也就是那些没有被任何容器使用的旧镜像层，可以有效回收磁盘空间
docker image prune -af

echo "
====== 部署成功！======"
echo "应用正在容器 ${CONTAINER_NAME} 中运行。"

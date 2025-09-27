#!/bin/bash

# deploy-simple.sh - 简化版一键部署脚本
# 适合快速部署和日常更新使用

set -e

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../configs"
COMPOSE_FILE="$CONFIG_DIR/docker-compose.yml"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 开始部署 Rebirth Game...${NC}"

# 进入项目根目录
cd "$PROJECT_ROOT"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 未找到Docker，请先运行服务器初始化脚本${NC}"
    exit 1
fi

# 拉取最新代码
echo -e "${YELLOW}📥 拉取最新代码...${NC}"
git pull origin main || echo "无Git或拉取失败，跳过代码更新"

# 检查配置文件
if [ ! -f "config/settings.py" ]; then
    echo -e "${RED}❌ 未找到 config/settings.py 配置文件${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 使用内置配置系统 (config/settings.py)${NC}"

# 停止旧服务
echo -e "${YELLOW}🛑 停止旧服务...${NC}"
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# 构建并启动
echo -e "${YELLOW}🔨 构建并启动服务...${NC}"
docker compose -f "$COMPOSE_FILE" up -d --build

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 10

# 健康检查
for i in {1..12}; do
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo -e "${GREEN}✅ 部署成功！${NC}"
        echo
        echo "访问地址："
        echo "- 主页: http://$(curl -s ifconfig.me):8000"
        echo "- API: http://$(curl -s ifconfig.me):8000/docs"
        echo
        echo "管理命令："
        echo "- 查看状态: docker compose -f $COMPOSE_FILE ps"
        echo "- 查看日志: docker compose -f $COMPOSE_FILE logs -f"
        echo "- 监控服务: $SCRIPT_DIR/monitor.sh status"
        exit 0
    fi
    echo "等待中... ($i/12)"
    sleep 5
done

echo -e "${RED}❌ 服务启动失败，请检查日志：${NC}"
docker compose -f "$COMPOSE_FILE" logs
exit 1

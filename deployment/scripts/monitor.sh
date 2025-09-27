#!/bin/bash

# monitor.sh - 部署监控和管理脚本
# 提供服务状态监控、日志查看、性能监控等功能

set -euo pipefail

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../configs"
COMPOSE_FILE="$CONFIG_DIR/docker-compose.yml"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- 服务状态检查 ---
check_service_status() {
    echo -e "${BLUE}=== 服务状态 ===${NC}"
    
    cd "$PROJECT_ROOT"
    
    if ! docker compose -f "$COMPOSE_FILE" ps &> /dev/null; then
        echo -e "${RED}❌ Docker Compose 服务未运行${NC}"
        return 1
    fi
    
    # 显示容器状态
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
    
    echo
    echo -e "${BLUE}=== 健康检查 ===${NC}"
    
    # API健康检查
    if curl -f -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✅ API服务正常${NC}"
        
        # 获取详细健康信息
        health_info=$(curl -s http://localhost:8000/health)
        echo "健康状态: $health_info"
    else
        echo -e "${RED}❌ API服务异常${NC}"
    fi
    
    # 数据库连接检查
    if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U rebirth &> /dev/null; then
        echo -e "${GREEN}✅ 数据库连接正常${NC}"
    else
        echo -e "${RED}❌ 数据库连接异常${NC}"
    fi
}

# --- 查看日志 ---
view_logs() {
    local service="${1:-}"
    
    cd "$PROJECT_ROOT"
    
    if [ -z "$service" ]; then
        echo -e "${BLUE}=== 所有服务日志 (最近50行) ===${NC}"
        docker compose -f "$COMPOSE_FILE" logs --tail=50
    else
        echo -e "${BLUE}=== $service 服务日志 ===${NC}"
        docker compose -f "$COMPOSE_FILE" logs -f "$service"
    fi
}

# --- 性能监控 ---
show_performance() {
    echo -e "${BLUE}=== 系统性能 ===${NC}"
    
    # CPU和内存使用
    echo "系统资源:"
    free -h
    echo
    echo "CPU使用率:"
    top -bn1 | grep "Cpu(s)" | awk '{print $2 $3 $4}' 2>/dev/null || echo "无法获取CPU信息"
    
    echo
    echo -e "${BLUE}=== Docker容器资源使用 ===${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" 2>/dev/null || echo "无法获取容器统计信息"
    
    echo
    echo -e "${BLUE}=== 磁盘使用 ===${NC}"
    df -h /
    
    echo
    echo -e "${BLUE}=== Docker磁盘使用 ===${NC}"
    docker system df 2>/dev/null || echo "无法获取Docker磁盘信息"
}

# --- 实时监控 ---
real_time_monitor() {
    echo -e "${BLUE}=== 实时监控 (按Ctrl+C退出) ===${NC}"
    
    cd "$PROJECT_ROOT"
    
    while true; do
        clear
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Rebirth Game 实时监控"
        echo "================================================"
        
        # 服务状态
        if curl -f -s http://localhost:8000/health > /dev/null; then
            echo -e "API服务: ${GREEN}正常${NC}"
        else
            echo -e "API服务: ${RED}异常${NC}"
        fi
        
        # 容器状态
        docker compose -f "$COMPOSE_FILE" ps --format "{{.Service}}: {{.Status}}" 2>/dev/null || echo "容器信息获取失败"
        
        echo
        # 系统资源
        echo "系统资源:"
        free -h | grep Mem
        df -h / | tail -1
        
        echo
        echo "最新日志:"
        docker compose -f "$COMPOSE_FILE" logs --tail=3 app 2>/dev/null | tail -3
        
        sleep 5
    done
}

# --- 快速诊断 ---
quick_diagnosis() {
    echo -e "${BLUE}=== 快速诊断 ===${NC}"
    
    cd "$PROJECT_ROOT"
    
    local issues=()
    
    # 检查Docker服务
    if ! systemctl is-active --quiet docker; then
        issues+=("Docker服务未运行")
    fi
    
    # 检查容器状态
    local app_status=$(docker compose -f "$COMPOSE_FILE" ps app --format "{{.Status}}" 2>/dev/null || echo "unknown")
    if [[ ! "$app_status" =~ "Up" ]]; then
        issues+=("应用容器未正常运行: $app_status")
    fi
    
    local db_status=$(docker compose -f "$COMPOSE_FILE" ps db --format "{{.Status}}" 2>/dev/null || echo "unknown")
    if [[ ! "$db_status" =~ "Up" ]]; then
        issues+=("数据库容器未正常运行: $db_status")
    fi
    
    # 检查端口占用
    if ! ss -tlpn | grep ":8000 " > /dev/null; then
        issues+=("端口8000未被监听")
    fi
    
    # 检查磁盘空间
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        issues+=("磁盘空间不足: ${disk_usage}%")
    fi
    
    # 检查内存使用
    local mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$mem_usage" -gt 90 ]; then
        issues+=("内存使用过高: ${mem_usage}%")
    fi
    
    # 显示诊断结果
    if [ ${#issues[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ 所有检查通过，系统运行正常${NC}"
    else
        echo -e "${RED}⚠️  发现以下问题:${NC}"
        for issue in "${issues[@]}"; do
            echo -e "${RED}  - $issue${NC}"
        done
        
        echo
        echo -e "${YELLOW}建议操作:${NC}"
        echo "1. 重启服务: docker compose -f $COMPOSE_FILE restart"
        echo "2. 查看详细日志: $0 logs"
        echo "3. 重新部署: ./deployment/scripts/deploy.sh"
    fi
}

# --- 服务管理 ---
manage_service() {
    local action="$1"
    
    cd "$PROJECT_ROOT"
    
    case "$action" in
        start)
            echo -e "${YELLOW}启动服务...${NC}"
            docker compose -f "$COMPOSE_FILE" up -d
            ;;
        stop)
            echo -e "${YELLOW}停止服务...${NC}"
            docker compose -f "$COMPOSE_FILE" down
            ;;
        restart)
            echo -e "${YELLOW}重启服务...${NC}"
            docker compose -f "$COMPOSE_FILE" restart
            ;;
        rebuild)
            echo -e "${YELLOW}重新构建并启动...${NC}"
            docker compose -f "$COMPOSE_FILE" up -d --build
            ;;
        *)
            echo -e "${RED}未知操作: $action${NC}"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}操作完成${NC}"
}

# --- 显示帮助 ---
show_help() {
    echo "Rebirth Game 监控和管理工具"
    echo
    echo "用法: $0 [命令]"
    echo
    echo "可用命令:"
    echo "  status          显示服务状态"
    echo "  logs [service]  查看日志 (可指定服务名)"
    echo "  perf           显示性能信息"
    echo "  monitor        实时监控"
    echo "  diag           快速诊断"
    echo "  start          启动服务"
    echo "  stop           停止服务"
    echo "  restart        重启服务"
    echo "  rebuild        重新构建并启动"
    echo "  help           显示此帮助"
    echo
    echo "示例:"
    echo "  $0 status      # 查看服务状态"
    echo "  $0 logs app    # 查看应用日志"
    echo "  $0 monitor     # 进入实时监控模式"
}

# --- 主函数 ---
main() {
    local command="${1:-status}"
    
    case "$command" in
        status)
            check_service_status
            ;;
        logs)
            view_logs "${2:-}"
            ;;
        perf|performance)
            show_performance
            ;;
        monitor)
            real_time_monitor
            ;;
        diag|diagnosis)
            quick_diagnosis
            ;;
        start|stop|restart|rebuild)
            manage_service "$command"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $command${NC}"
            echo "使用 '$0 help' 查看可用命令"
            exit 1
            ;;
    esac
}

# --- 脚本入口 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

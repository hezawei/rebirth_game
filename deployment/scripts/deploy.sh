#!/bin/bash

# deploy.sh - 统一智能部署脚本
# 功能：自动检测环境、修复问题、构建并部署应用

set -euo pipefail

# --- 配置变量 ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../configs"
COMPOSE_FILE="$CONFIG_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$PROJECT_ROOT/deploy-$(date +%Y%m%d-%H%M%S).log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- 日志函数 ---
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

info() { log "${BLUE}INFO${NC}" "$@"; }
warn() { log "${YELLOW}WARN${NC}" "$@"; }
error() { log "${RED}ERROR${NC}" "$@"; }
success() { log "${GREEN}SUCCESS${NC}" "$@"; }

# --- 环境检查函数 ---
check_prerequisites() {
    info "检查系统环境..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        error "Docker 未安装。请先运行 setup-server.sh 进行环境初始化。"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! docker compose version &> /dev/null; then
        error "Docker Compose 未安装或版本过低。"
        exit 1
    fi
    
    success "环境检查通过"
}

# --- 代码更新函数 ---
update_code() {
    info "更新代码..."
    cd "$PROJECT_ROOT"
    
    # 备份当前配置
    if [ -f "$ENV_FILE" ]; then
        mkdir -p "$BACKUP_DIR"
        cp "$ENV_FILE" "$BACKUP_DIR/env-backup-$(date +%Y%m%d-%H%M%S)"
        info "已备份当前环境配置"
    fi
    
    # 检查Git状态
    if [ -d ".git" ]; then
        git stash push -m "Auto-stash before deploy $(date)" || true
        git fetch origin
        git pull origin main --rebase
        git stash pop || warn "无法自动合并本地修改，请手动检查"
    else
        warn "非Git仓库，跳过代码更新"
    fi
    
    success "代码更新完成"
}

# --- 环境配置检查 ---
check_config() {
    info "检查环境配置..."
    
    # 检查项目配置文件是否存在
    if [ ! -f "$PROJECT_ROOT/config/settings.py" ]; then
        error "未找到 config/settings.py 配置文件"
        exit 1
    fi
    
    # 检查配置文件中的API密钥是否已配置（非空且不是占位符）
    if grep -q '"api_key": "[^"]\{10,\}"' "$PROJECT_ROOT/config/settings.py"; then
        success "发现配置文件中包含API密钥配置"
    else
        warn "注意：请确保 config/settings.py 中的API密钥已正确配置"
    fi
    
    info "项目使用内置配置系统 (config/settings.py)，无需 .env 文件"
    success "环境配置检查通过"
}

# --- 智能检查函数 ---
check_image_needs_rebuild() {
    local service_name="$1"
    local dockerfile_path="deployment/configs/Dockerfile"
    local requirements_path="deployment/configs/requirements-lock.txt"
    
    # 检查镜像是否存在
    if ! docker images --format "table {{.Repository}}\t{{.Tag}}" | grep -q "configs-${service_name}"; then
        return 0  # 镜像不存在，需要构建
    fi
    
    # 检查关键文件是否有变更
    local dockerfile_hash=$(git log -1 --format="%H" -- "$dockerfile_path" 2>/dev/null || echo "unknown")
    local requirements_hash=$(git log -1 --format="%H" -- "$requirements_path" 2>/dev/null || echo "unknown")
    local code_hash=$(git log -1 --format="%H" -- backend/ config/ 2>/dev/null || echo "unknown")
    
    # 检查是否有标记文件记录上次构建的哈希
    local build_marker="/tmp/.rebirth_last_build_hash"
    local current_hash="${dockerfile_hash}-${requirements_hash}-${code_hash}"
    
    if [[ -f "$build_marker" ]]; then
        local last_hash=$(cat "$build_marker")
        if [[ "$current_hash" == "$last_hash" ]]; then
            return 1  # 无需重建
        fi
    fi
    
    # 记录当前哈希
    echo "$current_hash" > "$build_marker"
    return 0  # 需要重建
}

# --- 智能构建和启动函数 ---  
build_and_start() {
    info "智能检查服务状态..."
    cd "$PROJECT_ROOT"
    
    # 停止旧服务
    docker compose -f "$COMPOSE_FILE" down --remove-orphans || warn "停止旧服务时出现警告"
    
    # 智能构建检查
    local needs_rebuild=false
    
    if check_image_needs_rebuild "app"; then
        info "检测到代码变更，需要重新构建镜像..."
        needs_rebuild=true
        
        # 清理未使用的镜像节省空间
        docker system prune -f || warn "清理Docker缓存时出现警告"
        
        # 构建镜像
        if [[ "$FORCE_REBUILD" == "true" ]]; then
            info "正在强制重建Docker镜像（无缓存）..."
            docker compose -f "$COMPOSE_FILE" build --no-cache
        else
            info "正在构建Docker镜像（利用缓存）..."
            docker compose -f "$COMPOSE_FILE" build
        fi
    else
        success "镜像无变更，跳过构建步骤 ⚡"
    fi
    
    # 启动服务
    info "正在启动服务..."
    docker compose -f "$COMPOSE_FILE" up -d
    
    # 等待服务就绪
    info "等待服务启动..."
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            success "服务启动成功"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "服务启动超时"
            docker compose -f "$COMPOSE_FILE" logs
            exit 1
        fi
        
        info "等待服务就绪... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
}

# --- 部署后验证 ---
post_deploy_verification() {
    info "执行部署后验证..."
    
    local health_response=$(curl -s http://localhost:8000/health || echo "failed")
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        success "健康检查通过"
    else
        error "健康检查失败: $health_response"
        return 1
    fi
    
    info "当前服务状态:"
    docker compose -f "$COMPOSE_FILE" ps
    
    success "部署验证完成"
}

# --- 显示部署信息 ---
show_deployment_info() {
    success "🎉 部署完成！"
    echo
    info "服务访问信息:"
    echo "  - 主页: http://$(curl -s http://ifconfig.me):8000"
    echo "  - API文档: http://$(curl -s http://ifconfig.me):8000/docs"
    echo "  - 健康检查: http://$(curl -s http://ifconfig.me):8000/health"
    echo
    info "服务管理命令:"
    echo "  - 查看日志: cd $PROJECT_ROOT && docker compose -f $COMPOSE_FILE logs -f"
    echo "  - 重启服务: cd $PROJECT_ROOT && docker compose -f $COMPOSE_FILE restart"
    echo "  - 停止服务: cd $PROJECT_ROOT && docker compose -f $COMPOSE_FILE down"
    echo "  - 服务监控: $SCRIPT_DIR/monitor.sh status"
    echo
    info "部署日志已保存到: $LOG_FILE"
}

# --- 错误处理 ---
handle_error() {
    error "部署过程中发生错误，正在回滚..."
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" down || true
    error "部署失败，请检查日志: $LOG_FILE"
    exit 1
}

show_help() {
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  --force-rebuild    强制重新构建Docker镜像"
    echo "  --help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                 智能部署（推荐）"
    echo "  $0 --force-rebuild 强制重建部署"
}

# --- 主函数 ---
main() {
    local force_rebuild=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-rebuild)
                force_rebuild=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                warn "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [[ "$force_rebuild" == true ]]; then
        info "开始强制重建部署..."
        # 删除构建标记，强制重建
        rm -f /tmp/.rebirth_last_build_hash
        export FORCE_REBUILD=true
    else
        info "开始智能部署..."
        export FORCE_REBUILD=false
    fi
    
    check_prerequisites
    update_code
    check_config
    build_and_start
    post_deploy_verification
    show_deployment_info
    
    success "🎉 Rebirth Game 部署完成！"
}

# --- 脚本入口 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

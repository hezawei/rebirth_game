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
check_environment() {
    info "检查环境配置..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$CONFIG_DIR/.env.example" ]; then
            warn "未找到 .env 文件，将基于 .env.example 创建"
            cp "$CONFIG_DIR/.env.example" "$ENV_FILE"
            warn "请编辑 $ENV_FILE 文件，配置必要的API密钥"
            read -p "配置完成后按回车继续..."
        else
            error "未找到 .env 文件和 .env.example 模板"
            exit 1
        fi
    fi
    
    # 检查必要的环境变量
    source "$ENV_FILE"
    local has_llm_key=false
    
    if [ -n "${OPENAI_API_KEY:-}" ] && [ "${OPENAI_API_KEY}" != "" ]; then
        success "OpenAI API密钥已配置"
        has_llm_key=true
    fi
    
    if [ -n "${DOUBAO_API_KEY:-}" ] && [ "${DOUBAO_API_KEY}" != "" ]; then
        success "豆包API密钥已配置"  
        has_llm_key=true
    fi
    
    if [ -n "${GOOGLE_API_KEY:-}" ] && [ "${GOOGLE_API_KEY}" != "" ]; then
        success "Google API密钥已配置"
        has_llm_key=true
    fi
    
    if [ -n "${ANTHROPIC_API_KEY:-}" ] && [ "${ANTHROPIC_API_KEY}" != "" ]; then
        success "Anthropic API密钥已配置"
        has_llm_key=true
    fi
    
    if [ "$has_llm_key" = false ]; then
        error "未配置任何LLM API密钥，请在$ENV_FILE中配置至少一个"
        exit 1
    fi
    
    success "环境配置检查通过"
}

# --- 构建和启动函数 ---
build_and_start() {
    info "构建并启动服务..."
    cd "$PROJECT_ROOT"
    
    # 停止旧服务
    docker compose -f "$COMPOSE_FILE" down --remove-orphans || warn "停止旧服务时出现警告"
    
    # 清理无用镜像
    docker image prune -f
    
    # 构建镜像
    info "正在构建Docker镜像..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    
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

# --- 主函数 ---
main() {
    info "开始智能部署 Rebirth Game"
    info "部署日志: $LOG_FILE"
    
    # 设置错误处理
    trap handle_error ERR
    
    # 执行部署步骤
    check_prerequisites
    update_code
    check_environment
    build_and_start
    post_deploy_verification
    show_deployment_info
    
    success "✅ 部署成功完成！"
}

# --- 脚本入口 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

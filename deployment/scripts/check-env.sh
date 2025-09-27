#!/bin/bash

# check-env.sh - 部署环境检查和自动修复脚本
# 功能：检查部署环境的完整性，自动修复常见问题

set -euo pipefail

# --- 配置变量 ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../configs"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$CONFIG_DIR/docker-compose.yml"

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
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [${level}] $*"
}

info() { log "${BLUE}INFO${NC}" "$@"; }
warn() { log "${YELLOW}WARN${NC}" "$@"; }
error() { log "${RED}ERROR${NC}" "$@"; }
success() { log "${GREEN}OK${NC}" "$@"; }

# --- 检查Docker环境 ---
check_docker() {
    info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker未安装"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker服务未运行或权限不足"
        warn "尝试: sudo systemctl start docker"
        warn "添加用户到docker组: sudo usermod -aG docker \$USER"
        return 1
    fi
    
    local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    success "Docker版本: $docker_version"
    
    if ! docker compose version &> /dev/null; then
        error "Docker Compose插件未安装"
        return 1
    fi
    
    local compose_version=$(docker compose version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    success "Docker Compose版本: $compose_version"
    
    return 0
}

# --- 检查项目文件 ---
check_project_files() {
    info "检查项目文件..."
    
    cd "$PROJECT_ROOT"
    
    local required_files=(
        "backend/main.py"
        "frontend-web/package.json"
        "requirements.txt"
        "alembic.ini"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        error "缺少必要文件: ${missing_files[*]}"
        return 1
    fi
    
    success "项目文件完整"
    return 0
}

# --- 检查配置文件 ---
check_config_files() {
    info "检查配置文件..."
    
    local required_configs=(
        "$CONFIG_DIR/Dockerfile"
        "$CONFIG_DIR/docker-compose.yml"
        "$CONFIG_DIR/.env.example"
    )
    
    local missing_configs=()
    for file in "${required_configs[@]}"; do
        if [ ! -f "$file" ]; then
            missing_configs+=("$file")
        fi
    done
    
    if [ ${#missing_configs[@]} -gt 0 ]; then
        error "缺少配置文件: ${missing_configs[*]}"
        return 1
    fi
    
    success "配置文件完整"
    return 0
}

# --- 检查环境配置 ---
check_environment() {
    info "检查环境配置..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$CONFIG_DIR/.env.example" ]; then
            warn "未找到.env文件，将基于.env.example创建"
            cp "$CONFIG_DIR/.env.example" "$ENV_FILE"
            warn "请编辑$ENV_FILE配置必要参数"
        else
            error "未找到.env文件和.env.example"
            return 1
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
        return 1
    fi
    
    success "环境配置检查通过"
    return 0
}

# --- 检查端口占用 ---
check_ports() {
    info "检查端口占用..."
    
    local ports=(8000 5432 80)
    local occupied_ports=()
    
    for port in "${ports[@]}"; do
        if ss -tulpn | grep ":$port " > /dev/null 2>&1; then
            local process_info=$(ss -tulpn | grep ":$port " | head -1)
            if echo "$process_info" | grep -q "docker"; then
                success "端口$port已被Docker容器使用"
            else
                occupied_ports+=("$port")
            fi
        else
            success "端口$port可用"
        fi
    done
    
    if [ ${#occupied_ports[@]} -gt 0 ]; then
        error "以下端口被非Docker进程占用: ${occupied_ports[*]}"
        return 1
    fi
    
    return 0
}

# --- 检查系统资源 ---
check_resources() {
    info "检查系统资源..."
    
    # 检查磁盘空间
    local available_kb=$(df . | tail -1 | awk '{print $4}')
    local available_gb=$((available_kb / 1024 / 1024))
    
    if [ "$available_gb" -lt 2 ]; then
        error "可用磁盘空间不足: ${available_gb}GB (建议至少2GB)"
        return 1
    elif [ "$available_gb" -lt 5 ]; then
        warn "磁盘空间较少: ${available_gb}GB"
    else
        success "磁盘空间充足: ${available_gb}GB"
    fi
    
    # 检查内存
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    local available_mem=$(free -m | awk 'NR==2{print $7}')
    
    if [ "$total_mem" -lt 1024 ]; then
        warn "总内存较少: ${total_mem}MB (建议至少2GB)"
    else
        success "总内存: ${total_mem}MB"
    fi
    
    if [ "$available_mem" -lt 512 ]; then
        warn "可用内存较少: ${available_mem}MB"
    else
        success "可用内存: ${available_mem}MB"
    fi
    
    return 0
}

# --- 自动修复功能 ---
auto_fix() {
    info "尝试自动修复检测到的问题..."
    
    cd "$PROJECT_ROOT"
    
    # 创建缺失的目录
    mkdir -p assets/generated_images assets/images logs backups
    
    # 设置脚本权限
    find deployment/scripts -name "*.sh" -exec chmod +x {} \;
    
    # 清理Docker资源
    if command -v docker &> /dev/null; then
        info "清理无用的Docker资源..."
        docker system prune -f > /dev/null 2>&1 || true
    fi
    
    success "自动修复完成"
}

# --- 生成检查报告 ---
generate_report() {
    local report_file="$PROJECT_ROOT/deployment-check-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
=== 部署环境检查报告 ===
检查时间: $(date)

系统信息:
- 操作系统: $(lsb_release -ds 2>/dev/null || echo 'Unknown')
- 内核版本: $(uname -r)
- 架构: $(uname -m)

Docker信息:
- Docker版本: $(docker --version 2>/dev/null || echo 'Not installed')
- Compose版本: $(docker compose version 2>/dev/null || echo 'Not installed')

资源状态:
- 总内存: $(free -h | awk 'NR==2{print $2}')
- 可用内存: $(free -h | awk 'NR==2{print $7}')
- 磁盘空间: $(df -h . | tail -1 | awk '{print $4}')

项目状态:
- 项目目录: $PROJECT_ROOT
- .env文件: $([ -f "$ENV_FILE" ] && echo '存在' || echo '不存在')
- Docker配置: $([ -f "$COMPOSE_FILE" ] && echo '存在' || echo '不存在')
EOF

    info "检查报告已生成: $report_file"
}

# --- 主函数 ---
main() {
    echo "================================================"
    echo "   Rebirth Game - 部署环境检查工具"
    echo "================================================"
    echo
    
    local checks_passed=0
    local total_checks=6
    
    # 执行所有检查
    check_docker && ((checks_passed++)) || true
    check_project_files && ((checks_passed++)) || true
    check_config_files && ((checks_passed++)) || true
    check_environment && ((checks_passed++)) || true
    check_ports && ((checks_passed++)) || true
    check_resources && ((checks_passed++)) || true
    
    echo
    echo "================================================"
    
    if [ "$checks_passed" -eq "$total_checks" ]; then
        success "✅ 所有检查通过 ($checks_passed/$total_checks)"
        success "环境准备就绪，可以执行部署！"
        echo
        info "建议执行: ./deployment/scripts/deploy.sh"
    else
        warn "⚠️  检查完成 ($checks_passed/$total_checks)"
        warn "发现问题需要修复"
        echo
        read -p "是否尝试自动修复？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            auto_fix
        fi
    fi
    
    generate_report
}

# --- 脚本入口 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

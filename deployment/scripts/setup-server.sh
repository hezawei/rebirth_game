#!/bin/bash

# setup-server.sh - 完整的服务器初始化脚本
# 功能：一键完成从零到生产就绪的完整服务器配置

set -euo pipefail

# --- 配置变量 ---
SCRIPT_VERSION="2.0.0"
PROJECT_NAME="rebirth_game"

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
success() { log "${GREEN}SUCCESS${NC}" "$@"; }

# --- 权限检查 ---
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        error "此脚本需要root权限运行。请使用: sudo $0"
        exit 1
    fi
}

# --- 系统信息检查 ---
check_system() {
    info "检查系统信息..."
    
    if ! grep -q "Ubuntu" /etc/os-release; then
        warn "此脚本专为Ubuntu设计，其他系统可能出现问题"
    fi
    
    local ubuntu_version=$(lsb_release -rs 2>/dev/null || echo "unknown")
    info "操作系统: $(lsb_release -ds 2>/dev/null || echo 'Unknown')"
    info "Ubuntu版本: $ubuntu_version"
    
    local total_mem=$(free -m | awk 'NR==2{printf "%d", $2}')
    info "总内存: ${total_mem}MB"
    
    if [ "$total_mem" -lt 1024 ]; then
        warn "内存较少，建议至少2GB以获得最佳性能"
    fi
}

# --- 更新系统 ---
update_system() {
    info "更新系统软件包..."
    
    export DEBIAN_FRONTEND=noninteractive
    
    apt-get update -y
    apt-get -o Dpkg::Options::="--force-confdef" \
            -o Dpkg::Options::="--force-confold" \
            upgrade -y
    
    apt-get install -y \
        curl \
        wget \
        git \
        htop \
        vim \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        fail2ban \
        ufw \
        logrotate
    
    success "系统更新完成"
}

# --- 安装Docker ---
install_docker() {
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version)
        info "Docker已安装: $docker_version"
        return 0
    fi
    
    info "安装Docker..."
    
    # 移除旧版本
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # 添加Docker官方GPG密钥
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    # 添加Docker仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    
    # 安装Docker
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 启动Docker服务
    systemctl enable docker
    systemctl start docker
    
    # 添加当前用户到docker组
    if [ -n "${SUDO_USER:-}" ]; then
        usermod -aG docker "$SUDO_USER"
        info "用户 '$SUDO_USER' 已添加到docker组"
    fi
    
    success "Docker安装完成: $(docker --version)"
}

# --- 安装Nginx ---
install_nginx() {
    if command -v nginx &> /dev/null; then
        info "Nginx已安装: $(nginx -v 2>&1)"
        return 0
    fi
    
    info "安装Nginx..."
    
    apt-get update -y
    apt-get install -y nginx
    
    systemctl enable nginx
    systemctl start nginx
    
    success "Nginx安装完成"
}

# --- 配置防火墙 ---
configure_firewall() {
    info "配置防火墙..."
    
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    ufw allow OpenSSH
    ufw allow 'Nginx Full'
    ufw allow 8000/tcp comment 'Rebirth Game App'
    
    ufw --force enable
    
    success "防火墙配置完成"
}

# --- 配置Fail2Ban ---
configure_fail2ban() {
    info "配置Fail2Ban安全防护..."
    
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 6
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban
    
    success "Fail2Ban配置完成"
}

# --- 安装监控工具 ---
install_monitoring() {
    info "安装监控工具..."
    
    cat > /usr/local/bin/rebirth-status << 'EOF'
#!/bin/bash
echo "=== Rebirth Game 服务状态 ==="
echo "Docker容器状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo
echo "系统资源使用:"
free -h
df -h /
echo
echo "最近日志:"
docker logs rebirth-app --tail 10 2>/dev/null || echo "应用容器未运行"
EOF

    chmod +x /usr/local/bin/rebirth-status
    
    success "监控工具安装完成"
}

# --- 创建项目目录 ---
setup_project_directory() {
    info "设置项目目录..."
    
    local project_dir="/opt/$PROJECT_NAME"
    mkdir -p "$project_dir"
    
    if [ -n "${SUDO_USER:-}" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" "$project_dir"
        local user_home=$(eval echo "~$SUDO_USER")
        if [ ! -L "$user_home/rebirth_game" ]; then
            ln -s "$project_dir" "$user_home/rebirth_game"
            chown -h "$SUDO_USER:$SUDO_USER" "$user_home/rebirth_game"
        fi
    fi
    
    echo "$project_dir"
}

# --- 生成部署信息 ---
generate_deployment_info() {
    local project_dir="$1"
    local public_ip=$(curl -s http://ifconfig.me || echo "无法获取")
    
    cat > "$project_dir/deployment-info.txt" << EOF
=== Rebirth Game 部署信息 ===
部署时间: $(date)
脚本版本: $SCRIPT_VERSION

服务器信息:
- 公网IP: $public_ip
- 系统: $(lsb_release -ds 2>/dev/null || echo 'Unknown')

访问地址:
- 主服务: http://$public_ip
- API文档: http://$public_ip/docs
- 健康检查: http://$public_ip/health

项目目录: $project_dir

常用命令:
- 查看状态: rebirth-status
- 部署更新: cd $project_dir && ./deployment/scripts/deploy.sh
- 查看日志: cd $project_dir && docker compose logs -f

下一步操作:
1. 将代码克隆到项目目录
2. 配置 .env 文件
3. 运行 ./deployment/scripts/deploy.sh 进行部署
EOF

    success "部署信息已保存到: $project_dir/deployment-info.txt"
}

# --- 主函数 ---
main() {
    echo "================================================"
    echo "  Rebirth Game - 服务器完整初始化脚本"
    echo "  版本: $SCRIPT_VERSION"
    echo "================================================"
    
    check_root
    check_system
    
    update_system
    install_docker
    install_nginx
    configure_firewall
    configure_fail2ban
    install_monitoring
    
    local project_dir=$(setup_project_directory)
    generate_deployment_info "$project_dir"
    
    echo
    success "🎉 服务器初始化完成！"
    echo
    warn "重要提醒："
    warn "1. 请重新登录以应用用户组权限变更"
    warn "2. 将代码克隆到: $project_dir"
    warn "3. 配置 .env 文件中的API密钥"
    warn "4. 运行部署脚本: ./deployment/scripts/deploy.sh"
    echo
    info "查看详细信息: cat $project_dir/deployment-info.txt"
}

# --- 脚本入口 ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

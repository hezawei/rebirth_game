#!/bin/bash

# setup_server.sh: 一键初始化 Ubuntu 22.04 服务器环境
#
# 功能:
# 1. 更新系统
# 2. 安装 Docker (如果未安装)
# 3. 安装 Nginx (如果未安装)
# 4. 配置防火墙 (UFW)
#
# 特性: 幂等性、详细日志、错误即停

# --- 配置 --- #
# 如果脚本的任何命令返回非零退出码，则立即退出
set -e
# 如果在命令替换中，管道中的任何命令失败，则整个管道失败
set -o pipefail

# --- 日志函数 --- #
log() {
    # 格式: [YYYY-MM-DD HH:MM:SS] [LEVEL] MESSAGE
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
    exit 1
}

# --- 主逻辑 --- #
main() {
    log "=================================================="
    log "   开始初始化 Ubuntu 22.04 服务器环境..."
    log "=================================================="

    # 检查是否以 root 用户运行
    if [ "$(id -u)" -ne 0 ]; then
        error "此脚本必须以 root 用户或使用 sudo 运行。请尝试 'sudo ./setup_server.sh'"
    fi

    # --- 1. 更新系统 (以非交互模式) --- #
    log "正在更新系统软件包..."
    # 设置为非交互模式，避免 'apt-get upgrade' 弹出配置窗口
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y
    log "系统更新完成。"

    # --- 2. 安装 Docker --- #
    if command -v docker &> /dev/null; then
        log "Docker 已安装，版本: $(docker --version)"
    else
        log "未检测到 Docker，正在开始安装..."
        # 确保在非交互模式下安装
        export DEBIAN_FRONTEND=noninteractive
        apt-get install -y ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg

        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        apt-get update -y
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        log "Docker 安装成功。版本: $(docker --version)"
        
        # 允许当前用户（通过 sudo 运行脚本的用户）免 sudo 使用 docker
        if [ -n "$SUDO_USER" ]; then
            log "正在将用户 '$SUDO_USER' 添加到 'docker' 组..."
            usermod -aG docker $SUDO_USER
            log "用户 '$SUDO_USER' 已添加到 'docker' 组。请重新登录以使更改生效。"
        fi
    fi
    systemctl enable docker
    systemctl start docker
    log "Docker 服务已启动并设置为开机自启。"

    # --- 3. 安装 Nginx --- #
    if command -v nginx &> /dev/null; then
        log "Nginx 已安装。"
    else
        log "未检测到 Nginx，正在开始安装..."
        # 确保在非交互模式下安装
        export DEBIAN_FRONTEND=noninteractive
        apt-get install -y nginx
        log "Nginx 安装成功。"
    fi
    systemctl enable nginx
    systemctl start nginx
    log "Nginx 服务已启动并设置为开机自启。"

    # --- 4. 配置防火墙 (UFW) --- #
    log "正在配置防火墙 (UFW)..."
    if ufw status | grep -q "Status: active"; then
        log "UFW 已激活。"
    else
        log "UFW 未激活，正在启用..."
        ufw --force enable
    fi
    
    log "允许 OpenSSH (端口 22)..."
    ufw allow OpenSSH
    
    log "允许 Nginx Full (端口 80 和 443)..."
    ufw allow 'Nginx Full'

    log "防火墙配置完成。当前状态:"
    ufw status

    # --- 5. 自动配置 Nginx 反向代理 --- #
    log "正在自动配置 Nginx 反向代理..."

    # 自动获取公网IP
    PUBLIC_IP=$(curl -s http://ifconfig.me)
    if [ -z "$PUBLIC_IP" ]; then
        error "无法自动获取公网IP地址。请检查网络连接或手动配置Nginx。"
    fi
    log "检测到服务器公网IP为: $PUBLIC_IP"

    # Nginx 配置文件路径
    NGINX_CONF_FILE="/etc/nginx/sites-available/rebirth_game"

    log "正在创建 Nginx 配置文件: $NGINX_CONF_FILE"

    # 使用 cat 和 EOF 动态生成配置文件
    # 注意：EOF 前后的内容中，$host 等是 Nginx 变量，需要用 \ 转义 $，以防止被 shell 解释
    # 而 $PUBLIC_IP 是 shell 变量，不需要转义
    cat > "$NGINX_CONF_FILE" << EOF
server {
    listen 80;
    server_name $PUBLIC_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    proxy_connect_timeout 60s;
    proxy_read_timeout 60s;
}
EOF

    log "Nginx 配置文件创建成功。"

    # 启用新配置并禁用默认配置
    if [ -f /etc/nginx/sites-enabled/default ]; then
        log "正在移除默认的 Nginx 配置..."
        rm /etc/nginx/sites-enabled/default
    fi
    if [ ! -L /etc/nginx/sites-enabled/rebirth_game ]; then
        log "正在启用 'rebirth_game' Nginx 配置..."
        ln -s /etc/nginx/sites-available/rebirth_game /etc/nginx/sites-enabled/
    else
        log "'rebirth_game' Nginx 配置已经启用。"
    fi

    # 测试 Nginx 配置并重启
    log "正在测试 Nginx 配置语法..."
    nginx -t
    log "Nginx 配置语法正确。正在重启 Nginx 服务..."
    systemctl restart nginx
    log "Nginx 服务已重启，新配置已生效。"

    log "=================================================="
    log "      服务器环境初始化和配置成功!"
    log ""
    log "已完成:"
    log "  - Docker 安装与配置"
    log "  - Nginx 安装与自动化配置"
    log "  - 防火墙配置"
    log ""
    log "服务器已准备就绪，可以接收应用部署。"
    log ""
    log "下一步:"
    log "  1. (如果适用) 重新登录服务器以应用 docker 用户组权限。"
    log "  2. 在 GitHub 仓库中设置 Secrets 并推送代码以触发首次部署。"
    log "=================================================="
}

# --- 脚本执行入口 --- #
main "$@"

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

    # --- 1. 更新系统 --- #
    log "正在更新系统软件包..."
    apt-get update -y
    apt-get upgrade -y
    log "系统更新完成。"

    # --- 2. 安装 Docker --- #
    if command -v docker &> /dev/null; then
        log "Docker 已安装，版本: $(docker --version)"
    else
        log "未检测到 Docker，正在开始安装..."
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

    log "=================================================="
    log "      服务器环境初始化成功!"
    log ""
    log "已安装并启动:"
    log "  - Docker"
    log "  - Nginx"
    log ""
    log "防火墙已配置，允许以下服务:"
    log "  - OpenSSH (SSH)"
    log "  - Nginx Full (HTTP/HTTPS)"
    log ""
    log "下一步:"
    log "  1. (如果适用) 重新登录服务器以应用 docker 用户组权限。"
    log "  2. 配置 Nginx 反向代理。"
    log "  3. 设置 GitHub Actions 以进行自动化部署。"
    log "=================================================="
}

# --- 脚本执行入口 --- #
main "$@"

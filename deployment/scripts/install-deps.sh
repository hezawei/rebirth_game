#!/bin/bash
# install-deps.sh - 智能Python依赖安装脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 日志函数
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# 检查包版本是否匹配
check_package_version() {
    local package=$1
    local required_version=$2
    
    if pip show "$package" >/dev/null 2>&1; then
        local installed_version
        installed_version=$(pip show "$package" | grep Version | cut -d' ' -f2)
        if [[ "$installed_version" == "$required_version" ]]; then
            return 0  # 版本匹配
        fi
    fi
    return 1  # 版本不匹配或未安装
}

# 解析requirements文件
parse_requirements() {
    local req_file=$1
    local packages_to_install=()
    
    while IFS= read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # 提取包名和版本
        if [[ "$line" =~ ^([^=]+)==([^[:space:]]+) ]]; then
            local package="${BASH_REMATCH[1]}"
            local version="${BASH_REMATCH[2]}"
            
            # 处理extras (如 pydantic[email])
            package=$(echo "$package" | sed 's/\[.*\]//')
            
            if ! check_package_version "$package" "$version"; then
                packages_to_install+=("$line")
                info "需要安装/更新: $line"
            else
                info "✓ 已安装正确版本: $package==$version"
            fi
        fi
    done < "$req_file"
    
    echo "${packages_to_install[@]}"
}

main() {
    local req_file="${1:-deployment/configs/requirements-lock.txt}"
    
    if [[ ! -f "$req_file" ]]; then
        error "Requirements文件不存在: $req_file"
        exit 1
    fi
    
    info "检查Python包依赖: $req_file"
    
    # 配置pip镜像源
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
    
    # 升级pip
    info "升级pip..."
    pip install --upgrade pip
    
    # 解析需要安装的包
    local packages
    packages=$(parse_requirements "$req_file")
    
    if [[ -z "$packages" ]]; then
        info "🎉 所有依赖已是最新版本，无需安装"
        return 0
    fi
    
    # 批量安装需要更新的包
    info "安装/更新以下包:"
    echo "$packages" | tr ' ' '\n'
    
    # 创建临时requirements文件
    local temp_req="/tmp/temp_requirements.txt"
    echo "$packages" | tr ' ' '\n' > "$temp_req"
    
    info "开始安装..."
    if pip install -r "$temp_req"; then
        info "✅ 依赖安装完成"
        rm -f "$temp_req"
    else
        error "❌ 依赖安装失败"
        rm -f "$temp_req"
        exit 1
    fi
}

main "$@"

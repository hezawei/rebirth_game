#!/bin/bash

# organize-files.sh - 整理部署文件，清理根目录
# 将旧的部署文件移动到legacy目录，清理冗余文件

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$SCRIPT_DIR/.."
LEGACY_DIR="$DEPLOYMENT_DIR/legacy"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

echo "================================================"
echo "   Rebirth Game - 部署文件整理工具"
echo "================================================"

cd "$PROJECT_ROOT"

# 创建legacy目录
mkdir -p "$LEGACY_DIR"

info "开始整理部署相关文件..."

# 移动旧的部署文件到legacy目录
OLD_DEPLOY_FILES=(
    "deploy.sh"
    "deploy-smart.sh" 
    "deploy-simple.sh"
    "check-deployment.sh"
    "monitor.sh"
    "init-server-complete.sh"
    "setup_server.sh"
    "Dockerfile.fullstack"
    "docker-compose.production.yml"
    "nginx.conf"
    "DEPLOYMENT.md"
    "DEPLOYMENT_QUICK_START.md"
    "DEPLOYMENT_SUMMARY.md"
)

info "移动旧的部署文件到 legacy 目录..."
for file in "${OLD_DEPLOY_FILES[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$LEGACY_DIR/"
        info "移动: $file -> legacy/"
    fi
done

# 更新Dockerfile路径引用
info "更新优化后的Dockerfile..."
if [ -f "Dockerfile" ]; then
    # 备份原文件
    cp "Dockerfile" "$LEGACY_DIR/Dockerfile.original"
    info "备份原Dockerfile到 legacy/"
fi

# 创建根目录的快速部署脚本（入口脚本）
info "创建新的根目录入口脚本..."

cat > "deploy.sh" << 'EOF'
#!/bin/bash
# 快速部署入口脚本 - 调用deployment目录中的脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_SCRIPT="$SCRIPT_DIR/deployment/scripts/deploy.sh"

if [ -f "$DEPLOYMENT_SCRIPT" ]; then
    echo "🚀 启动 Rebirth Game 智能部署..."
    exec "$DEPLOYMENT_SCRIPT" "$@"
else
    echo "❌ 未找到部署脚本: $DEPLOYMENT_SCRIPT"
    exit 1
fi
EOF

chmod +x "deploy.sh"
success "创建快速部署入口: deploy.sh"

# 创建快速监控入口脚本
cat > "monitor.sh" << 'EOF'
#!/bin/bash
# 快速监控入口脚本 - 调用deployment目录中的脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/deployment/scripts/monitor.sh"

if [ -f "$MONITOR_SCRIPT" ]; then
    exec "$MONITOR_SCRIPT" "$@"
else
    echo "❌ 未找到监控脚本: $MONITOR_SCRIPT"
    exit 1
fi
EOF

chmod +x "monitor.sh"
success "创建快速监控入口: monitor.sh"

# 更新.dockerignore以排除legacy目录
info "更新 .dockerignore..."
if [ -f ".dockerignore" ]; then
    # 添加legacy目录到.dockerignore
    if ! grep -q "deployment/legacy" ".dockerignore"; then
        echo "" >> ".dockerignore"
        echo "# Legacy deployment files" >> ".dockerignore"
        echo "deployment/legacy/" >> ".dockerignore"
    fi
fi

# 清理可能存在的冗余文件
info "清理冗余和临时文件..."
CLEANUP_PATTERNS=(
    "deploy-*.log"
    "deployment-check-*.txt"
    "*.bak"
    "nohup.out"
)

for pattern in "${CLEANUP_PATTERNS[@]}"; do
    find . -maxdepth 1 -name "$pattern" -delete 2>/dev/null && info "清理: $pattern" || true
done

# 设置deployment目录中脚本的执行权限
info "设置脚本执行权限..."
find "$DEPLOYMENT_DIR/scripts" -name "*.sh" -exec chmod +x {} \;

# 生成整理报告
info "生成整理报告..."
cat > "$LEGACY_DIR/MIGRATION_REPORT.md" << EOF
# 部署文件整理报告

整理时间: $(date)

## 移动到Legacy的文件

以下文件已从根目录移动到 deployment/legacy/ 目录:

EOF

for file in "${OLD_DEPLOY_FILES[@]}"; do
    if [ -f "$LEGACY_DIR/$file" ]; then
        echo "- $file" >> "$LEGACY_DIR/MIGRATION_REPORT.md"
    fi
done

cat >> "$LEGACY_DIR/MIGRATION_REPORT.md" << EOF

## 新的目录结构

现在的部署文件组织如下:

\`\`\`
deployment/
├── scripts/           # 所有部署脚本
│   ├── deploy.sh     # 主要部署脚本 ⭐
│   ├── monitor.sh    # 监控脚本
│   └── ...
├── configs/          # 配置文件
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── ...
└── legacy/           # 旧文件归档
    └── 本报告及移动的旧文件
\`\`\`

## 使用方法

### 新的部署方式:
\`\`\`bash
# 方式1: 使用根目录入口脚本 (推荐)
./deploy.sh

# 方式2: 直接调用deployment目录脚本
./deployment/scripts/deploy.sh
\`\`\`

### 监控服务:
\`\`\`bash
# 方式1: 使用根目录入口脚本
./monitor.sh status

# 方式2: 直接调用deployment目录脚本  
./deployment/scripts/monitor.sh status
\`\`\`

## 兼容性

根目录的 deploy.sh 和 monitor.sh 是入口脚本，会自动调用 deployment/ 目录中的实际脚本，
保持了向后兼容性。
EOF

echo
success "🎉 部署文件整理完成！"
echo
info "整理报告: $LEGACY_DIR/MIGRATION_REPORT.md"
echo
info "新的使用方式:"
echo "  部署: ./deploy.sh"
echo "  监控: ./monitor.sh status"
echo "  检查: ./deployment/scripts/check-env.sh"
echo
warn "旧文件已移动到 deployment/legacy/ 目录"
warn "如确认新部署方式工作正常，可安全删除 legacy 目录"

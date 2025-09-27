# 🎯 Rebirth Game - 完整部署指南

## 📋 架构概述

### 技术栈
- **容器化**: Docker + Docker Compose
- **Web服务器**: Nginx (反向代理)
- **应用服务器**: Gunicorn + Uvicorn  
- **数据库**: PostgreSQL 16
- **前端**: SvelteKit (构建为静态文件)
- **后端**: FastAPI + Python 3.11

### 部署架构
```
Internet → Nginx (80/443) → App Container (8000) → PostgreSQL Container (5432)
```

## 🛠️ 部署脚本详解

### 1. `deploy.sh` - 智能部署脚本（推荐）

**功能特性：**
- 全自动环境检查和修复
- 代码拉取和备份
- 智能错误处理和回滚  
- 部署后验证
- 详细日志记录

**适用场景：**
- 生产环境部署
- CI/CD自动化
- 需要可靠性保证的场景

**使用方法：**
```bash
./deployment/scripts/deploy.sh
```

### 2. `deploy-simple.sh` - 简化部署脚本

**功能特性：**
- 最少用户交互
- 快速执行
- 基础错误检查

**适用场景：**
- 开发环境快速部署
- 熟悉流程的技术用户
- 快速测试和验证

**使用方法：**
```bash
./deployment/scripts/deploy-simple.sh
```

### 3. `setup-server.sh` - 服务器初始化脚本

**功能特性：**
- 系统包更新
- Docker和Docker Compose安装
- Nginx安装和配置
- 防火墙和安全配置
- 监控工具安装

**使用方法：**
```bash
sudo ./deployment/scripts/setup-server.sh
```

### 4. `check-env.sh` - 环境检查脚本

**功能特性：**
- Docker环境验证
- 项目文件完整性检查
- 环境变量验证
- 端口占用检查
- 系统资源检查
- 自动修复建议

**使用方法：**
```bash
./deployment/scripts/check-env.sh
```

### 5. `monitor.sh` - 服务监控脚本

**功能特性：**
- 实时服务状态监控
- 日志查看和分析
- 性能指标监控
- 快速问题诊断
- 服务管理操作

**常用命令：**
```bash
./deployment/scripts/monitor.sh status     # 查看状态
./deployment/scripts/monitor.sh logs      # 查看日志
./deployment/scripts/monitor.sh monitor   # 实时监控
./deployment/scripts/monitor.sh diag      # 快速诊断
./deployment/scripts/monitor.sh restart   # 重启服务
```

## ⚙️ 配置文件详解

### 1. `Dockerfile` - 容器镜像配置

**优化特性：**
- 多阶段构建减少镜像大小
- 缓存层优化加速构建
- 非root用户运行提升安全性
- 内置健康检查

### 2. `docker-compose.yml` - 容器编排配置  

**服务组件：**
- **db服务**: PostgreSQL数据库
- **app服务**: 应用容器
- **nginx服务**: 反向代理（可选）

**关键特性：**
- 健康检查和依赖管理
- 数据持久化
- 网络隔离
- 资源限制

### 3. `nginx.conf` - Nginx反向代理配置

**功能特性：**
- 反向代理和负载均衡
- 静态文件缓存优化
- Gzip压缩
- 安全头配置
- API路径特殊处理

### 4. `.env.example` - 环境变量模板

**配置分类：**
- 数据库连接配置
- LLM API密钥配置
- 服务器资源配置  
- Nginx端口配置
- 安全相关配置

## 🔧 高级配置

### 启用Nginx反向代理

```bash
# 使用Nginx profile启动
docker compose -f deployment/configs/docker-compose.yml --profile with-nginx up -d
```

### 资源限制配置

在`.env`文件中配置：
```env
CPU_LIMIT=2.0              # CPU核数限制
MEMORY_LIMIT=2G            # 内存限制  
MEMORY_RESERVE=512M        # 内存预留
GUNICORN_WORKERS=4         # 工作进程数
```

### SSL证书配置

1. 将证书文件放入`ssl-certs`目录：
```bash
mkdir -p ssl-certs  
cp your-cert.pem ssl-certs/cert.pem
cp your-key.pem ssl-certs/key.pem
```

2. 编辑`deployment/configs/nginx.conf`启用HTTPS配置

### 自定义数据库配置

```env
# 自定义数据库参数
PGUSER=custom_user
PGPASSWORD=custom_password  
PGDATABASE=custom_db
PG_PORT=5432
```

## 🔍 监控和运维

### 日志管理

**查看应用日志：**
```bash
./deployment/scripts/monitor.sh logs app
```

**查看数据库日志：**
```bash
./deployment/scripts/monitor.sh logs db
```

**实时日志监控：**
```bash
./deployment/scripts/monitor.sh logs
```

### 性能监控

**系统资源监控：**
```bash
./deployment/scripts/monitor.sh perf
```

**实时监控界面：**
```bash
./deployment/scripts/monitor.sh monitor
```

### 备份和恢复

**数据库备份：**
```bash
docker compose -f deployment/configs/docker-compose.yml exec db pg_dump -U rebirth rebirth > backup.sql
```

**数据库恢复：**
```bash
docker compose -f deployment/configs/docker-compose.yml exec -T db psql -U rebirth rebirth < backup.sql
```

## 🚨 故障排除指南

### 常见问题诊断

#### 1. 服务启动失败
```bash
# 检查容器状态
./deployment/scripts/monitor.sh status

# 查看启动日志
./deployment/scripts/monitor.sh logs

# 检查配置
./deployment/scripts/check-env.sh
```

#### 2. 数据库连接问题
```bash
# 检查数据库容器
./deployment/scripts/monitor.sh logs db

# 测试数据库连接
docker compose -f deployment/configs/docker-compose.yml exec db pg_isready -U rebirth
```

#### 3. API访问异常  
```bash
# 检查健康状态
curl http://localhost:8000/health

# 查看应用日志
./deployment/scripts/monitor.sh logs app
```

#### 4. 资源不足
```bash
# 系统资源检查  
./deployment/scripts/monitor.sh diag

# 清理Docker资源
docker system prune -a
```

### 错误代码参考

| 错误类型 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 容器启动失败 | 端口占用、配置错误 | 检查端口、验证配置 |
| 数据库连接失败 | 数据库未就绪、密码错误 | 等待数据库启动、检查密码 |
| API请求超时 | 资源不足、应用异常 | 检查资源、查看日志 |
| 镜像构建失败 | 依赖问题、网络问题 | 检查依赖、重试构建 |

## 📈 性能优化

### 生产环境推荐配置

**服务器规格：**
- CPU: 4核心+  
- 内存: 8GB+
- 存储: 50GB+ SSD
- 网络: 10Mbps+

**应用配置：**
```env
GUNICORN_WORKERS=8          # CPU核数 * 2
CPU_LIMIT=4.0               # 适当的CPU限制
MEMORY_LIMIT=4G             # 充足的内存
LOG_LEVEL=warning           # 减少日志量
```

### 数据库优化

**PostgreSQL调优：**
```sql
-- 在数据库容器中执行
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';  
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

## 🔐 安全最佳实践

### 服务器安全

- ✅ 使用非root用户运行应用
- ✅ 防火墙配置（UFW）
- ✅ 入侵检测（Fail2Ban）
- ✅ SSH密钥认证
- ✅ 定期安全更新

### 应用安全

- ✅ 容器运行时安全
- ✅ 网络隔离
- ✅ 敏感信息环境变量化
- ✅ API密钥轮换
- ✅ HTTPS加密

### 数据安全

- ✅ 数据库密码复杂化
- ✅ 定期数据备份
- ✅ 访问日志记录
- ✅ 数据卷加密（可选）

---

**🎯 通过本指南，你将拥有一个安全、可靠、高性能的生产级AI游戏服务！**

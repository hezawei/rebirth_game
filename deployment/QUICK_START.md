# 🚀 Rebirth Game - 快速部署指南

## 📋 部署概述

本指南将帮助你在Ubuntu服务器上实现**一键式Docker容器化部署**，确保项目的完全隔离和一致性。

### 🎯 部署目标
- ✅ **完全容器化**: 所有服务运行在Docker容器中，确保环境一致性
- ✅ **一键操作**: `git pull` + 一个命令即可完成部署  
- ✅ **零配置冲突**: 本地开发环境与服务器完全隔离
- ✅ **生产就绪**: 包含Nginx、数据库、监控等完整配置

## 🚀 快速开始（3分钟部署）

### 第一步：服务器初始化（一次性）

在全新的Ubuntu服务器上执行：

```bash
# SSH登录服务器
ssh your_user@your_server_ip

# 下载并运行初始化脚本
cd /opt
git clone https://github.com/your-username/rebirth_game.git
cd rebirth_game

# 运行服务器初始化
sudo ./deployment/scripts/setup-server.sh

# 重新登录以应用权限变更
exit
ssh your_user@your_server_ip
```

### 第二步：配置环境

```bash
# 进入项目目录
cd /opt/rebirth_game

# 配置环境变量
cp deployment/configs/.env.example .env
nano .env  # 配置API密钥

# 检查环境
./deployment/scripts/check-env.sh
```

**必须配置的参数：**
```env
# 至少配置一个LLM API密钥
OPENAI_API_KEY=sk-your-openai-key
# 或者其他API密钥...
```

### 第三步：一键部署

```bash
# 执行智能部署
./deployment/scripts/deploy.sh
```

**就是这么简单！** 🎉

## 🔄 日常更新流程

本地开发完成后，在服务器执行：

```bash
cd /opt/rebirth_game
./deployment/scripts/deploy.sh
```

脚本会自动：
1. 拉取最新代码
2. 重新构建镜像  
3. 滚动更新服务
4. 验证部署结果

## 📊 服务管理

### 查看服务状态
```bash
# 快速状态检查
./deployment/scripts/monitor.sh status

# 查看实时日志
./deployment/scripts/monitor.sh logs

# 实时监控
./deployment/scripts/monitor.sh monitor
```

### 常用操作
```bash
# 重启服务
./deployment/scripts/monitor.sh restart

# 停止服务
./deployment/scripts/monitor.sh stop

# 重新构建
./deployment/scripts/monitor.sh rebuild
```

## 🐛 故障排除

### 快速诊断
```bash
# 环境检查
./deployment/scripts/check-env.sh

# 快速诊断  
./deployment/scripts/monitor.sh diag
```

### 常见问题

**问题1: API密钥未配置**
```bash
# 解决: 编辑.env文件
nano .env
```

**问题2: 服务启动失败**
```bash
# 查看日志
./deployment/scripts/monitor.sh logs

# 重新部署
./deployment/scripts/deploy.sh
```

**问题3: 端口占用**
```bash
# 检查端口
./deployment/scripts/monitor.sh diag
```

## 🎉 部署完成

部署成功后，你可以通过以下地址访问：

- **主页**: `http://your-server-ip`
- **API文档**: `http://your-server-ip/docs`  
- **健康检查**: `http://your-server-ip/health`

## 📁 目录结构

```
deployment/
├── README.md              # 部署目录说明
├── QUICK_START.md         # 本文档
├── DEPLOYMENT_GUIDE.md    # 完整部署指南
├── scripts/               # 部署脚本
│   ├── deploy.sh         # 主要部署脚本 ⭐
│   ├── deploy-simple.sh  # 简化版本
│   ├── setup-server.sh   # 服务器初始化
│   ├── check-env.sh      # 环境检查
│   └── monitor.sh        # 服务监控
├── configs/              # 配置文件
│   ├── Dockerfile        # Docker镜像配置
│   ├── docker-compose.yml # 容器编排
│   ├── nginx.conf        # Nginx配置
│   └── .env.example      # 环境变量模板
└── docs/                 # 详细文档
```

---

**🎉 恭喜！你已经拥有了一个生产就绪的AI游戏服务！**

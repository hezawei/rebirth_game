# 🚀 部署说明

## 📋 唯一方案

### Windows本地整理（一次性）
```cmd
python organize.py
git add .
git commit -m "整理部署文件"
git push
```

### Ubuntu服务器部署
```bash
# 首次：服务器初始化
git clone https://github.com/your-repo/rebirth_game.git
cd rebirth_game
sudo ./deployment/scripts/setup-server.sh

# 配置环境
cp deployment/configs/.env.example .env
nano .env  # 配置API密钥

# 部署（日常使用）
git pull
./deploy.sh

# 监控
./monitor.sh status
```

## 📁 结构
- `deployment/scripts/` - 部署脚本
- `deployment/configs/` - 配置文件  
- `deploy.sh` - 部署入口
- `monitor.sh` - 监控入口

就这么简单！

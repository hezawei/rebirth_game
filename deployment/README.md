# 部署目录

## 📁 结构
```
deployment/
├── scripts/              # 部署脚本
│   ├── deploy.sh        # 智能部署脚本
│   ├── setup-server.sh  # 服务器初始化  
│   ├── check-env.sh     # 环境检查
│   └── monitor.sh       # 服务监控
└── configs/             # 配置文件
    ├── Dockerfile       # 容器镜像
    ├── docker-compose.yml # 容器编排
    ├── nginx.conf       # 反向代理
    └── .env.example     # 环境模板
```

## 🚀 使用
- 部署: `../deploy.sh` 
- 监控: `../monitor.sh status`

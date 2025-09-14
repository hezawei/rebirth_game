# 《重生之旅》阿里云服务器部署指南

本文档将指导你如何将《重生之旅》项目部署到一台全新的阿里云ECS服务器（推荐使用Ubuntu 22.04 LTS）。

## 核心架构

我们的生产环境架构如下：
- **Nginx**: 作为反向代理和Web服务器。它负责处理所有来自用户的HTTP/HTTPS请求。
  - 如果是静态文件请求（如HTML, CSS, JS, 图片），Nginx会直接从前端构建好的文件中返回。
  - 如果是API请求（如 `/api/...`, `/auth/...`），Nginx会把请求转发给后端的Gunicorn服务。
- **Gunicorn**: 一个生产级的Python WSGI服务器，负责运行我们的FastAPI后端应用。它比 `uvicorn` 更稳定，更适合生产环境。
- **FastAPI Backend**: 我们的Python后端应用实例。
- **SvelteKit Frontend**: 已经通过 `npm run build` 构建成了一套纯静态文件。

## 1. 服务器初始化

在一台全新的阿里云Ubuntu服务器上，首先需要安装基础环境。

```bash
# 更新软件包列表
sudo apt update && sudo apt upgrade -y

# 安装Python 3.10+ 和 pip
sudo apt install python3 python3-pip python3-venv -y

# 安装Node.js 18+ 和 npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 安装Nginx 和 Git
sudo apt install nginx git -y

# 验证安装
python3 --version
node --version
npm --version
nginx -v
git --version
```

## 2. 获取并部署代码

我们提供了一个自动化的Python部署脚本来完成大部分繁琐的工作。

```bash
# 1. 从你的代码仓库克隆项目
git clone <你的项目git仓库地址> rebirth_game
cd rebirth_game

# 2. 运行自动化部署脚本
python3 deploy.py
```

`deploy.py` 脚本将会自动完成以下所有工作：
- 创建一个Python虚拟环境 (`.venv`)。
- 安装所有Python依赖 (`requirements.txt`)。
- 运行数据库迁移 (`alembic upgrade head`)。
- 安装前端Node.js依赖。
- 构建生产环境的前端静态文件 (`frontend-web/build`)。

## 3. 配置Nginx

这是最关键的一步。你需要告诉Nginx如何处理请求。

**a. 创建Nginx配置文件**

```bash
# 使用nano编辑器创建一个新的配置文件
sudo nano /etc/nginx/sites-available/rebirth_game
```

**b. 粘贴以下内容**

将下面的配置**完整地**复制并粘贴到 `nano` 编辑器中。

**注意**: 你需要把 `your_domain.com` 替换成你的服务器IP地址或域名。

```nginx
server {
    listen 80;
    server_name your_domain.com; # <-- 修改这里

    # 定义项目根目录
    root /root/rebirth_game/frontend-web/build; # <-- 确认你的项目路径
    index index.html;

    # 处理API请求，转发给Gunicorn
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /auth {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 处理所有其他请求（前端路由）
    # SvelteKit的静态Adapter需要这个try_files规则
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**c. 启用配置**

```bash
# 创建一个符号链接来启用这个配置
sudo ln -s /etc/nginx/sites-available/rebirth_game /etc/nginx/sites-enabled/

# 移除默认的配置，防止冲突
sudo rm /etc/nginx/sites-enabled/default

# 测试Nginx配置是否有语法错误
sudo nginx -t
# 如果显示 "syntax is ok" 和 "test is successful"，则说明配置正确

# 重启Nginx使配置生效
sudo systemctl restart nginx
```

## 4. 使用控制脚本管理应用

我们提供了一个 `control.sh` 脚本来轻松地启动、停止和重启你的应用。

```bash
# 赋予脚本执行权限
chmod +x control.sh

# 启动应用 (Gunicorn + Nginx)
./control.sh start

# 停止应用
./control.sh stop

# 重启应用
./control.sh restart
```

启动成功后，你的应用就可以通过服务器的IP地址或域名进行访问了！

## 5. 日常维护

- **查看后端日志**: `tail -f gunicorn.log`
- **更新代码**:
  ```bash
  git pull
  ./control.sh stop
  python3 deploy.py # 重新安装依赖和构建
  ./control.sh start

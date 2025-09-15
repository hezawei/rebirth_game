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

请根据你的服务器操作系统，选择对应的命令。

### **选项A: Ubuntu / Debian 系统**

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
```

### **选项B: Alibaba Cloud Linux / CentOS / Red Hat 系统**

**注意**: 如果你选择了这个选项，请在本指南的后续步骤中，始终选择为 "Alibaba Cloud/CentOS" 准备的命令。

**1. 安装编译依赖和基础工具**
```bash
sudo dnf update -y
sudo dnf groupinstall "Development Tools" -y
sudo dnf install -y zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel git nginx nodejs
```

**2. 安装 `pyenv` (Python版本管理器)**
```bash
# 使用Gitee镜像进行加速安装，避免从GitHub下载卡顿
git clone https://gitee.com/pyenv/pyenv.git ~/.pyenv
```

**3. 配置 `pyenv` 环境变量**
```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
```
*注意: 执行 `source` 后，你的命令行提示符可能会变化，这是正常的。*

**4. 使用 `pyenv` 安装 Python 3.10 (配置镜像)**
```bash
# 将镜像配置和安装命令放在同一行，确保环境变量生效
export PYTHON_BUILD_MIRROR_URL="http://mirrors.sohu.com/python/" && pyenv install 3.10.13

# 设置全局Python版本为我们刚刚安装的版本
pyenv global 3.10.13
```
*如果 `pyenv install` 过程中提示缺少依赖，请根据提示使用 `sudo dnf install <包名>` 来安装。*

**5. 安装 Node.js (如果上一步没装)**
```bash
sudo dnf module install nodejs:18 -y
```

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
# pyenv已经将python3命令指向了3.10.13版本
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

- **Ubuntu**: `sudo nano /etc/nginx/sites-available/rebirth_game`
- **Alibaba Cloud/CentOS**: `sudo nano /etc/nginx/conf.d/rebirth_game.conf`

请根据你的系统选择对应的路径。

**b. 粘贴以下内容**

将下面的配置**完整地**复制并粘贴到 `nano` 编辑器中。这份配置是纯粹的 `server` 块，不包含任何会导致错误的全局指令。

**注意**: 你需要把 `your_domain.com` 替换成你的服务器IP地址或域名。

```nginx
server {
    listen 80;
    server_name your_domain.com; # <-- 修改这里

    # 定义项目根目录
    root /root/rebirth_game/frontend-web/build; # <-- 确认你的项目路径
    index index.html;

    # API requests proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend routing for Single Page Application
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**c. 启用配置**

- **Ubuntu**:
  ```bash
  # 创建一个符号链接来启用这个配置
  sudo ln -s /etc/nginx/sites-available/rebirth_game /etc/nginx/sites-enabled/
  # 移除默认的配置，防止冲突
  sudo rm /etc/nginx/sites-enabled/default
  ```
- **Alibaba Cloud/CentOS**:
  在 `conf.d` 目录中创建的 `.conf` 文件会自动被加载，通常无需创建符号链接。

然后，继续执行以下通用命令：

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

**如果无法访问，请检查下一步！**

## 5. 配置阿里云安全组 (关键一步)

默认情况下，云服务器的防火墙（安全组）是关闭了80端口的，你需要手动开启它。

1.  登录到你的**阿里云控制台**。
2.  找到并进入 **弹性计算 > ECS** 服务。
3.  在左侧菜单栏中，找到 **网络与安全 > 安全组**。
4.  找到你的服务器正在使用的那个安全组（通常在服务器实例详情里能看到），点击右侧的 **配置规则**。
5.  在规则页面，选择 **入方向** 标签页，然后点击 **手动添加**。
6.  按照以下内容，添加一条新的规则：
    - **授权策略**: `允许`
    - **协议类型**: `自定义 TCP`
    - **端口范围**: `80/80`
    - **授权对象**: `0.0.0.0/0`
7.  点击 **保存**。

规则添加后，通常会立即生效。现在，你应该就能通过 `http://你的IP地址` 访问你的游戏了。

## 6. 日常维护

- **查看后端日志**: `tail -f gunicorn.log`
- **更新代码**:
  ```bash
  git pull
  ./control.sh stop
  python3 deploy.py # 重新安装依赖和构建
  ./control.sh start

---

## 附录：网络故障时的手动安装Python

如果 `pyenv install` 命令因为网络问题卡住，请按照以下步骤进行手动安装：

**1. 在你的本地电脑上操作**

   a. 打开浏览器，下载Python 3.10.13的源码包。
      下载地址: `https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tar.xz`

   b. 将下载好的 `Python-3.10.13.tar.xz` 文件上传到你的阿里云服务器。你可以使用 `scp` (Mac/Linux) 或 `WinSCP` / `MobaXterm` 的图形化上传功能。
      假设你把它上传到了服务器的 `/root` 目录下。

**2. 在你的阿里云服务器上操作**

   a. `pyenv` 有一个专门存放下载缓存的目录，我们需要创建它，并将文件放进去。
      ```bash
      # 创建缓存目录
      mkdir -p ~/.pyenv/cache

      # 将你上传的文件移动到缓存目录
      mv /root/Python-3.10.13.tar.xz ~/.pyenv/cache/
      ```

   b. 现在，重新运行安装命令。
      ```bash
      pyenv install 3.10.13
      ```
      这一次，`pyenv` 会检测到缓存目录中已经有了它需要的文件，于是会**跳过整个下载步骤**，直接开始编译安装。

   c. 安装成功后，继续执行指南中 `pyenv global 3.10.13` 及之后的步骤。

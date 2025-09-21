# AI Rebirth Game - 自动化部署指南

本文档描述了将此项目部署到一台新的阿里云 ECS 服务器的完整、自动化流程。

## 技术架构

- **云服务**: 阿里云 ECS (Ubuntu 22.04 LTS)
- **容器化**: Docker
- **Web 服务器**: Nginx (作为反向代理)
- **应用服务器**: Gunicorn + Uvicorn
- **CI/CD**: GitHub Actions

## 部署流程概览

整个流程分为两部分：
1.  **一次性服务器初始化**: 在一台全新的服务器上运行一个脚本，完成所有环境配置。
2.  **日常开发与手动部署**: 开发者在本地推送代码后，登录服务器并运行一个部署脚本来完成更新。

---

## Part 1: 一次性服务器初始化

假设你已经购买了一台新的、安装了 Ubuntu 22.04 的阿里云 ECS 实例。

### 步骤 1: SSH 登录服务器

使用你的 SSH 客户端登录到服务器。

```bash
ssh your_user@your_server_ip
```

### 步骤 2: 运行一键初始化脚本

`setup_server.sh` 脚本会自动完成所有必需的软件安装和配置，包括 Docker, Nginx, 防火墙和反向代理。

1.  在服务器上，创建一个新文件：
    ```bash
    nano setup_server.sh
    ```

2.  将项目根目录下的 `setup_server.sh` 文件的**全部内容**复制并粘贴到 nano 编辑器中。

3.  保存并退出 (`Ctrl+X`, `Y`, `Enter`)。

4.  赋予脚本执行权限：
    ```bash
    chmod +x setup_server.sh
    ```

5.  以 root 权限运行脚本：
    ```bash
    sudo ./setup_server.sh
    ```

脚本执行完毕后，服务器就已经准备就绪，可以接收应用部署了。

---

## Part 2: 准备项目仓库

为了让服务器能够拉取代码，我们需要在服务器上克隆 GitHub 仓库并配置访问权限。

### 步骤 1: 生成服务器专用的 SSH 密钥

为了让服务器能从**私有** GitHub 仓库拉取代码，需要为其配置一个专用的只读 SSH 密钥。

1.  在**服务器**上运行以下命令生成密钥对：
    ```bash
    # -N '' 表示不设置密码，方便脚本自动执行
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/github_readonly_key -N '' -C "server-readonly-key"
    ```

2.  获取公钥内容：
    ```bash
    cat ~/.ssh/github_readonly_key.pub
    ```

3.  复制输出的公钥内容。

### 步骤 2: 在 GitHub 中添加部署密钥 (Deploy Key)

1.  进入项目 GitHub 仓库的 `Settings` > `Deploy keys` 页面。
2.  点击 `Add deploy key`。
3.  **Title**: 任意填写，例如 `Aliyun ECS Deploy Key`。
4.  **Key**: 粘贴你上一步复制的**公钥** (`github_readonly_key.pub` 的内容)。
5.  **不要**勾选 `Allow write access`，因为服务器只需要读取代码。
6.  点击 `Add key`。

### 步骤 3: 在服务器上克隆项目

1.  在服务器上，选择一个位置存放项目（例如用户主目录 `~/`）。
    ```bash
    cd ~
    ```

2.  使用 **SSH 地址**克隆你的仓库：
    ```bash
    # 将地址替换为你自己仓库的 SSH 地址
    git clone git@github.com:YourUsername/rebirth_game.git
    ```

---

## Part 3: 日常开发与手动部署

完成以上所有配置后，你的手动部署流程已经完全打通。

### 开发流程

1.  在本地进行代码开发和修改。
2.  完成后，提交代码并推送到 `main` 分支：
    ```bash
    git add .
    git commit -m "你的提交信息"
    git push origin main
    ```

### 部署流程

1.  SSH 登录到你的阿里云服务器。

2.  进入项目目录：
    ```bash
    cd ~/rebirth_game
    ```

3.  运行一键部署脚本：
    ```bash
    ./deploy.sh
    ```

脚本会自动拉取最新代码、构建镜像并重启服务。部署完成后，你的所有更新就已生效。

### 本地开发

使用 `manage.py` 脚本进行本地开发：

-   启动所有服务: `python manage.py start`
-   仅清理端口: `python manage.py cleanup`

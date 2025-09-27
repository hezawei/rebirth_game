import subprocess
import platform
import os
import socket
import time
import argparse
import sys
import shutil

# --- 配置 --- #
# 本地开发配置
BACKEND_PORT = 8000
BACKEND_COMMAND = "uvicorn backend.main:app --host 0.0.0.0 --port {port} --reload --reload-exclude 'assets/generated_images'"

# 前端配置 (假设仍在 frontend-web 目录并使用 npm)
FRONTEND_DIR = "frontend-web"
FRONTEND_PORT = 5173
FRONTEND_COMMAND = "npm run dev"

# 服务器部署配置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(PROJECT_ROOT, "deployment", "configs", "docker-compose.yml")

# --- 核心功能 --- #

# --- 默认数据库容器配置（仅当未提供 DATABASE_URL 时启用） --- #
DEFAULT_PG_USER = "rebirth"
DEFAULT_PG_PASSWORD = "StrongPass!"
DEFAULT_PG_PASSWORD_ENC = "StrongPass%21"  # URL编码后的密码
DEFAULT_PG_DB = "rebirth"
PG_CONTAINER_NAME = "rebirth-pg"

def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def _docker_available() -> bool:
    return shutil.which("docker") is not None

def _docker_compose_available() -> bool:
    """检查docker compose命令是否可用"""
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "compose", "version"], 
        capture_output=True, check=False
    ).returncode == 0

def _is_server_environment() -> bool:
    """检测是否为服务器环境（Docker Compose部署）"""
    # 检查基本条件
    has_compose_file = os.path.exists(COMPOSE_FILE)
    has_docker_compose = _docker_compose_available()
    
    # 检查操作系统 - Windows通常是本地开发环境
    is_windows = platform.system() == "Windows"
    
    # 检查当前工作目录是否在典型服务器路径
    current_path = os.getcwd()
    is_server_path = any(current_path.startswith(path) for path in ['/root/', '/opt/', '/home/', '/var/'])
    
    # 检查是否有node_modules（本地开发环境的标志）
    has_node_modules = os.path.exists(os.path.join(FRONTEND_DIR, 'node_modules'))
    
    # 检查是否有运行中的项目容器
    has_running_containers = False
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=rebirth-", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            has_running_containers = True
    except:
        pass
    
    # 调试输出
    print(f"[DEBUG] OS: {platform.system()}")
    print(f"[DEBUG] COMPOSE_FILE: {COMPOSE_FILE}, exists: {has_compose_file}")
    print(f"[DEBUG] Docker Compose available: {has_docker_compose}")
    print(f"[DEBUG] Running containers: {has_running_containers}")
    print(f"[DEBUG] Server path: {is_server_path} (cwd: {current_path})")
    print(f"[DEBUG] Node modules: {has_node_modules}")
    
    # 服务器环境判定逻辑（优先级从高到低）：
    # 1. Windows系统 = 本地开发环境（除非明确在Linux容器中）
    if is_windows:
        return False
    
    # 2. Linux + 在服务器典型路径 + 有Docker Compose = 服务器
    if is_server_path and has_compose_file and has_docker_compose:
        return True
        
    # 3. Linux + 没有本地node_modules + 有Docker + 有运行容器 = 服务器  
    if not has_node_modules and has_compose_file and has_docker_compose and has_running_containers:
        return True
    
    # 4. 默认为本地开发环境
    return False

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)

def _docker_container_exists(name: str) -> bool:
    res = _run(["docker", "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"])
    return name in res.stdout.split()

def _docker_container_running(name: str) -> bool:
    res = _run(["docker", "ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"])
    return name in res.stdout.split()

def _docker_get_mapped_port(name: str, container_port: int = 5432) -> int | None:
    res = _run(["docker", "port", name, str(container_port)])
    if res.returncode != 0:
        return None
    # 输出示例: "0.0.0.0:5432" 或 "127.0.0.1:5433"
    line = res.stdout.strip().splitlines()[0] if res.stdout.strip() else ""
    if ":" in line:
        try:
            return int(line.rsplit(":", 1)[-1])
        except ValueError:
            return None
    return None

def _choose_free_port(candidates=(5432, 5433, 5434)) -> int:
    for p in candidates:
        if not _is_port_open("127.0.0.1", p):
            return p
    return candidates[-1]

def ensure_postgres_ready_and_env():
    """确保本机存在可用的PostgreSQL实例，并设置必要的环境变量。

    策略：
    - 如果已设置 DATABASE_URL（以 postgresql 开头），直接返回。
    - 未设置：尝试使用 Docker 自动启动/复用名为 rebirth-pg 的容器。
      - 若容器存在则启动之，并解析映射端口；
      - 否则选择一个空闲主机端口（5432/5433/5434），创建容器，等待就绪；
      - 设置 os.environ['DATABASE_URL'] 和 os.environ['ENFORCE_DB_VENDOR']。
    - 若本机无 Docker，则提示用户设置 DATABASE_URL（保持单命令思路但给出明确指引）。
    """
    current_url = os.environ.get("DATABASE_URL", "")
    if current_url and current_url.lower().startswith("postgresql"):
        # 已由用户配置
        os.environ.setdefault("ENFORCE_DB_VENDOR", "postgresql")
        print(f"检测到外部 DATABASE_URL，跳过容器启动。URL: {current_url}")
        return

    if not _docker_available():
        raise RuntimeError(
            "未检测到 Docker，且未提供 DATABASE_URL。请安装 Docker 或在 .env 中设置 PostgreSQL 的 DATABASE_URL。"
        )

    # 优先复用已存在的容器
    if _docker_container_exists(PG_CONTAINER_NAME):
        if not _docker_container_running(PG_CONTAINER_NAME):
            print("检测到现有 PostgreSQL 容器，正在启动...")
            res = _run(["docker", "start", PG_CONTAINER_NAME])
            if res.returncode != 0:
                print(res.stderr)
                raise RuntimeError("无法启动已有的 PostgreSQL 容器")
        mapped = _docker_get_mapped_port(PG_CONTAINER_NAME, 5432)
        if not mapped:
            raise RuntimeError("无法解析 PostgreSQL 容器映射端口")
        host_port = mapped
    else:
        # 新建容器
        host_port = _choose_free_port()
        print(f"正在创建 PostgreSQL 容器 {PG_CONTAINER_NAME} (端口 {host_port}->5432)...")
        run_cmd = [
            "docker", "run", "--name", PG_CONTAINER_NAME,
            "-e", f"POSTGRES_USER={DEFAULT_PG_USER}",
            "-e", f"POSTGRES_PASSWORD={DEFAULT_PG_PASSWORD}",
            "-e", f"POSTGRES_DB={DEFAULT_PG_DB}",
            "-p", f"{host_port}:5432",
            "-d", "postgres:16"
        ]
        res = _run(run_cmd)
        if res.returncode != 0:
            print(res.stderr)
            raise RuntimeError("无法创建并启动 PostgreSQL 容器")

    # 等待端口就绪
    print("等待 PostgreSQL 就绪...")
    for i in range(120):  # 增加到120秒
        if _is_port_open("127.0.0.1", host_port):
            # 端口开放后再等待5秒确保数据库完全就绪
            print("端口已开放，等待数据库初始化完成...")
            time.sleep(5)
            break
        if i % 10 == 0:  # 每10秒显示一次进度
            print(f"等待中... ({i}/120秒)")
        time.sleep(1)
    else:
        raise RuntimeError("等待 PostgreSQL 超时，端口未就绪")

    # 设置环境变量（供后续 settings/base.py 使用）
    pg_url = f"postgresql+psycopg2://{DEFAULT_PG_USER}:{DEFAULT_PG_PASSWORD_ENC}@127.0.0.1:{host_port}/{DEFAULT_PG_DB}"
    os.environ["DATABASE_URL"] = pg_url
    os.environ["ENFORCE_DB_VENDOR"] = "postgresql"
    print(f"DATABASE_URL 已设置为: {pg_url}")

def find_pid_on_port(port):
    """根据端口号查找进程ID"""
    pids = []
    system = platform.system()  
    if system == "Windows":
        command = f'netstat -ano | findstr ":{port}"'
    else:  # macOS & Linux
        command = f'lsof -i tcp:{port}'

    try:
        result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.DEVNULL)
        lines = result.strip().split('\n')
        for line in lines:
            if system == "Windows":
                parts = line.strip().split()
                if len(parts) > 4 and parts[3] != '0': # Ensure there is a PID
                    pid = parts[-1]
                    if pid not in pids:
                        pids.append(pid)
            else:
                if 'LISTEN' in line:
                    parts = line.strip().split()
                    if len(parts) > 1:
                        pid = parts[1]
                        if pid not in pids:
                            pids.append(pid)
    except subprocess.CalledProcessError:
        # 命令未找到任何监听该端口的进程，这是正常情况
        pass
    return pids

def kill_processes(pids):
    """根据PID列表终止进程"""
    for pid in pids:
        try:
            if platform.system() == "Windows":
                subprocess.run(f"taskkill /F /PID {pid}", check=True, shell=True, capture_output=True)
                print(f"成功终止进程 {pid}")
            else:
                subprocess.run(f"kill -9 {pid}", check=True, shell=True, capture_output=True)
                print(f"成功终止进程 {pid}")
        except subprocess.CalledProcessError as e:
            print(f"终止进程 {pid} 失败: {e.stderr.decode('gbk', 'ignore')}")

def cleanup_ports():
    """清理前后端占用的端口"""
    print("--- 1. 正在清理端口 --- ")
    backend_pids = find_pid_on_port(BACKEND_PORT)
    if backend_pids:
        print(f"发现后端端口 {BACKEND_PORT} 被占用，正在尝试终止...")
        kill_processes(backend_pids)
    else:
        print(f"后端端口 {BACKEND_PORT} 未被占用。")

    frontend_pids = find_pid_on_port(FRONTEND_PORT)
    if frontend_pids:
        print(f"发现前端端口 {FRONTEND_PORT} 被占用，正在尝试终止...")
        kill_processes(frontend_pids)
    else:
        print(f"前端端口 {FRONTEND_PORT} 未被占用。")
    print("端口清理完成。\n")

def start_backend():
    """在当前终端的后台启动后端服务"""
    print("--- 2. 正在启动后端服务 --- ")
    command = BACKEND_COMMAND.format(port=BACKEND_PORT)
    print(f"执行命令: {command}")
    # 使用 Popen 在后台运行，不打开新窗口，输出会保留在当前终端
    process = subprocess.Popen(command, shell=True)
    print(f"后端服务已在后台启动，进程ID: {process.pid}，端口: {BACKEND_PORT}\n")
    return process

def start_frontend():
    """启动前端服务。

    - Windows：在新窗口中运行，便于查看日志。
    - macOS/Linux（有GUI）：尝试打开新终端窗口。
    - 无GUI（服务器场景）：在当前终端前台运行（继承输出），绑定 0.0.0.0 以便远程访问。
    """
    print("--- 3. 正在启动前端服务 --- ")
    vite_cmd = f"npm run dev -- --host 0.0.0.0 --port {FRONTEND_PORT}"
    full_command = f"cd {FRONTEND_DIR} && {vite_cmd}"
    print(f"执行命令: {full_command}")

    system = platform.system()
    if system == "Windows":
        # 为前端打开一个新窗口
        subprocess.Popen(f'start cmd /k "{full_command}"', shell=True)
        print("前端服务已在新窗口中启动，请查看新窗口。\n")
        return None
    else:
        # macOS & Linux：优先尝试GUI终端，否则在当前终端运行
        display = os.environ.get("DISPLAY")
        if display:
            # 尝试 gnome-terminal 或 xterm
            proc = subprocess.Popen(
                f'gnome-terminal -- bash -c "{full_command}; exec bash" || xterm -e "{full_command}"',
                shell=True
            )
            if proc.poll() is None:
                print("前端服务已在新窗口中启动，请查看新窗口。\n")
                return None
            # 如果打开失败，退回到当前终端
        # 无GUI：在当前终端直接运行（前台输出）
        subprocess.Popen(vite_cmd, shell=True, cwd=FRONTEND_DIR)
        print(f"前端服务已在当前终端启动，监听端口 {FRONTEND_PORT}（0.0.0.0）。\n")
        return None

def apply_db_migrations():
    """确保数据库 schema 与最新 Alembic 迁移一致（PostgreSQL-only）。

    逻辑：
    - 必须设置 DATABASE_URL，且以 postgresql 开头
    - 如果数据库尚未版本化（无 alembic_version 表）：
      - 若已存在业务表（如 story_nodes），说明此前通过 SQLAlchemy 自动建表：先 stamp 到初始版本，再 upgrade head。
      - 若不存在业务表：直接 upgrade head。
    - 如果已版本化：直接 upgrade head。
    """
    print("--- 0. 检查并应用数据库迁移 --- ")
    project_dir = os.path.dirname(os.path.abspath(__file__))

    from sqlalchemy import create_engine, inspect
    from config.settings import settings

    database_url = getattr(settings, 'database_url', None)
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set for PostgreSQL")
    if not database_url.lower().startswith("postgresql"):
        raise RuntimeError(f"Only PostgreSQL is supported. Got: {database_url}")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    has_alembic = inspector.has_table('alembic_version')
    has_users = inspector.has_table('users')
    has_sessions = inspector.has_table('game_sessions')
    has_nodes = inspector.has_table('story_nodes')

    if not has_alembic:
        # 数据库未版本化
        if has_users or has_sessions or has_nodes:
            print("检测到已有业务表但无 Alembic 版本信息，先进行 stamp 基线，然后升级...")
            # 基线设为首个迁移版本（创建表的版本）
            base_rev = '37691daea28a'
            _run_alembic(["stamp", base_rev], cwd=project_dir)
            _run_alembic(["upgrade", "head"], cwd=project_dir)
        else:
            print("检测到空数据库，直接执行 Alembic 升级以创建所有表...")
            _run_alembic(["upgrade", "head"], cwd=project_dir)
    else:
        print("检测到 Alembic 版本表，直接升级到最新...")
        _run_alembic(["upgrade", "head"], cwd=project_dir)

def _run_alembic(args, cwd):
    """以 python -m alembic 方式执行 Alembic 命令，提升跨平台可靠性。"""
    cmd = [sys.executable, "-m", "alembic"] + list(args)
    print(f"执行 Alembic: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
        print("Alembic 执行成功。")
    except subprocess.CalledProcessError as e:
        print("Alembic 执行失败。详情如下：")
        print(e)
        # 中断启动流程，因为数据库不可用会导致后续失败
        raise

# --- 服务器环境 Docker Compose 管理 ---

def docker_compose_start():
    """启动Docker Compose服务"""
    print("--- 启动Docker Compose服务 ---")
    if not os.path.exists(COMPOSE_FILE):
        raise RuntimeError(f"Docker Compose配置文件不存在: {COMPOSE_FILE}")
    
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"]
    print(f"执行命令: {' '.join(cmd)}")
    print(f"工作目录: {os.getcwd()}")
    result = subprocess.run(cmd, check=True)
    print("✅ Docker Compose服务启动成功")
    return result

def docker_compose_stop():
    """停止Docker Compose服务"""
    print("--- 停止Docker Compose服务 ---")
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "down"]
    print(f"执行命令: {' '.join(cmd)}")
    print(f"工作目录: {os.getcwd()}")
    result = subprocess.run(cmd, check=True)
    print("✅ Docker Compose服务已停止")
    return result

def docker_compose_restart():
    """重启Docker Compose服务"""
    print("--- 重启Docker Compose服务 ---")
    docker_compose_stop()
    time.sleep(2)
    docker_compose_start()

def docker_compose_status():
    """显示Docker Compose服务状态"""
    print("--- Docker Compose服务状态 ---")
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "ps"]
    subprocess.run(cmd)
    
    # 显示访问信息
    try:
        # 尝试获取服务器IP
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            server_ip = result.stdout.strip().split()[0]
            print(f"\n🌐 服务访问地址:")
            print(f"  主站: http://{server_ip}")
            print(f"  API文档: http://{server_ip}/docs")
    except:
        print(f"\n🌐 服务访问地址:")
        print(f"  主站: http://localhost")
        print(f"  API文档: http://localhost/docs")

def docker_compose_logs(service=None):
    """显示Docker Compose日志"""
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "logs", "-f"]
    if service:
        cmd.append(service)
        print(f"--- 显示 {service} 服务日志 ---")
    else:
        print("--- 显示所有服务日志 ---")
    
    subprocess.run(cmd)

# --- 统一服务管理 ---

def start_services():
    """启动所有服务（自动检测环境）"""
    if _is_server_environment():
        print("🔍 检测到服务器环境，使用Docker Compose管理")
        docker_compose_start()
        docker_compose_status()
    else:
        print("🔍 检测到本地开发环境，启动本地服务")
        start_local_services()

def start_local_services():
    """启动本地开发服务"""
    cleanup_ports()
    # 在启动后端前，先确保数据库迁移已应用
    # 0. 确保本机有可用的 PostgreSQL（若未配置，则自动以 Docker 启动一个本地容器）
    ensure_postgres_ready_and_env()
    # 1. 迁移
    apply_db_migrations()
    backend_process = start_backend()
    # 等待一下，确保后端服务已初步启动
    time.sleep(5)
    frontend_process = start_frontend()
    
    print("--- 所有本地服务已启动 --- ")
    print("你可以通过 Ctrl+C 来停止此脚本，但这只会关闭 manage.py。")
    print("后端服务将在后台继续运行。你可以通过再次运行 `python manage.py start` 来清理端口并重启。")

    # 保持主脚本运行，以便捕获 Ctrl+C
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n检测到 Ctrl+C，正在关闭... (注意：这只会关闭此脚本，后台进程可能需要手动清理或通过再次运行脚本来清理)")

def stop_services():
    """停止所有服务（自动检测环境）"""
    if _is_server_environment():
        print("🔍 检测到服务器环境，停止Docker Compose服务")
        docker_compose_stop()
    else:
        print("🔍 检测到本地开发环境，清理本地端口")
        cleanup_ports()

def restart_services():
    """重启所有服务（自动检测环境）"""
    if _is_server_environment():
        print("🔍 检测到服务器环境，重启Docker Compose服务")
        docker_compose_restart()
    else:
        print("🔍 检测到本地开发环境，重启本地服务")
        start_local_services()

# --- 主程序入口 --- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Rebirth Game 统一管理脚本 (支持本地开发 + 服务器部署)")
    subparsers = parser.add_subparsers(dest="command", help="可用的命令")

    # 通用命令（自动检测环境）
    start_parser = subparsers.add_parser("start", help="启动服务（自动检测本地/服务器环境）")
    start_parser.set_defaults(func=start_services)

    stop_parser = subparsers.add_parser("stop", help="停止服务（自动检测本地/服务器环境）")
    stop_parser.set_defaults(func=stop_services)

    restart_parser = subparsers.add_parser("restart", help="重启服务（自动检测本地/服务器环境）")
    restart_parser.set_defaults(func=restart_services)

    # 本地开发专用命令
    cleanup_parser = subparsers.add_parser("cleanup", help="[本地] 清理被占用的端口")
    cleanup_parser.set_defaults(func=cleanup_ports)

    # 服务器专用命令
    status_parser = subparsers.add_parser("status", help="[服务器] 显示Docker Compose服务状态")
    status_parser.set_defaults(func=docker_compose_status)

    logs_parser = subparsers.add_parser("logs", help="[服务器] 显示服务日志")
    logs_parser.add_argument("service", nargs="?", help="指定服务名 (app/db/nginx)，不指定则显示所有")
    logs_parser.set_defaults(func=lambda: docker_compose_logs(getattr(parser.parse_args(), 'service', None)))

    args = parser.parse_args()

    # 环境检测提示
    if _is_server_environment():
        print("🖥️  当前环境: 服务器 (Docker Compose)")
    else:
        print("💻 当前环境: 本地开发")
    
    if hasattr(args, 'func'):
        try:
            args.func()
        except KeyboardInterrupt:
            print("\n操作已取消")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            sys.exit(1)
    else:
        parser.print_help()

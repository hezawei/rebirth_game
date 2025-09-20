import subprocess
import platform
import os
import socket
import time
import argparse

# --- 配置 --- #
# 后端配置
BACKEND_PORT = 8000
BACKEND_COMMAND = "uvicorn backend.main:app --host 0.0.0.0 --port {port} --reload"

# 前端配置 (假设仍在 frontend-web 目录并使用 npm)
FRONTEND_DIR = "frontend-web"
FRONTEND_PORT = 5173
FRONTEND_COMMAND = "npm run dev"

# --- 核心功能 --- #

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
    """在新的终端窗口中启动前端服务（前端通常需要一个专门的窗口来看日志和热更新）"""
    print("--- 3. 正在启动前端服务 --- ")
    full_command = f"cd {FRONTEND_DIR} && {FRONTEND_COMMAND}"
    print(f"执行命令: {full_command}")
    
    system = platform.system()
    if system == "Windows":
        # 仍然为前端打开一个新窗口，因为前端开发服务器的输出非常多
        subprocess.Popen(f'start cmd /k "{full_command}"', shell=True)
    else: # macOS & Linux
        # 行为可能取决于默认终端
        subprocess.Popen(f'gnome-terminal -- bash -c "{full_command}; exec bash" || xterm -e "{full_command}"', shell=True)
    
    print(f"前端服务已在新窗口中启动，请查看新窗口。\n")
    return None

def start_services():
    """启动所有开发服务"""
    cleanup_ports()
    backend_process = start_backend()
    # 等待一下，确保后端服务已初步启动
    time.sleep(5)
    frontend_process = start_frontend()
    
    print("--- 所有服务已启动 --- ")
    print("你可以通过 Ctrl+C 来停止此脚本，但这只会关闭 manage.py。")
    print("后端服务将在后台继续运行。你可以通过再次运行 `python manage.py start` 来清理端口并重启。")

    # 保持主脚本运行，以便捕获 Ctrl+C
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n检测到 Ctrl+C，正在关闭... (注意：这只会关闭此脚本，后台进程可能需要手动清理或通过再次运行脚本来清理)")

# --- 主程序入口 --- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Rebirth Game 本地开发管理脚本")
    subparsers = parser.add_subparsers(dest="command", help="可用的命令")

    # 'start' 命令
    start_parser = subparsers.add_parser("start", help="清理端口并启动本地开发服务器")
    start_parser.set_defaults(func=start_services)

    # 'cleanup' 命令
    cleanup_parser = subparsers.add_parser("cleanup", help="仅清理被占用的端口")
    cleanup_parser.set_defaults(func=cleanup_ports)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func()
    else:
        parser.print_help()

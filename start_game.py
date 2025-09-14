import os
import subprocess
import platform
import time
import socket

# --- 配置 ---
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
FRONTEND_DIR = "frontend-web"
BACKEND_COMMAND = "uvicorn backend.main:app --host 0.0.0.0 --port {port}"
FRONTEND_COMMAND = "npm run dev"

def find_pid_on_port(port):
    """根据端口号查找进程ID"""
    pids = []
    system = platform.system()
    try:
        if system == "Windows":
            command = f"netstat -aon | findstr :{port}"
            result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in result.strip().split('\n'):
                if "LISTENING" in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    pids.append(pid)
        else: # macOS & Linux
            command = f"lsof -ti :{port}"
            result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.DEVNULL)
            for pid in result.strip().split('\n'):
                if pid:
                    pids.append(pid)
    except subprocess.CalledProcessError:
        # 如果命令失败（例如，没有找到进程），则忽略错误
        pass
    return list(set(pids)) # 返回去重后的PID列表

def kill_processes(pids):
    """根据PID列表终止进程"""
    if not pids:
        return
    
    system = platform.system()
    for pid in pids:
        try:
            if system == "Windows":
                command = f"taskkill /F /PID {pid}"
                subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                command = f"kill -9 {pid}"
                subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  - 成功终止进程 {pid}")
        except subprocess.CalledProcessError:
            print(f"  - 终止进程 {pid} 失败 (可能已关闭)")

def cleanup_ports():
    """清理前后端端口"""
    print("--- 1. 正在清理端口 ---")
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
    """在新的终端窗口中启动后端服务"""
    print("--- 2. 正在启动后端服务 ---")
    command = BACKEND_COMMAND.format(port=BACKEND_PORT)
    print(f"执行命令: {command}")
    
    if platform.system() == "Windows":
        subprocess.Popen(f'start cmd /k "{command}"', shell=True)
    else: # macOS & Linux
        # 在macOS上，这会打开一个新的终端应用窗口
        # 在Linux上，行为可能取决于默认终端
        subprocess.Popen(f'gnome-terminal -- bash -c "{command}; exec bash" || xterm -e "{command}"', shell=True)
    print(f"后端服务已在端口 {BACKEND_PORT} 的新窗口中启动。\n")

def start_frontend():
    """在新的终端窗口中启动前端服务"""
    print("--- 3. 正在启动前端服务 ---")
    print(f"切换目录到: {FRONTEND_DIR}")
    
    full_command = f"cd {FRONTEND_DIR} && {FRONTEND_COMMAND}"
    
    if platform.system() == "Windows":
        subprocess.Popen(f'start cmd /k "{full_command}"', shell=True)
    else: # macOS & Linux
        subprocess.Popen(f'gnome-terminal -- bash -c "{full_command}; exec bash" || xterm -e "{full_command}"', shell=True)
    print(f"前端服务已在端口 {FRONTEND_PORT} 的新窗口中启动。\n")

def main():
    """主函数"""
    print("==============================")
    print("  重生之旅 - 游戏启动脚本  ")
    print("==============================\n")
    
    cleanup_ports()
    time.sleep(1) # 等待端口释放
    
    start_backend()
    time.sleep(2) # 错开启动时间，避免资源竞争
    
    start_frontend()
    
    print("--- 4. 启动完成 ---")
    print("请检查新打开的两个终端窗口，确保服务都已正常运行。")
    print(f"游戏入口: http://localhost:{FRONTEND_PORT} (当前端服务编译完成后)")
    print("==============================")

if __name__ == "__main__":
    # 将工作目录设置为脚本所在的目录，以确保路径正确
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    main()

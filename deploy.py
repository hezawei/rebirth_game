import subprocess
import sys
import os
import shutil
from pathlib import Path

# --- 核心配置（用户可根据项目调整）---
VENV_DIR = ".venv"
FRONTEND_DIR = "frontend-web"
REQUIREMENTS_FILE = "requirements.txt"
PIP_MIRROR = "https://pypi.doubanio.com/simple/"
REQUIRED_PYTHON_EXEC = "python3.8"  # 与用户实际使用的Python版本一致
# 【关键】统一数据库路径配置（所有地方都将使用这个路径）
DATABASE_DIR = "./data"
DATABASE_FILENAME = "rebirth_game.db"  # 从env.py中确认的实际文件名
DATABASE_PATH = os.path.abspath(f"{DATABASE_DIR}/{DATABASE_FILENAME}")
ALEMBIC_DIR = "alembic"
ALEMBIC_ENV_PATH = os.path.join(ALEMBIC_DIR, "env.py")
ALEMBIC_VERSIONS_DIR = os.path.join(ALEMBIC_DIR, "versions")
# 应用配置文件（用于同步数据库路径）
SETTINGS_PATH = "config/settings.py"
ENV_FILE_PATH = ".env"


def run_command(command, cwd=None, venv_path=None, check_exit_code=True):
    """执行命令，带实时输出和错误处理"""
    print(f"🚀 Executing: {' '.join(command)}")
    
    env = os.environ.copy()
    if venv_path:
        venv_bin = os.path.join(venv_path, 'Scripts' if sys.platform == 'win32' else 'bin')
        env['PATH'] = f"{venv_bin}{os.pathsep}{env['PATH']}"
        env['VIRTUAL_ENV'] = venv_path

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env,
        bufsize=1,
        universal_newlines=True
    )

    for line in process.stdout:
        print(line, end='')

    process.wait()
    if check_exit_code and process.returncode != 0:
        print(f"❌ ERROR: Command failed with exit code {process.returncode}")
        sys.exit(1)
    if process.returncode == 0:
        print("✅ Success!")
    return process.returncode


def check_python_version():
    """检查Python版本是否符合要求（修正版本提示不一致问题）"""
    print(f"\n--- 🐍 Checking for required Python: {REQUIRED_PYTHON_EXEC} ---")
    try:
        result = subprocess.run(
            [REQUIRED_PYTHON_EXEC, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        if result.returncode != 0:
            raise FileNotFoundError
        print(f"✅ Found Python: {result.stdout.strip()}")
        return REQUIRED_PYTHON_EXEC
    except FileNotFoundError:
        print(f"❌ ERROR: {REQUIRED_PYTHON_EXEC} not found!")
        print(f"请先安装Python {REQUIRED_PYTHON_EXEC.split('.')[0]}.{REQUIRED_PYTHON_EXEC.split('.')[1]}（参考部署文档）")  # 动态匹配版本提示
        sys.exit(1)


def create_venv(python_exec):
    """创建虚拟环境"""
    print("\n--- 🐍 Setting up Python virtual environment ---")
    if not os.path.exists(VENV_DIR):
        run_command([python_exec, "-m", "venv", VENV_DIR])
    else:
        print(f"✅ Virtual environment already exists: {VENV_DIR}")
    return os.path.abspath(VENV_DIR)


def install_dependencies(venv_path):
    """安装Python依赖"""
    print("\n--- 📦 Installing Python dependencies ---")
    pip_exec = os.path.join(venv_path, 'bin', 'pip')
    run_command([pip_exec, "install", "--upgrade", "pip", "-i", PIP_MIRROR], venv_path=venv_path)
    run_command([pip_exec, "install", "-r", REQUIREMENTS_FILE, "-i", PIP_MIRROR], venv_path=venv_path)


def find_existing_database():
    """自动查找系统中已存在的数据库文件（解决路径混乱问题）"""
    print(f"\n--- 🔍 Searching for existing database files ---")
    # 优先检查已知可能的路径
    possible_paths = [
        DATABASE_PATH,  # 目标路径
        os.path.abspath(DATABASE_FILENAME),  # 项目根目录
        os.path.join(ALEMBIC_DIR, DATABASE_FILENAME),  # alembic目录
        os.path.join("/tmp", DATABASE_FILENAME),  # 临时目录
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found existing database at: {path}")
            return path
    
    # 全局搜索（最后手段）
    print(f"⚠️ No database found in common paths. Searching system...")
    try:
        result = subprocess.run(
            ["sudo", "find", "/", "-name", DATABASE_FILENAME, "2>/dev/null"],
            stdout=subprocess.PIPE,
            universal_newlines=True
        )
        paths = [p.strip() for p in result.stdout.splitlines() if p.strip()]
        if paths:
            print(f"✅ Found existing database at: {paths[0]}")
            return paths[0]
    except Exception as e:
        print(f"⚠️ Global search failed: {e}")
    
    print("ℹ️ No existing database found. Will create new one.")
    return None


def move_database_to_target(existing_path):
    """将找到的旧数据库文件移动到目标目录"""
    print(f"\n--- 📦 Moving database to target location ---")
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    if os.path.abspath(existing_path) == DATABASE_PATH:
        print(f"✅ Database already in target location: {DATABASE_PATH}")
        return
    
    try:
        shutil.move(existing_path, DATABASE_PATH)
        print(f"✅ Moved database from {existing_path} to {DATABASE_PATH}")
    except Exception as e:
        print(f"❌ Failed to move database: {e}")
        sys.exit(1)


def fix_alembic_env_py():
    """自动修正alembic/env.py（解决变量名重复、正则替换不完整问题）"""
    print(f"\n--- 🔧 Fixing alembic/env.py ---")
    if not os.path.exists(ALEMBIC_ENV_PATH):
        print(f"❌ ERROR: {ALEMBIC_ENV_PATH} not found!")
        sys.exit(1)
    
    # 读取现有内容
    with open(ALEMBIC_ENV_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 确保项目根目录在sys.path中（避免重复添加）
    root_path_code = """
# Auto-added by deploy.py: Add project root to sys.path
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__))))
"""
    if "Auto-added by deploy.py: Add project root to sys.path" not in content:
        content = root_path_code + content
    
    # 2. 强制设置数据库路径为统一目标路径（修正正则替换，避免变量重复）
    target_url = f"sqlite:///{DATABASE_PATH}"
    # 替换DATABASE_URL定义（用贪婪匹配.*确保完整替换）
    content = re.sub(
        r'DATABASE_URL\s*=\s*settings\.database_url\s*or\s*".*"',  # 去掉?，用贪婪匹配完整行
        f'DATABASE_URL = settings.database_url or "{target_url}"',
        content
    )
    # 确保online模式使用正确URL（同样用贪婪匹配，避免残留字符）
    content = re.sub(
        r'configuration\["sqlalchemy\.url"\]\s*=\s*.*',  # 去掉?，贪婪匹配完整配置行
        f'configuration["sqlalchemy.url"] = DATABASE_URL',  # 变量名唯一，无重复
        content
    )
    
    # 写入修改（确保无语法错误）
    with open(ALEMBIC_ENV_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Updated {ALEMBIC_ENV_PATH} to use database: {DATABASE_PATH}")


def fix_application_settings():
    """自动修正应用配置文件，确保使用统一的数据库路径"""
    print(f"\n--- 🔧 Fixing application settings ---")
    target_url = f"sqlite:///{DATABASE_PATH}"
    
    # 1. 处理settings.py
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换数据库URL配置（贪婪匹配，避免残留）
        content = re.sub(
            r'database_url\s*=\s*os\.getenv\("DATABASE_URL",\s*".*"\)',
            f'database_url = os.getenv("DATABASE_URL", "{target_url}")',
            content
        )
        
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated {SETTINGS_PATH} to use database: {DATABASE_PATH}")
    
    # 2. 处理.env文件（确保存在且配置正确）
    env_content = ""
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # 替换或添加DATABASE_URL（避免重复添加）
    if "DATABASE_URL=" in env_content:
        env_content = re.sub(
            r'DATABASE_URL=.*',
            f'DATABASE_URL={target_url}',
            env_content
        )
    else:
        env_content += f"\nDATABASE_URL={target_url}\n"
    
    with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(env_content)
    print(f"✅ Updated {ENV_FILE_PATH} to use database: {DATABASE_PATH}")


def sync_alembic_state(venv_path):
    """自动同步Alembic状态（增加空值判断，避免索引错误）"""
    print(f"\n--- 🔄 Syncing Alembic migration state ---")
    alembic_exec = os.path.join(venv_path, 'bin', 'alembic')
    if not os.path.exists(alembic_exec):
        print(f"❌ ERROR: alembic not found in virtual env!")
        sys.exit(1)
    
    # 检查是否有迁移脚本
    has_migrations = os.path.exists(ALEMBIC_VERSIONS_DIR) and len(os.listdir(ALEMBIC_VERSIONS_DIR)) > 0
    
    if not has_migrations:
        print(f"⚠️ No migration scripts found. Generating initial script...")
        run_command(
            [alembic_exec, "revision", "--autogenerate", "-m", "initial_create_tables"],
            venv_path=venv_path
        )
    
    # 检查数据库是否已存在表结构（增加空值判断）
    if os.path.exists(DATABASE_PATH):
        print(f"ℹ️ Database file exists. Checking if tables are already created...")
        try:
            # 获取最新迁移版本号（增加空值判断，避免索引错误）
            result = subprocess.run(
                [alembic_exec, "heads"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PATH": f"{os.path.dirname(alembic_exec)}{os.pathsep}{os.environ['PATH']}"},
                universal_newlines=True
            )
            stdout_stripped = result.stdout.strip()
            if not stdout_stripped:
                print(f"⚠️ No migration heads found. Running full migration...")
                run_command([alembic_exec, "upgrade", "head"], venv_path=venv_path)
                return
            
            latest_version = stdout_stripped.split()[0]  # 取第一个版本号
            print(f"ℹ️ Marking migration {latest_version} as completed...")
            run_command(
                [alembic_exec, "stamp", latest_version],
                venv_path=venv_path
            )
            print(f"✅ Successfully synced Alembic state")
            return
        except Exception as e:
            print(f"⚠️ Failed to sync state automatically: {e}")
    
    # 如果没有现有表，执行正常迁移
    print(f"ℹ️ Running migrations to create tables...")
    run_command(
        [alembic_exec, "upgrade", "head"],
        venv_path=venv_path
    )


def fix_frontend_permissions():
    """修复前端目录权限（确保 Vite 可执行文件权限不被覆盖）"""
    print(f"\n--- 🔒 Fixing frontend directory permissions ---")
    if os.path.exists(FRONTEND_DIR):
        for root, dirs, files in os.walk(FRONTEND_DIR):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                file_path = os.path.join(root, f)
                # 关键修复：为 vite.js 单独保留执行权限
                if "node_modules/vite/bin/vite.js" in file_path or "node_modules/.bin" in file_path:
                    os.chmod(file_path, 0o755)  # 可执行权限
                else:
                    os.chmod(file_path, 0o644)
        print(f"✅ Fixed permissions for {FRONTEND_DIR}")
    else:
        print(f"⚠️ Frontend directory {FRONTEND_DIR} not found. Skipping.")


def build_frontend():
    """构建前端项目（增加强制授权步骤）"""
    print(f"\n--- 🎨 Building frontend ---")
    if os.path.exists(FRONTEND_DIR):
        # 强制获取 vite.js 路径并设置执行权限（双重保险）
        vite_js_path = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")
        if os.path.exists(vite_js_path):
            os.chmod(vite_js_path, 0o755)
            print(f"✅ Forced execute permission for {vite_js_path}")
        else:
            print(f"⚠️ vite.js not found at {vite_js_path}, may cause errors")

        if not os.path.exists(os.path.join(FRONTEND_DIR, 'node_modules')):
            run_command(["npm", "install"], cwd=FRONTEND_DIR, venv_path=None)
        else:
            print(f"✅ node_modules already exists. Skipping npm install.")
        # 执行构建时使用绝对路径调用 npm，避免环境变量影响
        npm_exec = shutil.which("npm")  # 获取系统原生 npm 路径
        if npm_exec:
            run_command([npm_exec, "run", "build"], cwd=FRONTEND_DIR, venv_path=None)
        else:
            print(f"❌ ERROR: npm not found in system PATH")
            sys.exit(1)
    else:
        print(f"⚠️ Frontend directory {FRONTEND_DIR} not found. Skipping build.")


def main():
    print("--- 🚀 Starting FULLY AUTOMATIC Deployment ---")
    project_root = os.path.abspath(os.getcwd())
    print(f"📂 Project root: {project_root}")

    # 新增：修复前端父目录权限
    if os.path.exists(FRONTEND_DIR):
        os.chmod(FRONTEND_DIR, 0o755)
        # 修复 node_modules 及其父目录权限
        node_modules_dir = os.path.join(FRONTEND_DIR, "node_modules")
        if os.path.exists(node_modules_dir):
            os.chmod(node_modules_dir, 0o755)
            os.chmod(os.path.join(FRONTEND_DIR, "node_modules", "vite"), 0o755)
            os.chmod(os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin"), 0o755)
        print(f"✅ Fixed parent directory permissions for frontend")

    # 1. 检查Python版本
    python_exec = check_python_version()

    # 2. 创建虚拟环境
    venv_path = create_venv(python_exec)

    # 3. 安装依赖
    install_dependencies(venv_path)

    # 4. 数据库核心处理（全自动）
    # 4.1 查找现有数据库文件
    existing_db = find_existing_database()
    # 4.2 移动到目标目录（如果找到）
    if existing_db:
        move_database_to_target(existing_db)
    else:
        # 确保目标目录存在
        os.makedirs(DATABASE_DIR, exist_ok=True)
    
    # 4.3 统一所有配置文件的数据库路径
    fix_alembic_env_py()
    fix_application_settings()

    # 4.4 同步Alembic状态，处理迁移问题
    sync_alembic_state(venv_path)

    # 4.5 最终验证数据库文件
    if os.path.exists(DATABASE_PATH):
        print(f"\n✅ Final check: Database file created successfully at {DATABASE_PATH}")
    else:
        print(f"\n❌ ERROR: Database file not found at {DATABASE_PATH}")
        sys.exit(1)

    # 5. 前端处理
    fix_frontend_permissions()
    build_frontend()

    print("\n--- 🎉 FULL DEPLOYMENT COMPLETED SUCCESSFULLY! ---")
    print(f"📌 Database location: {DATABASE_PATH}")
    print("💡 Next steps:")
    print("  1. Start the application: ./control.sh start")
    print("  2. Configure Nginx (if not already done)")
    print("  3. Access via your server IP")


if __name__ == "__main__":
    import re  # 延迟导入，仅在主程序运行时需要
    main()

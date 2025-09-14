import subprocess
import sys
import os

# --- Configuration ---
VENV_DIR = ".venv"
FRONTEND_DIR = "frontend-web"
REQUIREMENTS_FILE = "requirements.txt"

def run_command(command, cwd=None, venv_path=None):
    """Runs a command in a subprocess, optionally in a specific directory and virtual environment."""
    print(f"🚀 Executing: {' '.join(command)}")
    
    env = os.environ.copy()
    if venv_path:
        # Activate virtual environment by modifying the PATH
        env['PATH'] = os.path.join(venv_path, 'bin') + os.pathsep + env['PATH']
        env['VIRTUAL_ENV'] = venv_path

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        env=env,
        bufsize=1,
        universal_newlines=True
    )

    for line in process.stdout:
        print(line, end='')

    process.wait()
    if process.returncode != 0:
        print(f"❌ ERROR: Command failed with exit code {process.returncode}")
        sys.exit(1)
    print("✅ Success!")

def main():
    """Main deployment script."""
    print("--- 🚀 Starting Deployment Process ---")
    
    # 1. Setup Python Virtual Environment
    print("\n--- 🐍 Setting up Python virtual environment ---")
    if not os.path.exists(VENV_DIR):
        run_command([sys.executable, "-m", "venv", VENV_DIR])
    else:
        print("✅ Virtual environment already exists.")
        
    # Determine the full path to the virtual environment's activate script
    venv_python_path = os.path.abspath(os.path.join(VENV_DIR, 'Scripts' if sys.platform == 'win32' else 'bin'))

    # 2. Install Python Dependencies
    print("\n--- 📦 Installing Python dependencies ---")
    pip_executable = os.path.join(venv_python_path, 'pip')
    run_command([pip_executable, "install", "-r", REQUIREMENTS_FILE])

    # 3. Run Database Migrations
    print("\n--- 🗄️ Running database migrations ---")
    alembic_executable = os.path.join(venv_python_path, 'alembic')
    run_command([alembic_executable, "upgrade", "head"])

    # 4. Setup Frontend
    print("\n--- 🎨 Setting up SvelteKit frontend ---")
    if not os.path.exists(os.path.join(FRONTEND_DIR, 'node_modules')):
        run_command(["npm", "install"], cwd=FRONTEND_DIR)
    else:
        print("✅ node_modules already exists, skipping install.")

    # 5. Build Frontend for Production
    print("\n--- 🏗️ Building frontend for production ---")
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)

    print("\n--- 🎉 Deployment setup complete! ---")
    print("You can now use 'control.sh' to start the application.")

if __name__ == "__main__":
    main()

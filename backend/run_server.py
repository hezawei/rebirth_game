import os
import sys
import subprocess
from typing import List

# Ensure project root is on sys.path
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

from config.logging_config import LOGGER


def run_alembic(args: List[str]):
    cmd = [sys.executable, "-m", "alembic"] + list(args)
    LOGGER.info(f"Running Alembic: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


def apply_db_migrations():
    """Apply Alembic migrations; require PostgreSQL DATABASE_URL."""
    from sqlalchemy import create_engine, inspect
    from config.settings import settings

    database_url = getattr(settings, 'database_url', None)
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set (PostgreSQL)")
    if not database_url.lower().startswith("postgresql"):
        raise RuntimeError(f"Only PostgreSQL is supported. Got: {database_url}")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    has_alembic = inspector.has_table('alembic_version')
    has_users = inspector.has_table('users')
    has_sessions = inspector.has_table('game_sessions')
    has_nodes = inspector.has_table('story_nodes')

    if not has_alembic and (has_users or has_sessions or has_nodes):
        LOGGER.info("Found existing business tables without Alembic metadata; stamping baseline then upgrading...")
        base_rev = '37691daea28a'
        run_alembic(["stamp", base_rev])
        run_alembic(["upgrade", "head"])
    else:
        run_alembic(["upgrade", "head"])


def compute_workers() -> int:
    """Auto-select Gunicorn workers for PostgreSQL: CPU*2+1 (min 3)."""
    env_workers = os.getenv("GUNICORN_WORKERS")
    if env_workers and env_workers.isdigit():
        return int(env_workers)

    cpu = os.cpu_count() or 2
    return max(3, cpu * 2 + 1)


def main():
    try:
        apply_db_migrations()
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Alembic failed with code {e.returncode}: {e}")
        raise
    except Exception as e:
        LOGGER.error(f"Unexpected error applying migrations: {e}")
        raise

    workers = compute_workers()
    cmd = [
        "gunicorn",
        "-w", str(workers),
        "-k", "uvicorn.workers.UvicornWorker",
        "--bind", "0.0.0.0:8000",
        "backend.main:app",
    ]
    LOGGER.info(f"Starting Gunicorn with {workers} workers...")
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()

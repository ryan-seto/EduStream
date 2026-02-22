#!/usr/bin/env python3
"""
Development startup script.
Starts Docker services, runs migrations, and launches backend + frontend.

Usage: python dev.py
"""

import subprocess
import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def run(cmd, cwd=None, check=True):
    """Run a command and return the result."""
    print(f"\n> {cmd}")
    return subprocess.run(cmd, shell=True, cwd=cwd, check=check)


def check_docker():
    """Check if Docker is running."""
    result = subprocess.run(
        "docker info", shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Docker is not running. Please start Docker Desktop first.")
        sys.exit(1)


def start_services():
    """Start PostgreSQL and Redis via Docker Compose."""
    print("\n=== Starting Docker services ===")
    run("docker-compose up -d", cwd=ROOT)

    # Wait for PostgreSQL to be ready
    print("Waiting for PostgreSQL...")
    for i in range(30):
        result = subprocess.run(
            'docker-compose exec -T db pg_isready -U edustream',
            shell=True, cwd=ROOT, capture_output=True
        )
        if result.returncode == 0:
            print("PostgreSQL is ready!")
            break
        time.sleep(1)
    else:
        print("PostgreSQL did not start in time")
        sys.exit(1)


def setup_backend():
    """Install backend dependencies and run migrations."""
    print("\n=== Setting up backend ===")

    # Check if venv exists
    venv_path = BACKEND / "venv"
    if not venv_path.exists():
        print("Creating virtual environment...")
        run(f"python -m venv venv", cwd=BACKEND)

    # Determine pip path
    if sys.platform == "win32":
        pip = venv_path / "Scripts" / "pip"
        python = venv_path / "Scripts" / "python"
    else:
        pip = venv_path / "bin" / "pip"
        python = venv_path / "bin" / "python"

    # Install dependencies
    print("Installing dependencies...")
    run(f'"{pip}" install -r requirements.txt', cwd=BACKEND)

    # Copy .env if not exists
    env_file = BACKEND / ".env"
    env_example = ROOT / ".env.example"
    if not env_file.exists() and env_example.exists():
        print("Creating .env from .env.example...")
        import shutil
        shutil.copy(env_example, env_file)

    # Run migrations
    print("Running database migrations...")
    run(f'"{python}" -m alembic upgrade head', cwd=BACKEND, check=False)

    return python


def setup_frontend():
    """Install frontend dependencies."""
    print("\n=== Setting up frontend ===")

    node_modules = FRONTEND / "node_modules"
    if not node_modules.exists():
        print("Installing npm dependencies...")
        run("npm install", cwd=FRONTEND)


def main():
    print("=" * 50)
    print("EduStream AI - Development Server")
    print("=" * 50)

    # Check Docker
    check_docker()

    # Start services
    start_services()

    # Setup backend
    python = setup_backend()

    # Setup frontend
    setup_frontend()

    print("\n" + "=" * 50)
    print("Starting development servers...")
    print("=" * 50)
    print("\nBackend:  http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop all servers\n")

    # Start both servers
    try:
        if sys.platform == "win32":
            # On Windows, start backend in new window and frontend in current
            subprocess.Popen(
                f'start "Backend" cmd /k "cd /d {BACKEND} && {python} -m uvicorn app.main:app --reload"',
                shell=True
            )
            # Run frontend in current terminal
            run("npm run dev", cwd=FRONTEND)
        else:
            # On Unix, use & to background
            backend_proc = subprocess.Popen(
                f'cd "{BACKEND}" && "{python}" -m uvicorn app.main:app --reload',
                shell=True
            )
            frontend_proc = subprocess.Popen(
                f'cd "{FRONTEND}" && npm run dev',
                shell=True
            )
            backend_proc.wait()
            frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down...")


if __name__ == "__main__":
    main()

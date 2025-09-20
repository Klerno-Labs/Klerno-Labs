#!/usr/bin/env python3
"""
Klerno Labs Build Script
=======================

Cross-platform build script that works on Windows, macOS, and Linux.
This replaces the need for a Makefile.

Usage:
    python build.py <command>

Commands:
    install     Install dependencies
    lint        Run linting checks
    format      Format code with black and isort
    test        Run tests
    validate    Run full validation (same as CI)
    clean       Clean cache and temporary files
    dev         Install development dependencies
    server      Start development server
    security    Run security checks
    spell       Run spell checking
    help        Show this help message
"""

import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, description=None):
    """Run a command and handle errors."""
    if description:
        print(f"🔍 {description}")

    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)
    print("✅ Success\n")


def install():
    """Install production dependencies."""
    run_cmd("python -m pip install --upgrade pip", "Upgrading pip")
    run_cmd("pip install -r requirements.txt", "Installing production dependencies")


def dev():
    """Install development dependencies."""
    run_cmd("python -m pip install --upgrade pip", "Upgrading pip")
    run_cmd("pip install -r requirements.txt", "Installing production dependencies")
    run_cmd("pip install ruff black isort mypy pytest pytest-cov", "Installing development dependencies")


def lint():
    """Run linting checks."""
    run_cmd("ruff check app/", "Running ruff checks")


def format_code():
    """Format code with black and isort."""
    run_cmd("black app/", "Formatting with black")
    run_cmd("isort app/", "Sorting imports with isort")


def test():
    """Run tests."""
    run_cmd("python -m pytest app/tests/ -v", "Running tests")


def security():
    """Run security checks."""
    print("🔒 Security checks")
    print("Note: Install bandit for security scanning: pip install bandit")
    print("Run: bandit -r app/")


def spell():
    """Run spell checking."""
    try:
        run_cmd("codespell --skip=\"./.git,./node_modules,./dist,./build,./.venv,./__pycache__,./.pytest_cache,./.mypy_cache,./.ruff_cache,./data,./artifacts,./backups,./temp,./logs\" app/", "Checking spelling")
    except:
        print("Note: Install codespell for spell checking: pip install codespell")


def clean():
    """Clean cache and temporary files."""
    print("🧹 Cleaning cache and temporary files")

    patterns = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "*.pyc",
        "*.pyo",
        ".coverage",
        "htmlcov",
        "dist",
        "build",
        "*.egg-info"
    ]

    for pattern in patterns:
        for path in Path(".").rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                print(f"Removed directory: {path}")
            elif path.is_file():
                path.unlink()
                print(f"Removed file: {path}")


def server():
    """Start development server."""
    print("🚀 Starting development server...")
    run_cmd("python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000", "Starting uvicorn server")


def validate():
    """Run full validation (same as CI)."""
    print("🚀 Running full validation...")
    install()
    dev()
    lint()
    test()
    security()
    spell()
    print("✅ All validation checks passed!")


def help_cmd():
    """Show help message."""
    print(__doc__)


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        help_cmd()
        sys.exit(1)

    command = sys.argv[1]

    commands = {
        "install": install,
        "dev": dev,
        "lint": lint,
        "format": format_code,
        "test": test,
        "security": security,
        "spell": spell,
        "validate": validate,
        "clean": clean,
        "server": server,
        "help": help_cmd,
    }

    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(f"Available commands: {', '.join(commands.keys())}")
        sys.exit(1)

    commands[command]()


if __name__ == "__main__":
    main()

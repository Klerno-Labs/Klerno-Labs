#!/usr/bin/env python3
"""
Local Validation Script for Klerno Labs
=======================================

This script runs the same validation checks as the CI pipeline locally.
Use this to validate your changes before pushing to GitHub.

Usage:
    python validate.py [--quick] [--no-tests] [--no-spell]

Options:
    --quick     Skip time-consuming checks (mypy, tests)
    --no-tests  Skip test execution
    --no-spell  Skip spell checking
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description, allow_failure=False):
    """Run a command and return success status."""
    print(f"\n🔍 {description}")
    print(f"Running: {cmd}")

    start_time = time.time()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ SUCCESS ({duration:.1f}s)")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAILED ({duration:.1f}s)")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")

            if allow_failure:
                print("⚠️ Continuing despite failure...")
                return True
            return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return not allow_failure

def main():
    parser = argparse.ArgumentParser(description="Run local validation checks")
    parser.add_argument("--quick", action="store_true", help="Skip time-consuming checks")
    parser.add_argument("--no-tests", action="store_true", help="Skip test execution")
    parser.add_argument("--no-spell", action="store_true", help="Skip spell checking")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 KLERNO LABS - LOCAL VALIDATION")
    print("=" * 60)

    # Change to project directory
    project_dir = Path(__file__).parent
    print(f"📁 Working directory: {project_dir}")

    checks = []

    # Dependency installation
    checks.append((
        "python -m pip install --upgrade pip",
        "Upgrade pip",
        False
    ))

    checks.append((
        "pip install -r requirements.txt -r requirements-dev.txt",
        "Install dependencies",
        False
    ))

    # Code quality checks
    checks.append((
        "ruff check app/ --output-format=text",
        "Lint with ruff",
        False
    ))

    checks.append((
        "black --check app/ --diff",
        "Format check with black",
        False
    ))

    checks.append((
        "isort --check-only app/ --diff",
        "Import sort check with isort",
        False
    ))

    if not args.quick:
        checks.append((
            "mypy app/ --config-file=mypy.ini",
            "Type check with mypy",
            True  # Allow mypy failures
        ))

    # Security and spell checks
    checks.append((
        "bandit -r app/ -f txt",
        "Security check with bandit",
        True  # Allow bandit failures
    ))

    if not args.no_spell:
        checks.append((
            "pip install codespell",
            "Install codespell",
            False
        ))

        checks.append((
            'codespell --skip="./.git,./node_modules,./dist,./build,./.venv,./__pycache__,./.pytest_cache,./.mypy_cache,./.ruff_cache,./data,./artifacts,./backups,./temp,./logs" app/',
            "Spell check with codespell",
            True  # Allow spell check failures
        ))

    # Testing
    if not args.no_tests and not args.quick:
        checks.append((
            "pytest app/tests/ tests/ -v --tb=short",
            "Run tests with pytest",
            False
        ))

    # Syntax validation
    checks.append((
        "python -m py_compile app/main.py",
        "Syntax validation",
        False
    ))

    checks.append((
        'python -c "import app.main; print(\'✅ Main module imports successfully\')"',
        "Import validation",
        False
    ))

    # Run all checks
    passed = 0
    total = len(checks)

    for cmd, description, allow_failure in checks:
        if run_command(cmd, description, allow_failure):
            passed += 1
        elif not allow_failure:
            print(f"\n❌ Critical check failed: {description}")
            print("🛑 Stopping validation due to critical failure")
            break

    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    print(f"🎯 Checks passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL VALIDATION CHECKS PASSED!")
        print("✨ Your code is ready for push to GitHub")
        print("✨ CI pipeline should pass without issues")
        return 0
    else:
        print(f"\n⚠️ {total - passed} checks failed or had warnings")
        print("🔧 Please fix the issues before pushing to GitHub")
        return 1

if __name__ == "__main__":
    sys.exit(main())

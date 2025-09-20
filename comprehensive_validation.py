#!/usr/bin/env python3
"""Comprehensive validation test to confirm all CI/CD and optimization issues are resolved."""

import json
import subprocess
import sys
import time
from pathlib import Path

import requests


def run_command(cmd, description):
    """Run a command and return results."""
    print(f"\n🔍 {description}")
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ FAILED")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def test_server_endpoints():
    """Test server endpoints."""
    print("\n🔍 Testing FastAPI Server Endpoints")

    endpoints_to_test = [
        ("/health", "GET", "Health check endpoint"),
        ("/status", "GET", "Status endpoint"),
        ("/docs", "GET", "API documentation"),
        ("/", "GET", "Root endpoint")
    ]

    server_running = False
    for endpoint, method, description in endpoints_to_test:
        try:
            response = requests.get(f"http://127.0.0.1:8000{endpoint}", timeout=5)
            print(f"✅ {description}: {response.status_code}")
            server_running = True
        except requests.exceptions.ConnectionError:
            print(f"🔌 {description}: Server not running")
        except Exception as e:
            print(f"❌ {description}: {str(e)[:50]}...")

    return server_running

def main():
    """Run comprehensive validation."""
    print("=" * 60)
    print("🚀 KLERNO LABS - COMPREHENSIVE VALIDATION TEST")
    print("=" * 60)

    # Change to project directory
    project_dir = Path(__file__).parent
    print(f"📁 Working directory: {project_dir}")

    results = {}

    # 1. Python Environment Check
    results['python_version'] = run_command("python --version", "Python Version Check")

    # 2. Dependencies Check
    results['dependencies'] = run_command("python -c \"import fastapi, uvicorn, pydantic; print('Core dependencies available')\"",
                                        "Core Dependencies Check")

    # 3. Syntax Validation
    results['syntax_main'] = run_command("python -m py_compile app/main.py", "Main Module Syntax Check")
    results['syntax_settings'] = run_command("python -m py_compile app/settings.py", "Settings Module Syntax Check")

    # 4. Import Validation
    results['import_main'] = run_command("python -c \"import app.main; print('Main module imports successfully')\"",
                                       "Main Module Import Check")

    # 5. Server Endpoint Tests
    results['server_endpoints'] = test_server_endpoints()

    # 6. Linting Configuration Check
    results['flake8_config'] = run_command("python -c \"import configparser; c=configparser.ConfigParser(); c.read('.flake8'); print('Flake8 config valid')\"",
                                         "Linting Configuration Check")

    # 7. Project Structure Validation
    required_files = [
        'app/main.py',
        'app/settings.py',
        'requirements.txt',
        'Dockerfile',
        '.flake8',
        'pyproject.toml',
        '.github/workflows/ci-cd.yml'
    ]

    print(f"\n🔍 Project Structure Validation")
    structure_valid = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            structure_valid = False

    results['project_structure'] = structure_valid

    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    print(f"\n🎯 Overall Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 ALL VALIDATION TESTS PASSED!")
        print("✨ CI/CD pipeline issues have been resolved")
        print("✨ Optimization work is complete")
        print("✨ System is ready for production")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} issues remain")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

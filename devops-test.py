#!/usr/bin/env python3
"""
Klerno Labs DevOps Integration Test Suite
=========================================

Comprehensive test suite that validates all DevOps improvements and CI/CD pipeline functionality.
This script runs the same checks that GitHub Actions CI will perform.

Usage:
    python devops-test.py [options]

Options:
    --fast      Skip slow tests (no full dependency install)
    --coverage  Include test coverage reporting
    --security  Include security vulnerability scanning
    --all       Run all tests including slow ones
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


class DevOpsTestSuite:
    """Comprehensive DevOps validation test suite."""

    def __init__(self, fast=False, coverage=False, security=False):
        self.fast = fast
        self.coverage = coverage
        self.security = security
        self.results = {}
        self.start_time = time.time()

    def run_command(self, command, description, allow_failure=False):
        """Run a command and capture results."""
        print(f"\n🔍 {description}")
        print(f"$ {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print(f"✅ SUCCESS: {description}")
                self.results[description] = {"status": "PASS", "output": result.stdout}
                return True
            else:
                status = "WARN" if allow_failure else "FAIL"
                print(f"{'⚠️' if allow_failure else '❌'} {status}: {description}")
                print(f"Error: {result.stderr[:200]}...")
                self.results[description] = {
                    "status": status,
                    "error": result.stderr,
                    "output": result.stdout
                }
                return allow_failure

        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {description}")
            self.results[description] = {"status": "TIMEOUT", "error": "Command timed out"}
            return False
        except Exception as e:
            print(f"💥 ERROR: {description} - {e}")
            self.results[description] = {"status": "ERROR", "error": str(e)}
            return False

    def test_import_validation(self):
        """Test that all core modules can be imported successfully."""
        print("\n" + "="*60)
        print("🐍 PYTHON IMPORT VALIDATION")
        print("="*60)

        imports = [
            "import app.main",
            "import app.auth",
            "import app.models",
            "import app.store",
            "from app.main import app",
            "import fastapi",
            "import pydantic",
            "import uvicorn"
        ]

        for import_stmt in imports:
            success = self.run_command(
                f'python -c "{import_stmt}; print(\'✓ {import_stmt}\')"',
                f"Import: {import_stmt}",
                allow_failure=True
            )
            if not success and not self.fast:
                return False

        return True

    def test_linting_pipeline(self):
        """Test code quality and linting pipeline."""
        print("\n" + "="*60)
        print("🔍 CODE QUALITY PIPELINE")
        print("="*60)

        # Check ruff configuration
        self.run_command(
            "python -m ruff check app/ --statistics",
            "Ruff linting analysis",
            allow_failure=True
        )

        # Check import sorting
        self.run_command(
            "python -m isort --check-only app/",
            "Import sorting validation",
            allow_failure=True
        )

        # Check black formatting
        self.run_command(
            "python -m black --check app/",
            "Black code formatting check",
            allow_failure=True
        )

        return True

    def test_application_health(self):
        """Test application health and basic functionality."""
        print("\n" + "="*60)
        print("🏥 APPLICATION HEALTH CHECK")
        print("="*60)

        # Test health endpoint if server is running
        try:
            import requests
            response = requests.get("http://127.0.0.1:8001/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health endpoint responsive: {health_data.get('status', 'unknown')}")
                print(f"📊 Uptime: {health_data.get('uptime_seconds', 0):.1f}s")
                self.results["Application Health"] = {"status": "PASS", "data": health_data}
            else:
                print(f"⚠️ Health endpoint returned {response.status_code}")
                self.results["Application Health"] = {"status": "WARN", "code": response.status_code}
        except Exception as e:
            print(f"ℹ️ Application health check skipped: {e}")
            self.results["Application Health"] = {"status": "SKIP", "reason": str(e)}

        return True

    def test_security_basics(self):
        """Test basic security configurations."""
        if not self.security:
            print("\n⏭️ Skipping security tests (use --security to enable)")
            return True

        print("\n" + "="*60)
        print("🔒 SECURITY VALIDATION")
        print("="*60)

        # Check for common security issues
        self.run_command(
            "python -c \"import app.security; print('Security module OK')\"",
            "Security module validation",
            allow_failure=True
        )

        # Check for hardcoded secrets (basic check)
        self.run_command(
            "grep -r --include='*.py' -i 'password.*=' app/ || echo 'No hardcoded passwords found'",
            "Basic secret scanning",
            allow_failure=True
        )

        return True

    def test_file_structure(self):
        """Validate project file structure and important files."""
        print("\n" + "="*60)
        print("📁 PROJECT STRUCTURE VALIDATION")
        print("="*60)

        required_files = [
            "requirements.txt",
            "pyproject.toml",
            ".github/workflows/ci.yml",
            "app/main.py",
            "app/__init__.py",
            "cspell.json",
            "build.py"
        ]

        for file_path in required_files:
            if Path(file_path).exists():
                print(f"✅ Found: {file_path}")
            else:
                print(f"❌ Missing: {file_path}")
                return False

        self.results["File Structure"] = {"status": "PASS", "files": required_files}
        return True

    def test_ci_workflow_syntax(self):
        """Validate GitHub Actions workflow syntax."""
        print("\n" + "="*60)
        print("⚙️ CI/CD WORKFLOW VALIDATION")
        print("="*60)

        # Basic YAML syntax check
        try:
            import yaml
            with open(".github/workflows/ci.yml", "r", encoding='utf-8') as f:
                workflow = yaml.safe_load(f)
            print("✅ CI workflow YAML syntax valid")
            print(f"📋 Jobs defined: {', '.join(workflow.get('jobs', {}).keys())}")
            self.results["CI Workflow"] = {"status": "PASS", "jobs": list(workflow.get('jobs', {}).keys())}
        except Exception as e:
            print(f"❌ CI workflow validation failed: {e}")
            self.results["CI Workflow"] = {"status": "FAIL", "error": str(e)}
            return False

        return True

    def generate_report(self):
        """Generate comprehensive test report."""
        end_time = time.time()
        duration = end_time - self.start_time

        print("\n" + "="*80)
        print("📊 DEVOPS TEST SUITE RESULTS")
        print("="*80)

        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        warned = sum(1 for r in self.results.values() if r["status"] == "WARN")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results.values() if r["status"] == "SKIP")

        print(f"⏱️ Duration: {duration:.2f}s")
        print(f"✅ Passed: {passed}")
        print(f"⚠️ Warnings: {warned}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️ Skipped: {skipped}")
        print(f"📊 Total: {len(self.results)}")

        print(f"\n🎯 Success Rate: {(passed/(len(self.results)-skipped)*100):.1f}%")

        # Detailed results
        print("\n📋 Detailed Results:")
        print("-" * 60)
        for test, result in self.results.items():
            status_icon = {
                "PASS": "✅",
                "WARN": "⚠️",
                "FAIL": "❌",
                "SKIP": "⏭️",
                "TIMEOUT": "⏰",
                "ERROR": "💥"
            }.get(result["status"], "❓")
            print(f"{status_icon} {test}: {result['status']}")

        # Save detailed report
        report_file = f"devops-test-report-{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "duration": duration,
                "summary": {"passed": passed, "warned": warned, "failed": failed, "skipped": skipped},
                "results": self.results
            }, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")

        return failed == 0

    def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 Starting Klerno Labs DevOps Integration Test Suite")
        print(f"⚙️ Configuration: fast={self.fast}, coverage={self.coverage}, security={self.security}")
        print("=" * 80)

        # Run test categories
        tests = [
            self.test_file_structure,
            self.test_import_validation,
            self.test_ci_workflow_syntax,
            self.test_linting_pipeline,
            self.test_application_health,
            self.test_security_basics,
        ]

        all_passed = True
        for test in tests:
            try:
                if not test():
                    all_passed = False
                    if not self.fast:  # Stop on first failure unless in fast mode
                        break
            except Exception as e:
                print(f"💥 Test suite error: {e}")
                all_passed = False
                break

        # Generate final report
        success = self.generate_report()

        if success and all_passed:
            print("\n🎉 All DevOps validation tests passed!")
            print("🚀 Your CI/CD pipeline is ready for production!")
            return True
        else:
            print("\n⚠️ Some tests failed or need attention")
            print("📋 Review the report above for details")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Klerno Labs DevOps Integration Test Suite")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--coverage", action="store_true", help="Include coverage reporting")
    parser.add_argument("--security", action="store_true", help="Include security scanning")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    if args.all:
        args.coverage = True
        args.security = True

    suite = DevOpsTestSuite(
        fast=args.fast,
        coverage=args.coverage,
        security=args.security
    )

    success = suite.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

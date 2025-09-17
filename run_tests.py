#!/usr/bin/env python3
"""
Automated Test Runner for Klerno Labs Enterprise Optimization System

This script provides automated testing capabilities with different test suites
and comprehensive reporting for the enterprise optimization system.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRunner:
    """Automated test runner for enterprise optimization system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def setup_test_environment(self):
        """Setup test environment and dependencies."""
        print("🔧 Setting up test environment...")
        
        # Set environment variables
        os.environ["TESTING"] = "true"
        os.environ["LOG_LEVEL"] = "ERROR"
        os.environ["ENVIRONMENT"] = "test"
        
        # Create test data directory if it doesn't exist
        test_data_dir = self.project_root / "test_data"
        test_data_dir.mkdir(exist_ok=True)
        
        # Create test database
        test_db_path = test_data_dir / "test_klerno.db"
        if test_db_path.exists():
            test_db_path.unlink()
        
        print("✅ Test environment setup complete")
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests for all optimization components."""
        print("\n🧪 Running Unit Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-m", "not integration",
            "--durations=10",
            "--junitxml=test-results-unit.xml"
        ]
        
        result = self._run_command(cmd, "Unit Tests")
        return result
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("\n🔗 Running Integration Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/",
            "-v",
            "--tb=short",
            "-m", "integration",
            "--durations=10",
            "--junitxml=test-results-integration.xml"
        ]
        
        result = self._run_command(cmd, "Integration Tests")
        return result
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance and benchmark tests."""
        print("\n⚡ Running Performance Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-k", "performance",
            "--durations=10",
            "--junitxml=test-results-performance.xml"
        ]
        
        result = self._run_command(cmd, "Performance Tests")
        return result
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security-specific tests."""
        print("\n🔒 Running Security Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-k", "security",
            "--durations=10",
            "--junitxml=test-results-security.xml"
        ]
        
        result = self._run_command(cmd, "Security Tests")
        return result
    
    def run_all_tests_with_coverage(self) -> Dict[str, Any]:
        """Run all tests with coverage reporting."""
        print("\n📊 Running All Tests with Coverage...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--durations=10",
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-branch",
            "--junitxml=test-results-complete.xml"
        ]
        
        result = self._run_command(cmd, "Complete Test Suite")
        return result
    
    def run_quick_smoke_tests(self) -> Dict[str, Any]:
        """Run quick smoke tests for basic functionality."""
        print("\n💨 Running Quick Smoke Tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "app/tests/test_guardian.py",
            "app/tests/test_compliance.py",
            "-v",
            "--tb=short", 
            "--durations=5",
            "--junitxml=test-results-smoke.xml"
        ]
        
        result = self._run_command(cmd, "Smoke Tests")
        return result
    
    def _run_command(self, cmd: List[str], test_name: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            test_result = {
                "name": test_name,
                "success": result.returncode == 0,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
            if result.returncode == 0:
                print(f"✅ {test_name} completed successfully in {duration:.2f}s")
            else:
                print(f"❌ {test_name} failed in {duration:.2f}s")
                print(f"Error: {result.stderr}")
            
            self.test_results[test_name] = test_result
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {test_name} timed out after {duration:.2f}s")
            
            test_result = {
                "name": test_name,
                "success": False,
                "duration": duration,
                "error": "Test execution timed out",
                "return_code": -1
            }
            
            self.test_results[test_name] = test_result
            return test_result
        
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {test_name} failed with exception: {e}")
            
            test_result = {
                "name": test_name,
                "success": False,
                "duration": duration,
                "error": str(e),
                "return_code": -1
            }
            
            self.test_results[test_name] = test_result
            return test_result
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - successful_tests
        total_duration = sum(result["duration"] for result in self.test_results.values())
        
        report = {
            "summary": {
                "total_test_suites": total_tests,
                "successful_suites": successful_tests,
                "failed_suites": failed_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_duration": total_duration,
                "start_time": self.start_time,
                "end_time": self.end_time
            },
            "test_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check overall success rate
        successful_count = sum(1 for result in self.test_results.values() if result["success"])
        total_count = len(self.test_results)
        
        if total_count > 0:
            success_rate = successful_count / total_count
            
            if success_rate < 0.8:
                recommendations.append("⚠️  Test success rate is below 80%. Review failing tests and fix issues.")
            
            if success_rate == 1.0:
                recommendations.append("🎉 All tests passed! System is ready for deployment.")
        
        # Check for performance issues
        slow_tests = [name for name, result in self.test_results.items() 
                     if result.get("duration", 0) > 30]
        
        if slow_tests:
            recommendations.append(f"🐌 Slow test suites detected: {', '.join(slow_tests)}. Consider optimization.")
        
        # Check for security test failures
        security_failures = [name for name, result in self.test_results.items() 
                           if "Security" in name and not result["success"]]
        
        if security_failures:
            recommendations.append("🔒 Security tests failed. Review security configurations before deployment.")
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], filename: str = "test_report.json"):
        """Save test report to file."""
        report_path = self.project_root / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Test report saved to: {report_path}")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test summary."""
        summary = report["summary"]
        
        print("\n" + "="*60)
        print("🎯 TEST EXECUTION SUMMARY")
        print("="*60)
        
        print(f"Total Test Suites: {summary['total_test_suites']}")
        print(f"Successful Suites: {summary['successful_suites']}")
        print(f"Failed Suites: {summary['failed_suites']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Total Duration: {summary['total_duration']:.2f} seconds")
        
        print("\n📊 DETAILED RESULTS:")
        for name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"  {status} - {name} ({result['duration']:.2f}s)")
        
        if report["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report["recommendations"]:
                print(f"  {rec}")
        
        print("\n" + "="*60)


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Klerno Labs Enterprise Test Runner")
    parser.add_argument("--suite", choices=["unit", "integration", "performance", "security", "smoke", "all"], 
                       default="smoke", help="Test suite to run")
    parser.add_argument("--coverage", action="store_true", help="Include coverage reporting")
    parser.add_argument("--report", default="test_report.json", help="Test report filename")
    parser.add_argument("--no-setup", action="store_true", help="Skip test environment setup")
    
    args = parser.parse_args()
    
    print("🚀 Klerno Labs Enterprise Test Runner")
    print("="*50)
    
    # Initialize test runner
    runner = TestRunner(PROJECT_ROOT)
    runner.start_time = time.time()
    
    # Setup test environment
    if not args.no_setup:
        runner.setup_test_environment()
    
    # Run selected test suite
    try:
        if args.suite == "unit":
            runner.run_unit_tests()
        elif args.suite == "integration":
            runner.run_integration_tests()
        elif args.suite == "performance":
            runner.run_performance_tests()
        elif args.suite == "security":
            runner.run_security_tests()
        elif args.suite == "smoke":
            runner.run_quick_smoke_tests()
        elif args.suite == "all":
            if args.coverage:
                runner.run_all_tests_with_coverage()
            else:
                runner.run_unit_tests()
                runner.run_integration_tests()
                runner.run_performance_tests()
                runner.run_security_tests()
    
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
    
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
    
    finally:
        runner.end_time = time.time()
        
        # Generate and display report
        report = runner.generate_test_report()
        runner.print_summary(report)
        runner.save_report(report, args.report)


if __name__ == "__main__":
    main()
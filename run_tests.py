#!/usr/bin/env python3
"""
Automated Test Runner with Advanced Features
Comprehensive test execution with reporting and analysis
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class TestRunner:
    """Advanced test runner with reporting and analysis."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests with coverage."""
        print("🧪 Running unit tests...")
        
        cmd = [
            "pytest",
            "app/tests/test_unit_comprehensive.py",
            "-v",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=json:coverage-unit.json",
            "--junit-xml=unit-test-results.xml",
            "-m", "unit"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        cmd = [
            "pytest",
            "app/tests/test_integration_comprehensive.py",
            "-v",
            "--junit-xml=integration-test-results.xml",
            "-m", "integration"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        cmd = [
            "pytest",
            "app/tests/test_performance_comprehensive.py",
            "-v",
            "--junit-xml=performance-test-results.xml",
            "-m", "performance"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests with comprehensive reporting."""
        print("🚀 Running comprehensive test suite...")
        
        self.start_time = datetime.now()
        
        # Run different test categories
        self.results["unit"] = self.run_unit_tests()
        self.results["integration"] = self.run_integration_tests()
        self.results["performance"] = self.run_performance_tests()
        
        self.end_time = datetime.now()
        
        # Generate summary report
        self.generate_summary_report()
        
        return self.results
    
    def generate_summary_report(self):
        """Generate comprehensive test summary report."""
        print("📊 Generating test summary report...")
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        report = {
            "test_run": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": total_duration,
                "timestamp": datetime.now().isoformat()
            },
            "summary": {
                "total_categories": len(self.results),
                "successful_categories": sum(1 for r in self.results.values() if r["success"]),
                "failed_categories": sum(1 for r in self.results.values() if not r["success"]),
                "overall_success": all(r["success"] for r in self.results.values())
            },
            "categories": self.results,
            "coverage_info": self.extract_coverage_info()
        }
        
        # Save detailed report
        with open("test-summary-report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report
        self.generate_html_report(report)
        
        # Print summary to console
        self.print_summary(report)
    
    def extract_coverage_info(self) -> Dict[str, Any]:
        """Extract coverage information from coverage reports."""
        coverage_info = {}
        
        try:
            if os.path.exists("coverage-unit.json"):
                with open("coverage-unit.json", "r") as f:
                    coverage_data = json.load(f)
                    coverage_info["unit_tests"] = {
                        "coverage_percent": coverage_data.get("totals", {}).get("percent_covered", 0),
                        "lines_covered": coverage_data.get("totals", {}).get("covered_lines", 0),
                        "lines_missing": coverage_data.get("totals", {}).get("missing_lines", 0)
                    }
        except Exception as e:
            coverage_info["error"] = str(e)
        
        return coverage_info
    
    def generate_html_report(self, report: Dict[str, Any]):
        """Generate HTML test report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Klerno Labs Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }}
        .summary {{ background: #ecf0f1; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .success {{ color: #27ae60; }}
        .failure {{ color: #e74c3c; }}
        .category {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }}
        .details {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Klerno Labs Test Report</h1>
        <p>Generated: {report['test_run']['timestamp']}</p>
        <p>Duration: {report['test_run']['duration_seconds']:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <h2>📊 Test Summary</h2>
        <p><strong>Overall Status:</strong> 
            <span class="{'success' if report['summary']['overall_success'] else 'failure'}">
                {'✅ PASSED' if report['summary']['overall_success'] else '❌ FAILED'}
            </span>
        </p>
        <p><strong>Categories:</strong> {report['summary']['successful_categories']}/{report['summary']['total_categories']} passed</p>
        
        {f"<p><strong>Coverage:</strong> {report['coverage_info'].get('unit_tests', {}).get('coverage_percent', 'N/A')}%</p>" if 'unit_tests' in report.get('coverage_info', {}) else ''}
    </div>
    
    <div class="categories">
        <h2>📋 Test Categories</h2>
"""
        
        for category, result in report["categories"].items():
            status_class = "success" if result["success"] else "failure"
            status_icon = "✅" if result["success"] else "❌"
            
            html_content += f"""
        <div class="category">
            <h3 class="{status_class}">{status_icon} {category.title()} Tests</h3>
            <p><strong>Status:</strong> <span class="{status_class}">{'PASSED' if result['success'] else 'FAILED'}</span></p>
            <p><strong>Exit Code:</strong> {result['exit_code']}</p>
            
            <details>
                <summary>View Output</summary>
                <div class="details">
                    <h4>Standard Output:</h4>
                    <pre>{result['stdout']}</pre>
                    
                    <h4>Standard Error:</h4>
                    <pre>{result['stderr']}</pre>
                </div>
            </details>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open("test-report.html", "w") as f:
            f.write(html_content)
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test summary to console."""
        print("\n" + "=" * 60)
        print("🧪 TEST EXECUTION COMPLETE")
        print("=" * 60)
        
        overall_status = "✅ PASSED" if report['summary']['overall_success'] else "❌ FAILED"
        print(f"Overall Status: {overall_status}")
        print(f"Duration: {report['test_run']['duration_seconds']:.2f} seconds")
        print(f"Categories: {report['summary']['successful_categories']}/{report['summary']['total_categories']} passed")
        
        if 'unit_tests' in report.get('coverage_info', {}):
            coverage = report['coverage_info']['unit_tests']['coverage_percent']
            print(f"Code Coverage: {coverage}%")
        
        print("\n📋 Category Results:")
        for category, result in report["categories"].items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"  {category.title()}: {status}")
        
        print("\n📄 Reports Generated:")
        print("  • test-summary-report.json")
        print("  • test-report.html")
        if os.path.exists("htmlcov/index.html"):
            print("  • htmlcov/index.html (coverage report)")
        
        print("\n" + "=" * 60)


def main():
    """Main test execution function."""
    print("🚀 Starting Klerno Labs Test Suite")
    print("=" * 60)
    
    runner = TestRunner()
    results = runner.run_all_tests()
    
    # Return appropriate exit code
    overall_success = all(r["success"] for r in results.values())
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()

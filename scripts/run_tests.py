#!/usr/bin/env python
"""
Run all tests for the Klerno Labs application.
"""
import os
import sys
import subprocess
import argparse


def run_tests(coverage=False, verbose=False, test_path=None):
    """Run the pytest test suite with optional coverage."""
    os.environ["APP_ENV"] = "test"
    
    pytest_args = []
    
    # Add coverage if requested
    if coverage:
        pytest_args.extend(["--cov=app", "--cov-report=term", "--cov-report=html:coverage_report"])
    
    # Add verbosity if requested
    if verbose:
        pytest_args.append("-v")
    
    # Add test path if specified
    if test_path:
        pytest_args.append(test_path)
    else:
        pytest_args.append("tests/")
    
    # Print command for transparency
    cmd = [sys.executable, "-m", "pytest"] + pytest_args
    print(f"Running: {' '.join(cmd)}")
    
    # Run pytest
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Klerno Labs tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--path", help="Specific test path to run")
    
    args = parser.parse_args()
    
    exit_code = run_tests(
        coverage=args.coverage,
        verbose=args.verbose,
        test_path=args.path
    )
    
    sys.exit(exit_code)
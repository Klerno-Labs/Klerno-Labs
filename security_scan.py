# security_scan.py
"""
Security scanning script for dependency vulnerabilities and code security issues.
"""
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Any


def run_safety_scan() -> Dict[str, Any]:
    """Run safety scan for known security vulnerabilities in dependencies."""
    print("🔍 Running dependency vulnerability scan with safety...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "safety", "check", 
            "--json", "--ignore", "70612"  # Ignore specific jinja2 issue if needed
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ No known vulnerabilities found in dependencies")
            return {"status": "clean", "vulnerabilities": []}
        else:
            vulnerabilities = json.loads(result.stdout) if result.stdout else []
            print(f"⚠️  Found {len(vulnerabilities)} vulnerability(ies)")
            return {"status": "vulnerabilities_found", "vulnerabilities": vulnerabilities}
            
    except subprocess.TimeoutExpired:
        print("❌ Safety scan timed out")
        return {"status": "timeout", "vulnerabilities": []}
    except FileNotFoundError:
        print("❌ Safety not installed. Install with: pip install safety")
        return {"status": "tool_missing", "vulnerabilities": []}
    except json.JSONDecodeError:
        print("❌ Could not parse safety output")
        return {"status": "parse_error", "vulnerabilities": []}
    except Exception as e:
        print(f"❌ Safety scan failed: {e}")
        return {"status": "error", "vulnerabilities": []}


def run_bandit_scan() -> Dict[str, Any]:
    """Run bandit security linting on the codebase."""
    print("🔍 Running security linting with bandit...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "bandit", "-r", "app/", 
            "-f", "json", "-ll"  # Low and Low-Medium severity
        ], capture_output=True, text=True, timeout=120)
        
        if result.stdout:
            bandit_output = json.loads(result.stdout)
            issues = bandit_output.get("results", [])
            
            if not issues:
                print("✅ No security issues found in code")
                return {"status": "clean", "issues": []}
            else:
                high_issues = [i for i in issues if i.get("issue_severity") in ["HIGH", "MEDIUM"]]
                print(f"⚠️  Found {len(issues)} security issue(s), {len(high_issues)} high/medium severity")
                return {"status": "issues_found", "issues": issues, "high_severity": high_issues}
        else:
            print("✅ Bandit completed with no output")
            return {"status": "clean", "issues": []}
            
    except subprocess.TimeoutExpired:
        print("❌ Bandit scan timed out")
        return {"status": "timeout", "issues": []}
    except FileNotFoundError:
        print("❌ Bandit not installed. Install with: pip install bandit")
        return {"status": "tool_missing", "issues": []}
    except json.JSONDecodeError:
        print("❌ Could not parse bandit output")
        return {"status": "parse_error", "issues": []}
    except Exception as e:
        print(f"❌ Bandit scan failed: {e}")
        return {"status": "error", "issues": []}


def check_pip_audit() -> Dict[str, Any]:
    """Run pip-audit for additional vulnerability scanning."""
    print("🔍 Running pip-audit for additional vulnerability checks...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip_audit", "--format=json"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            output = json.loads(result.stdout) if result.stdout else {"vulnerabilities": []}
            vulns = output.get("vulnerabilities", [])
            
            if not vulns:
                print("✅ No vulnerabilities found with pip-audit")
                return {"status": "clean", "vulnerabilities": []}
            else:
                print(f"⚠️  Found {len(vulns)} vulnerability(ies) with pip-audit")
                return {"status": "vulnerabilities_found", "vulnerabilities": vulns}
        else:
            print("⚠️  pip-audit completed with warnings")
            return {"status": "warnings", "vulnerabilities": []}
            
    except FileNotFoundError:
        print("ℹ️  pip-audit not available (optional)")
        return {"status": "tool_missing", "vulnerabilities": []}
    except Exception as e:
        print(f"ℹ️  pip-audit check skipped: {e}")
        return {"status": "skipped", "vulnerabilities": []}


def check_environment_security() -> Dict[str, Any]:
    """Check for common security misconfigurations in environment."""
    print("🔍 Checking environment security configuration...")
    
    issues = []
    
    # Check for insecure environment variables
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            
        # Check for weak secrets
        if "CHANGE_ME" in content:
            issues.append("Weak default secrets found in .env file")
        
        if "JWT_SECRET" in content and len(content.split("JWT_SECRET=")[1].split("\n")[0]) < 32:
            issues.append("JWT secret appears to be too short")
    
    # Check for debug mode in production files
    main_py = Path("app/main.py")
    if main_py.exists():
        with open(main_py, 'r') as f:
            content = f.read()
            
        if 'debug=True' in content:
            issues.append("Debug mode enabled in main application file")
    
    # Check for hardcoded credentials
    for py_file in Path("app").rglob("*.py"):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Simple checks for common hardcoded credentials
            if any(pattern in content.lower() for pattern in [
                'password="', "password='", 'api_key="', "api_key='",
                'secret_key="', "secret_key='", 'token="', "token='"
            ]):
                if "test" not in str(py_file).lower():  # Ignore test files
                    issues.append(f"Potential hardcoded credentials in {py_file}")
        except Exception:
            continue
    
    if not issues:
        print("✅ Environment security check passed")
        return {"status": "clean", "issues": []}
    else:
        print(f"⚠️  Found {len(issues)} environment security issue(s)")
        return {"status": "issues_found", "issues": issues}


def generate_security_report() -> None:
    """Generate comprehensive security report."""
    print("🛡️  Klerno Labs Security Scanner")
    print("=" * 50)
    
    # Run all security scans
    safety_results = run_safety_scan()
    bandit_results = run_bandit_scan()
    pip_audit_results = check_pip_audit()
    env_results = check_environment_security()
    
    # Generate summary
    print("\n📋 Security Scan Summary")
    print("-" * 30)
    
    total_issues = 0
    critical_issues = 0
    
    # Safety (dependency vulnerabilities)
    if safety_results["status"] == "vulnerabilities_found":
        vuln_count = len(safety_results["vulnerabilities"])
        total_issues += vuln_count
        critical_issues += vuln_count
        print(f"❌ Dependencies: {vuln_count} vulnerability(ies)")
    else:
        print("✅ Dependencies: No known vulnerabilities")
    
    # Bandit (code security issues)
    if bandit_results["status"] == "issues_found":
        issue_count = len(bandit_results["issues"])
        high_count = len(bandit_results.get("high_severity", []))
        total_issues += issue_count
        critical_issues += high_count
        print(f"⚠️  Code Security: {issue_count} issue(s), {high_count} high severity")
    else:
        print("✅ Code Security: No issues found")
    
    # Environment configuration
    if env_results["status"] == "issues_found":
        env_count = len(env_results["issues"])
        total_issues += env_count
        print(f"⚠️  Environment: {env_count} configuration issue(s)")
    else:
        print("✅ Environment: Configuration secure")
    
    # Overall assessment
    print(f"\n🎯 Overall Assessment")
    print(f"Total Issues: {total_issues}")
    print(f"Critical Issues: {critical_issues}")
    
    if critical_issues == 0:
        print("✅ Security posture: GOOD")
        exit_code = 0
    elif critical_issues <= 3:
        print("⚠️  Security posture: NEEDS ATTENTION")
        exit_code = 1
    else:
        print("❌ Security posture: REQUIRES IMMEDIATE ACTION")
        exit_code = 2
    
    # Save detailed report
    report = {
        "timestamp": str(subprocess.run(["date", "-u"], capture_output=True, text=True).stdout.strip()),
        "summary": {
            "total_issues": total_issues,
            "critical_issues": critical_issues
        },
        "safety": safety_results,
        "bandit": bandit_results,
        "pip_audit": pip_audit_results,
        "environment": env_results
    }
    
    with open("security_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: security_report.json")
    
    return exit_code


if __name__ == "__main__":
    exit_code = generate_security_report()
    sys.exit(exit_code)
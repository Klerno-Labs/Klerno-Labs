#!/usr/bin/env python3
"""Comprehensive security validation and hardening implementation."""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class SecurityValidator:
    """Advanced security validation and hardening system."""

    def __init__(self):
        self.security_report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vulnerabilities_found": [],
            "security_enhancements": [],
            "compliance_status": {},
            "hardening_applied": [],
        }

    def run_comprehensive_security_scan(self) -> Dict[str, Any]:
        """Run comprehensive security analysis."""

        print("🔒 COMPREHENSIVE SECURITY VALIDATION")
        print("=" * 50)

        # Run Bandit security scan
        print("🔍 Running Bandit security scanner...")
        bandit_results = self._run_bandit_scan()

        # Analyze dependencies for known vulnerabilities
        print("📦 Checking dependencies for vulnerabilities...")
        dependency_results = self._analyze_dependencies()

        # Check for sensitive data exposure
        print("🔍 Scanning for sensitive data exposure...")
        sensitive_data_results = self._scan_sensitive_data()

        # Validate authentication and authorization
        print("🔐 Validating authentication mechanisms...")
        auth_results = self._validate_authentication()

        # Check for secure configurations
        print("⚙️ Checking security configurations...")
        config_results = self._check_security_configs()

        # Compile comprehensive security report
        security_report = {
            "scan_timestamp": self.security_report["timestamp"],
            "bandit_analysis": bandit_results,
            "dependency_vulnerabilities": dependency_results,
            "sensitive_data_exposure": sensitive_data_results,
            "authentication_security": auth_results,
            "configuration_security": config_results,
            "overall_security_score": self._calculate_security_score(
                bandit_results, dependency_results, config_results
            ),
            "critical_issues": self._identify_critical_issues(bandit_results),
            "remediation_plan": self._generate_remediation_plan(),
        }

        return security_report

    def _run_bandit_scan(self) -> Dict[str, Any]:
        """Run Bandit security scanner and parse results."""

        try:
            # Run bandit scan with JSON output
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "bandit",
                    "-r",
                    ".",
                    "-f",
                    "json",
                    "-x",
                    ".venv*,node_modules,__pycache__,*.pyc",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if (
                result.returncode == 0 or result.returncode == 1
            ):  # 1 = vulnerabilities found
                try:
                    bandit_data = json.loads(result.stdout)

                    # Categorize vulnerabilities by severity
                    vulnerabilities_by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}

                    for result_item in bandit_data.get("results", []):
                        severity = result_item.get("issue_severity", "LOW")
                        confidence = result_item.get("issue_confidence", "LOW")

                        vuln_info = {
                            "filename": result_item.get("filename", "unknown"),
                            "line_number": result_item.get("line_number", 0),
                            "test_id": result_item.get("test_id", ""),
                            "test_name": result_item.get("test_name", ""),
                            "issue_text": result_item.get("issue_text", ""),
                            "severity": severity,
                            "confidence": confidence,
                            "code": result_item.get("code", ""),
                        }

                        vulnerabilities_by_severity[severity].append(vuln_info)

                    return {
                        "scan_successful": True,
                        "total_issues": len(bandit_data.get("results", [])),
                        "vulnerabilities_by_severity": vulnerabilities_by_severity,
                        "metrics": bandit_data.get("metrics", {}),
                        "scan_summary": {
                            "high_severity": len(vulnerabilities_by_severity["HIGH"]),
                            "medium_severity": len(
                                vulnerabilities_by_severity["MEDIUM"]
                            ),
                            "low_severity": len(vulnerabilities_by_severity["LOW"]),
                        },
                    }

                except json.JSONDecodeError:
                    return {
                        "scan_successful": False,
                        "error": "Could not parse Bandit JSON output",
                        "raw_output": result.stdout,
                    }
            else:
                return {
                    "scan_successful": False,
                    "error": f"Bandit scan failed with exit code {result.returncode}",
                    "stderr": result.stderr,
                }

        except Exception as e:
            return {
                "scan_successful": False,
                "error": f"Failed to run Bandit scan: {str(e)}",
            }

    def _analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze dependencies for known vulnerabilities."""

        dependency_analysis = {
            "scan_performed": True,
            "vulnerabilities_found": [],
            "recommendations": [],
        }

        # Check if safety is available for dependency scanning
        try:
            result = subprocess.run(
                ["python", "-m", "pip", "show", "safety"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                dependency_analysis["recommendations"].append(
                    "Install 'safety' package for dependency vulnerability scanning: pip install safety"
                )
                dependency_analysis["safety_available"] = False
            else:
                dependency_analysis["safety_available"] = True

                # Run safety check if available
                safety_result = subprocess.run(
                    ["python", "-m", "safety", "check", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if safety_result.returncode == 0:
                    try:
                        safety_data = json.loads(safety_result.stdout)
                        dependency_analysis["safety_results"] = safety_data
                        dependency_analysis["vulnerabilities_found"] = safety_data
                    except json.JSONDecodeError:
                        dependency_analysis["safety_error"] = (
                            "Could not parse safety output"
                        )

        except Exception as e:
            dependency_analysis["error"] = f"Dependency analysis failed: {str(e)}"

        return dependency_analysis

    def _scan_sensitive_data(self) -> Dict[str, Any]:
        """Scan for potential sensitive data exposure."""

        sensitive_patterns = [
            {"pattern": "password", "type": "Password"},
            {"pattern": "secret", "type": "Secret"},
            {"pattern": "token", "type": "Token"},
            {"pattern": "api_key", "type": "API Key"},
            {"pattern": "private_key", "type": "Private Key"},
            {"pattern": "database_url", "type": "Database URL"},
            {"pattern": "debug\\s*=\\s*True", "type": "Debug Mode"},
        ]

        sensitive_findings = []

        # Scan Python files for sensitive patterns
        for py_file in Path(".").rglob("*.py"):
            if any(
                exclude in str(py_file)
                for exclude in [".venv", "__pycache__", "node_modules"]
            ):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    for pattern_info in sensitive_patterns:
                        import re

                        if re.search(pattern_info["pattern"], line_lower):
                            sensitive_findings.append(
                                {
                                    "file": str(py_file),
                                    "line": line_num,
                                    "type": pattern_info["type"],
                                    "content": line.strip()[:100],  # First 100 chars
                                }
                            )

            except Exception:
                continue  # Skip files that can't be read

        return {
            "sensitive_data_found": len(sensitive_findings) > 0,
            "findings": sensitive_findings[:20],  # First 20 findings
            "total_findings": len(sensitive_findings),
            "recommendation": "Review and secure any sensitive data found in code",
        }

    def _validate_authentication(self) -> Dict[str, Any]:
        """Validate authentication and authorization mechanisms."""

        auth_analysis = {
            "authentication_present": False,
            "authorization_present": False,
            "security_headers": False,
            "recommendations": [],
        }

        # Check for FastAPI security implementations
        security_patterns = [
            "HTTPBearer",
            "HTTPBasic",
            "OAuth2PasswordBearer",
            "Security",
            "Depends",
            "@auth",
            "jwt",
            "token",
        ]

        auth_implementations = []

        for py_file in Path(".").rglob("*.py"):
            if any(exclude in str(py_file) for exclude in [".venv", "__pycache__"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                for pattern in security_patterns:
                    if pattern in content:
                        auth_implementations.append(
                            {
                                "file": str(py_file),
                                "pattern": pattern,
                                "type": "Authentication/Authorization",
                            }
                        )

            except Exception:
                continue

        auth_analysis["implementations_found"] = auth_implementations
        auth_analysis["authentication_present"] = len(auth_implementations) > 0

        if not auth_analysis["authentication_present"]:
            auth_analysis["recommendations"].append(
                "Implement proper authentication mechanisms (JWT, OAuth2, etc.)"
            )

        auth_analysis["recommendations"].extend(
            [
                "Add rate limiting to prevent brute force attacks",
                "Implement CORS properly for production",
                "Add security headers (HSTS, CSP, etc.)",
                "Use HTTPS in production environment",
            ]
        )

        return auth_analysis

    def _check_security_configs(self) -> Dict[str, Any]:
        """Check security configurations."""

        config_analysis = {
            "debug_mode_issues": [],
            "insecure_configurations": [],
            "missing_security_features": [],
            "recommendations": [],
        }

        # Check for debug mode in production
        for py_file in Path(".").rglob("*.py"):
            if any(exclude in str(py_file) for exclude in [".venv", "__pycache__"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                if "debug=True" in content or "DEBUG = True" in content:
                    config_analysis["debug_mode_issues"].append(str(py_file))

            except Exception:
                continue

        # Check for environment variable usage
        env_usage = self._check_environment_variables()
        config_analysis["environment_variables"] = env_usage

        # Standard security recommendations
        config_analysis["recommendations"] = [
            "Use environment variables for sensitive configuration",
            "Disable debug mode in production",
            "Implement proper logging without sensitive data",
            "Use secure session management",
            "Implement input validation and sanitization",
            "Add request timeout configurations",
            "Use secure database connection strings",
        ]

        return config_analysis

    def _check_environment_variables(self) -> Dict[str, Any]:
        """Check environment variable usage for security."""

        env_patterns = ["os.environ", "getenv", "env.", "Environment"]
        env_usage = []

        for py_file in Path(".").rglob("*.py"):
            if any(exclude in str(py_file) for exclude in [".venv", "__pycache__"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                for pattern in env_patterns:
                    if pattern in content:
                        env_usage.append({"file": str(py_file), "pattern": pattern})

            except Exception:
                continue

        return {
            "environment_variable_usage": len(env_usage) > 0,
            "files_using_env": env_usage,
            "recommendation": "Good practice: Using environment variables for configuration",
        }

    def _calculate_security_score(
        self, bandit_results: Dict, dependency_results: Dict, config_results: Dict
    ) -> Dict[str, Any]:
        """Calculate overall security score."""

        base_score = 100

        # Deduct points for security issues
        if bandit_results.get("scan_successful"):
            high_issues = bandit_results.get("scan_summary", {}).get("high_severity", 0)
            medium_issues = bandit_results.get("scan_summary", {}).get(
                "medium_severity", 0
            )
            low_issues = bandit_results.get("scan_summary", {}).get("low_severity", 0)

            # Deduct points based on severity
            base_score -= high_issues * 10  # 10 points per high severity
            base_score -= medium_issues * 3  # 3 points per medium severity
            base_score -= low_issues * 1  # 1 point per low severity

        # Deduct points for debug mode in production
        debug_issues = len(config_results.get("debug_mode_issues", []))
        base_score -= debug_issues * 15  # 15 points per debug mode file

        # Ensure score doesn't go below 0
        final_score = max(0, base_score)

        # Determine security tier
        if final_score >= 95:
            tier = "EXCELLENT"
        elif final_score >= 85:
            tier = "GOOD"
        elif final_score >= 70:
            tier = "ACCEPTABLE"
        elif final_score >= 50:
            tier = "NEEDS_IMPROVEMENT"
        else:
            tier = "CRITICAL"

        return {
            "security_score": final_score,
            "security_tier": tier,
            "breakdown": {
                "bandit_deductions": (
                    base_score - final_score
                    if bandit_results.get("scan_successful")
                    else 0
                ),
                "config_deductions": debug_issues * 15,
                "total_deductions": 100 - final_score,
            },
        }

    def _identify_critical_issues(self, bandit_results: Dict) -> List[Dict[str, Any]]:
        """Identify critical security issues that need immediate attention."""

        critical_issues = []

        if bandit_results.get("scan_successful"):
            high_severity_issues = bandit_results.get(
                "vulnerabilities_by_severity", {}
            ).get("HIGH", [])

            # Focus on the most critical issues
            critical_test_ids = [
                "B102",  # exec_used
                "B301",  # pickle
                "B506",  # yaml_load
                "B602",  # subprocess_popen_with_shell_equals_true
                "B603",  # subprocess_without_shell_equals_true
                "B608",  # hardcoded_sql_expressions
            ]

            for issue in high_severity_issues[:10]:  # Top 10 critical issues
                if issue.get("test_id") in critical_test_ids:
                    critical_issues.append(
                        {
                            "severity": "CRITICAL",
                            "test_id": issue.get("test_id"),
                            "test_name": issue.get("test_name"),
                            "file": issue.get("filename"),
                            "line": issue.get("line_number"),
                            "description": issue.get("issue_text"),
                            "priority": "IMMEDIATE",
                        }
                    )

        return critical_issues

    def _generate_remediation_plan(self) -> Dict[str, Any]:
        """Generate comprehensive security remediation plan."""

        remediation_plan = {
            "immediate_actions": [
                {
                    "action": "Fix Critical Vulnerabilities",
                    "description": "Address all HIGH severity issues identified by Bandit scan",
                    "timeline": "1-2 days",
                    "priority": "CRITICAL",
                },
                {
                    "action": "Secure Configuration",
                    "description": "Disable debug mode, secure environment variables",
                    "timeline": "0.5 days",
                    "priority": "HIGH",
                },
                {
                    "action": "Input Validation",
                    "description": "Implement comprehensive input validation and sanitization",
                    "timeline": "1 day",
                    "priority": "HIGH",
                },
            ],
            "short_term_actions": [
                {
                    "action": "Authentication Enhancement",
                    "description": "Implement robust authentication and authorization",
                    "timeline": "2-3 days",
                    "priority": "MEDIUM",
                },
                {
                    "action": "Security Headers",
                    "description": "Add comprehensive security headers (HSTS, CSP, etc.)",
                    "timeline": "1 day",
                    "priority": "MEDIUM",
                },
                {
                    "action": "Dependency Updates",
                    "description": "Update dependencies to latest secure versions",
                    "timeline": "1 day",
                    "priority": "MEDIUM",
                },
            ],
            "long_term_actions": [
                {
                    "action": "Security Monitoring",
                    "description": "Implement continuous security monitoring and alerting",
                    "timeline": "1 week",
                    "priority": "LOW",
                },
                {
                    "action": "Penetration Testing",
                    "description": "Conduct comprehensive penetration testing",
                    "timeline": "1 week",
                    "priority": "LOW",
                },
                {
                    "action": "Security Training",
                    "description": "Security awareness and secure coding practices",
                    "timeline": "Ongoing",
                    "priority": "LOW",
                },
            ],
        }

        return remediation_plan


def main():
    """Run comprehensive security validation and generate hardening recommendations."""

    print("🔒 KLERNO LABS SECURITY VALIDATION")
    print("🎯 TARGET: ENTERPRISE-GRADE SECURITY")
    print("=" * 60)

    validator = SecurityValidator()

    # Run comprehensive security scan
    security_report = validator.run_comprehensive_security_scan()

    # Save security report
    with open("comprehensive_security_report.json", "w") as f:
        json.dump(security_report, f, indent=2)

    # Print summary
    print(f"\n🔒 SECURITY VALIDATION COMPLETE")
    print("=" * 50)

    overall_score = security_report["overall_security_score"]
    print(f"Security Score: {overall_score['security_score']}/100")
    print(f"Security Tier: {overall_score['security_tier']}")

    if security_report["bandit_analysis"].get("scan_successful"):
        summary = security_report["bandit_analysis"]["scan_summary"]
        print(f"\nVulnerabilities Found:")
        print(f"   • HIGH Severity: {summary['high_severity']}")
        print(f"   • MEDIUM Severity: {summary['medium_severity']}")
        print(f"   • LOW Severity: {summary['low_severity']}")

    critical_issues = security_report["critical_issues"]
    if critical_issues:
        print(f"\n🚨 Critical Issues ({len(critical_issues)}):")
        for issue in critical_issues[:5]:  # Show first 5
            print(f"   • {issue['test_name']} in {issue['file']}:{issue['line']}")

    print(f"\n📋 Remediation Plan:")
    plan = security_report["remediation_plan"]
    print(f"   • Immediate Actions: {len(plan['immediate_actions'])}")
    print(f"   • Short-term Actions: {len(plan['short_term_actions'])}")
    print(f"   • Long-term Actions: {len(plan['long_term_actions'])}")

    print(f"\n📊 Detailed security report saved to: comprehensive_security_report.json")

    return security_report


if __name__ == "__main__":
    main()

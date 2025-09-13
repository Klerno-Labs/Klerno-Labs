# docs/security_testing_guide.md
# Security Testing Guide

## Overview

This guide provides comprehensive security testing procedures for the Klerno Labs platform, including automated scans, manual penetration testing, and vulnerability assessment.

## Automated Security Testing

### Dependency Vulnerability Scanning

```bash
# Run comprehensive security scan
python security_scan.py

# Individual scans
python -m safety check --json
python -m bandit -r app/ -f json
pip-audit --format=json
```

### Code Security Analysis

```bash
# Static analysis with bandit
bandit -r app/ -ll -f json -o security-report.json

# Type safety with mypy
mypy app/ --ignore-missing-imports

# Code quality with flake8
flake8 app/ --max-line-length=100
```

### Container Security Scanning

```bash
# Build production image
docker build --target production -t klerno-labs:security-test .

# Scan with Trivy
trivy image klerno-labs:security-test

# Scan with Docker Scout (if available)
docker scout cves klerno-labs:security-test
```

## Manual Penetration Testing Checklist

### Authentication & Authorization

- [ ] **Password Security**
  - Test password complexity requirements
  - Verify password hashing (bcrypt)
  - Check for password policy enforcement
  - Test account lockout mechanisms

- [ ] **Session Management**
  - Verify JWT token security
  - Test session timeout
  - Check secure cookie flags
  - Test session fixation attacks

- [ ] **API Key Security**
  - Test API key rotation
  - Verify key strength (entropy)
  - Check key storage security
  - Test unauthorized access

### Input Validation & Injection

- [ ] **SQL Injection**
  - Test all form inputs
  - Check query parameters
  - Verify parameterized queries
  - Test stored procedures

- [ ] **Cross-Site Scripting (XSS)**
  - Test reflected XSS
  - Check stored XSS
  - Verify CSP headers
  - Test DOM-based XSS

- [ ] **Command Injection**
  - Check file upload functionality
  - Test system command execution
  - Verify input sanitization

### Network Security

- [ ] **TLS/HTTPS**
  - Verify TLS version (1.2+)
  - Check certificate validity
  - Test cipher strength
  - Verify HSTS headers

- [ ] **Security Headers**
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy

### CSRF Protection

- [ ] **Token Validation**
  - Verify CSRF token generation
  - Test token validation
  - Check token entropy
  - Test missing token handling

### Data Protection

- [ ] **Sensitive Data**
  - Check encryption at rest
  - Verify encryption in transit
  - Test data masking
  - Check audit logging

## Penetration Testing Tools

### Network Scanning

```bash
# Nmap port scan
nmap -sV -sC <target-ip>

# SSL/TLS testing with testssl.sh
testssl.sh https://<target-domain>
```

### Web Application Testing

```bash
# OWASP ZAP automated scan
zap-cli quick-scan --self-contained --start-options '-config api.disablekey=true' https://<target>

# Nikto web vulnerability scanner
nikto -h https://<target>

# SQLMap for SQL injection testing
sqlmap -u "https://<target>/api/endpoint" --data="param=value"
```

### API Security Testing

```bash
# Test API endpoints with curl
curl -X POST https://<target>/api/analyze/tx \
  -H "Content-Type: application/json" \
  -H "x-api-key: invalid-key" \
  -d '{"test":"data"}'

# Use Postman/Insomnia for comprehensive API testing
# Test rate limiting, authentication, authorization
```

## Security Test Scenarios

### Scenario 1: Unauthorized API Access

**Objective**: Verify API key enforcement

**Steps**:
1. Attempt API calls without API key
2. Use invalid API key
3. Use expired/rotated key
4. Try session hijacking

**Expected Results**:
- 401 Unauthorized responses
- Audit logs generated
- No sensitive data exposure

### Scenario 2: Cross-Site Request Forgery

**Objective**: Test CSRF protection

**Steps**:
1. Create malicious form on external site
2. Attempt state-changing operations
3. Test missing CSRF tokens
4. Test token replay attacks

**Expected Results**:
- Operations blocked without valid CSRF token
- Security events logged
- User session protected

### Scenario 3: Data Exfiltration

**Objective**: Test data access controls

**Steps**:
1. Attempt unauthorized data export
2. Test SQL injection in queries
3. Try directory traversal
4. Test for information disclosure

**Expected Results**:
- Access denied for unauthorized users
- No sensitive data in error messages
- Audit trail of access attempts

### Scenario 4: Privilege Escalation

**Objective**: Test role-based access control

**Steps**:
1. Create viewer account
2. Attempt admin operations
3. Try to modify user roles
4. Test API endpoints by role

**Expected Results**:
- Role restrictions enforced
- Admin functions protected
- Audit logs for privilege attempts

## Compliance Testing

### GDPR Compliance

- [ ] Data minimization implemented
- [ ] Right to deletion supported
- [ ] Data portability available
- [ ] Consent management in place
- [ ] Privacy by design verified

### SOX Compliance

- [ ] Audit trails comprehensive
- [ ] Financial data protection
- [ ] Access controls documented
- [ ] Change management tracked

### AML/KYC Compliance

- [ ] Transaction monitoring active
- [ ] Risk scoring functional
- [ ] Alert generation working
- [ ] Reporting capabilities tested

## Vulnerability Assessment

### Critical Vulnerabilities

- Remote code execution
- SQL injection
- Authentication bypass
- Privilege escalation
- Data exposure

### High Vulnerabilities

- Cross-site scripting
- CSRF attacks
- Session hijacking
- Information disclosure
- Weak cryptography

### Medium Vulnerabilities

- Missing security headers
- Weak password policies
- Information leakage
- Directory listing
- Version disclosure

## Reporting Template

### Executive Summary

- Overall security posture
- Critical findings
- Risk assessment
- Recommendations

### Technical Findings

For each vulnerability:
- **Severity**: Critical/High/Medium/Low
- **CVSS Score**: Numeric score
- **Description**: Detailed explanation
- **Impact**: Business impact
- **Reproduction**: Step-by-step reproduction
- **Recommendation**: Remediation steps
- **Timeline**: Suggested fix timeline

### Evidence

- Screenshots
- HTTP requests/responses
- Log entries
- Code snippets

## Continuous Security Testing

### Automated Pipeline Integration

```yaml
# Add to CI/CD pipeline
security_tests:
  script:
    - python security_scan.py
    - bandit -r app/ -f json
    - safety check
    - trivy fs .
  artifacts:
    reports:
      security: security_report.json
```

### Regular Testing Schedule

- **Daily**: Dependency vulnerability scans
- **Weekly**: Code security analysis
- **Monthly**: Full penetration testing
- **Quarterly**: External security audit
- **Annually**: Compliance assessment

## Emergency Response

### Security Incident Response

1. **Identification**: Detect and confirm incident
2. **Containment**: Isolate affected systems
3. **Eradication**: Remove threat
4. **Recovery**: Restore normal operations
5. **Lessons Learned**: Document and improve

### Contacts

- **Security Team**: security@klerno.com
- **Development Team**: dev@klerno.com
- **Management**: management@klerno.com
- **External Auditor**: [Contact Information]

## Tools and Resources

### Open Source Tools

- OWASP ZAP
- Nmap
- Nikto
- SQLMap
- Bandit
- Safety

### Commercial Tools

- Burp Suite Professional
- Nessus
- Veracode
- Checkmarx
- Snyk

### Resources

- OWASP Top 10
- NIST Cybersecurity Framework
- CIS Controls
- ISO 27001
- SANS Top 25
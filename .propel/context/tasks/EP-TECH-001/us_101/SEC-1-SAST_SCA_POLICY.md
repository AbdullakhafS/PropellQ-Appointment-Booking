# SEC-1: SAST/SCA Policy Configuration

## Overview

This document defines the Static Application Security Testing (SAST) and Software Composition Analysis (SCA) policy for PropellQ. All PRs must pass security scanning before merge.

## 1. SAST (Static Application Security Testing)

### 1.1 Tool: Bandit

**Purpose**: Detect common security issues in Python code

**Configuration**:
- Tool: `bandit`
- Config file: `.bandit` (at project root)
- Command: `bandit -r app/src -f json -o bandit-report.json --severity-level medium`

### 1.2 Gate Policy

| Finding Severity | Action | Policy |
|------------------|--------|--------|
| CRITICAL | ❌ BLOCK MERGE | Must be fixed before PR merge. No exceptions except through formal waiver. |
| HIGH | ❌ BLOCK MERGE | Must be fixed or waived before PR merge. See SEC-2 for waiver process. |
| MEDIUM | ⚠️ REPORT ONLY | Report in PR but do not block merge. Must be tracked in backlog. |
| LOW | ℹ️ REPORT ONLY | Report in PR but do not block merge. Address in future improvements. |

### 1.3 Baseline Remediation

High/Critical Bandit checks that require remediation:

| Check ID | Name | Remediation |
|----------|------|-------------|
| B104 | Hardcoded bind all interfaces | Use environment variables for host binding, default to localhost |
| B105 | Hardcoded password strings | Use environment variables or secret management system |
| B106 | Hardcoded password function args | Extract to configuration/secrets, never hardcode |
| B107 | Hardcoded password defaults | Use secure defaults from config or environment |
| B201 | Flask debug = True | Set DEBUG=False in production, use environment variable |
| B301 | Pickle usage | Use JSON or MessagePack instead of pickle for untrusted data |
| B307 | Eval usage | Never use eval(). Use ast.literal_eval() or JSON for safe parsing |
| B308 | Mark safe usage (Django) | Validate all HTML before marking safe, use template auto-escaping |
| B310 | Urllib URL open | Validate URL scheme/host, use timeout, handle exceptions |
| B311 | Random for security | Use secrets.token_bytes() or os.urandom() for cryptographic purposes |
| B313-320 | XML parsing | Use defusedxml to prevent XXE attacks |
| B323 | Unverified SSL context | Always verify SSL certificates in production |
| B324 | Weak hashlib | Use SHA-256+ only, never MD5/SHA1 for security purposes |

### 1.4 Common False Positives & Handling

| Scenario | Tool Behavior | Resolution |
|----------|---------------|-----------|
| Password in test fixtures/mocks | HIGH/CRITICAL finding | Use `# noqa` or define in waiver (SEC-2) if intentional test fixture |
| Environment variable parsing in config | Potential finding | Use explicit validation: `assert os.getenv('VAR'), "VAR required"` |
| Cryptographic library imports | No finding | Bandit does not flag cryptography library usage |
| Intentional hardcoded demo values | Potential finding | Mark with `# nosec` comment or waiver if in non-production code |

---

## 2. SCA (Software Composition Analysis) - Dependency Scanning

### 2.1 Tool: pip-audit

**Purpose**: Detect known vulnerabilities in Python dependencies

**Configuration**:
- Tool: `pip-audit`
- Command: `pip-audit --desc --format json`

### 2.2 Gate Policy

| Vulnerability Severity | CVSS Score | Action | Policy |
|------------------------|-----------|--------|--------|
| CRITICAL | 9.0-10.0 | ❌ BLOCK MERGE | Must fix or waive immediately. Security team review required. |
| HIGH | 7.0-8.9 | ❌ BLOCK MERGE | Must fix or waive within 7 days via formal request. |
| MEDIUM | 4.0-6.9 | ⚠️ REPORT ONLY | Report in PR, fix in next sprint or waive if acceptable risk. |
| LOW | 0.1-3.9 | ℹ️ REPORT ONLY | Informational only, address in future maintenance. |

### 2.3 Dependency Management

**Pinning Strategy**:
```
# requirements.txt - pin major.minor, allow patches
package==1.2.*  # Latest patch of 1.2.x allowed

# For security-critical packages - pin exactly
cryptography==41.0.0  # DO NOT auto-update
```

**Update Frequency**:
- Weekly: Automated check for updates (report to #security channel)
- Monthly: Review and update non-security dependencies
- Immediately: Security advisories with CRITICAL/HIGH severity

**Vulnerable Dependency Process**:
1. Bandit/pip-audit detects in CI
2. Create issue in `#security` project
3. Assign to on-call security engineer
4. Determine if fix available or waiver needed
5. PR must wait for security approval

---

## 3. License Compliance (Future SCA)

**Planned**: Add license scanning (LicenseCheck) to prevent GPL/copyleft violations

Current scope: Dependency vulnerability scanning only

---

## 4. Waiver and Exception Workflow

See [SEC-2: Security Waiver Workflow](./SEC-2-SECURITY_WAIVER_WORKFLOW.md)

---

## 5. Baseline Security Requirements

All new code must meet:

✅ No CRITICAL SAST findings  
✅ No HIGH SAST findings (except waived)  
✅ No CRITICAL/HIGH vulnerability dependencies (except waived)  
✅ HTTPS only for all external calls  
✅ Secrets stored in environment variables (never hardcoded)  
✅ SQL queries use parameterized statements  
✅ File uploads validated by type/size  
✅ All user input validated and sanitized  

---

## 6. CI/CD Integration

### 6.1 Workflow Integration

Gate is active in `.github/workflows/ci-quality-gates.yml`:

```yaml
- Bandit runs as part of 'security' job
- pip-audit runs as part of 'security' job
- CRITICAL/HIGH findings block merge
- PR gets annotated with findings
```

### 6.2 Handling Security Failures

**When PR blocked due to security findings**:

1. Review Bandit report (JSON format)
2. Determine root cause:
   - **Is finding valid?** → Fix code
   - **Is finding false positive?** → Request waiver (SEC-2)
3. Rerun CI after fix/waiver

**To view detailed Bandit report**:

```bash
bandit -r app/src -f txt  # Human-readable
bandit -r app/src -f json > report.json  # Programmatic
```

---

## 7. Exceptions and Deviations

### When are exceptions allowed?

1. **Test code**: Bandit can flag security issues in test fixtures
   - Solution: Use `# nosec` comment or request waiver
   
2. **Demo/example code**: Code intentionally showing vulnerability for educational purposes
   - Solution: Mark clearly, request waiver with explicit scope

3. **Third-party library vulnerability**: Dependency has vulnerability but no patch available
   - Solution: Request waiver with risk assessment and mitigation plan

4. **Transitive dependency**: Vulnerability in dependency-of-dependency
   - Solution: Pin parent dependency to version without vulnerability

### Waiver not allowed for:

❌ Production code with authentication bypass vulnerabilities  
❌ Production code with SQL injection vulnerabilities  
❌ Production code accessing secrets without encryption  
❌ Hardcoded credentials of any kind  

---

## 8. Monitoring and Compliance

### Quarterly Review

- Review all active waivers
- Analyze trend in findings (increasing? decreasing?)
- Update policy based on threat landscape
- Document exemptions and their business justification

### Metrics

- Total CRITICAL/HIGH findings: **Target = 0**
- Median time to waiver resolution: **Target < 7 days**
- Security findings per KLOC: **Target < 1**
- Dependency vulnerability recurrence: **Target = 0**

---

## 9. References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)

---

**Last Updated**: 2026-06-22  
**Approved By**: Security Team  
**Effective Date**: 2026-06-22  
**Next Review**: 2026-09-22

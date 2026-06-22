# SEC-1: SAST/SCA Policy Configuration

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Platform engineers, security team, backend engineers

---

## 1. Overview

This document defines the security scanning policy for SAST (Static Application Security Testing) and SCA (Software Composition Analysis) scanning, including severity thresholds, gate behavior, and baseline rules.

**Objectives:**
- Define severity thresholds for vulnerability findings
- Establish gate behavior (block/warn/pass)
- Configure SAST baseline rules
- Define SCA/dependency scanning policy
- Ensure consistent security posture

---

## 2. SAST Policy Configuration

### 2.1 Severity Levels and Gate Behavior

| Severity | CVSS Score | Gate Behavior | Auto-Block | Waiver Allowed | SLA |
|---|---|---|---|---|---|
| **CRITICAL** | 9.0-10.0 | 🛑 BLOCK | ✅ Yes | ⚠️ Restricted (24h max) | Fix within 24h |
| **HIGH** | 7.0-8.9 | 🛑 BLOCK | ✅ Yes | ✅ Yes (7-day review) | Fix within 7 days |
| **MEDIUM** | 4.0-6.9 | ⚠️ WARN | ❌ No auto-block | ✅ Yes (open-ended) | Fix within 30 days |
| **LOW** | 0.1-3.9 | ℹ️ INFO | ❌ No | N/A (no waiver) | Fix within 90 days |

### 2.2 SAST Rule Categories

**Security scanning covers:**

```
Injection Attacks (CWE-89, CWE-78)
├─ SQL Injection
├─ OS Command Injection
├─ LDAP Injection
└─ XML Injection

Authentication & Authorization (CWE-287, CWE-347)
├─ Hardcoded Credentials
├─ Weak Cryptography
├─ Missing MFA
└─ Privilege Escalation

Sensitive Data (CWE-327, CWE-338)
├─ Hardcoded Secrets
├─ Weak Hashing
├─ Inadequate Logging
└─ Data Exposure

Input Validation (CWE-20)
├─ Missing Validation
├─ Improper Type Checking
├─ Buffer Overflow
└─ XXE (XML External Entity)

Configuration (CWE-200, CWE-668)
├─ Insecure Defaults
├─ Exposed Configuration
├─ Debug Mode Enabled
└─ CORS Misconfiguration
```

### 2.3 SAST Tools Configuration

#### Semgrep (Recommended for all languages)

```yaml
# .semgrep.yml
rules:
  - id: sql-injection
    pattern-either:
      - pattern: $DB.query($STR + $VAR)
      - pattern: $QUERY = "SELECT * WHERE id = '" + $VAR + "'"
    message: "SQL Injection: Use parameterized queries"
    severity: CRITICAL
    languages: [javascript, typescript, python, csharp]
    
  - id: hardcoded-secret
    pattern-either:
      - pattern-regex: |
          password\s*=\s*['"](.*)['"]\s*[,}]
      - pattern-regex: |
          api_key\s*=\s*['"](sk-.*)['"]\s*[,}]
    message: "Hardcoded Secret: Move to environment variable"
    severity: CRITICAL
    
  - id: weak-crypto
    pattern-either:
      - pattern: MD5(...)
      - pattern: SHA1(...)
    message: "Weak Cryptography: Use SHA256 or stronger"
    severity: HIGH
```

**GitHub Actions Integration:**

```yaml
name: SAST Scan

on:
  pull_request:
    branches: [main, develop]

jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/owasp-top-ten
            p/cwe-top-25
          generateSarif: true
          
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: semgrep.sarif
          category: semgrep
          
      - name: Check for blocking findings
        run: |
          # Parse SARIF and check for CRITICAL/HIGH
          if grep -q '"level": "error"' semgrep.sarif; then
            echo "❌ CRITICAL/HIGH severity findings detected"
            exit 1
          fi
          echo "✅ SAST scan passed"
```

#### Language-Specific SAST

**C# / .NET:**
```yaml
sonarqube:
  enabled: true
  severity: CRITICAL, HIGH
  language: csharp
  rules:
    - CWE-89: SQL Injection
    - CWE-427: Uncontrolled Search Path
    - S2092: Hardcoded Credentials
    - S2068: Weak Cryptography
```

**TypeScript / JavaScript:**
```yaml
eslint-security:
  enabled: true
  rules:
    - plugin:security/recommended
    - plugin:@typescript-eslint/recommended-requiring-type-checking
  severity: error
```

**Python:**
```yaml
bandit:
  enabled: true
  severity: HIGH, CRITICAL
  exclude_dirs:
    - tests
    - venv
  tests: [B101, B105, B106, B107, B601, B602, B605, B607]
```

---

## 3. SCA/Dependency Scanning Policy

### 3.1 Vulnerability Severity and Gate Behavior

| Severity | CVSS | Known Exploit | Gate Behavior | Auto-Update |
|---|---|---|---|---|
| **CRITICAL** | 9.0-10.0 | ✅ Yes | 🛑 BLOCK | ✅ Auto-merge |
| **HIGH** | 7.0-8.9 | ⚠️ Likely | 🛑 BLOCK | ✅ Auto-merge |
| **MEDIUM** | 4.0-6.9 | ❌ Unlikely | ⚠️ WARN | ⏳ Manual review |
| **LOW** | 0.1-3.9 | ❌ No | ℹ️ INFO | ❌ No auto |

### 3.2 Dependency Update Policy

**Automated Dependency Management:**

```yaml
renovate:
  enabled: true
  
  # Critical/High vulnerabilities
  vulnerabilityAlerts:
    enabled: true
    automerge: true  # Auto-merge security updates
    
  # Regular updates
  packageRules:
    - matchUpdateTypes: [minor, patch]
      automerge: true
      automergeType: pr
      
    - matchUpdateTypes: [major]
      automerge: false  # Manual review for breaking changes
      
    - matchDatasources: [npm]
      rangeStrategy: bump
      
    - matchDatasources: [nuget]
      rangeStrategy: bump
```

### 3.3 SCA Tools

#### npm / Node.js

```bash
# Install npm audit fix helper
npm install -g npm-audit-resolver

# Run audit
npm audit --audit-level=moderate

# Generate SARIF report
npm audit --json > audit-results.json

# Config: .npmrc
audit-level=moderate
save-exact=true
```

**GitHub Actions:**

```yaml
- name: npm Audit
  run: npm audit --audit-level=high --json > npm-audit.json || true
  
- name: Check High/Critical
  run: |
    if grep -q '"severity":"high"\|"severity":"critical"' npm-audit.json; then
      echo "❌ High/Critical vulnerabilities found"
      cat npm-audit.json
      exit 1
    fi
```

#### Snyk (Multi-language)

```bash
# Install Snyk
npm install -g snyk

# Test dependencies
snyk test \
  --severity-threshold=high \
  --json > snyk-report.json
```

**GitHub Actions Integration:**

```yaml
- uses: snyk/actions/setup@master
  
- name: Snyk Scan
  run: snyk test \
    --severity-threshold=high \
    --json-file-output=snyk-report.json
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

#### License Scanning

**FOSSA (License Compliance):**

```yaml
- name: FOSSA Scan
  uses: fossas/fossa-action@main
  with:
    fossa-api-key: ${{ secrets.FOSSA_API_KEY }}
    
- name: Check License Compliance
  run: fossa test
```

**Approved Licenses:**
```
Apache-2.0
MIT
BSD-2-Clause
BSD-3-Clause
ISC
GPL-3.0 (only in non-core dependencies)
```

**Forbidden Licenses:**
```
AGPL-3.0 (viral - forbidden for proprietary code)
GPL-1.0, GPL-2.0 (weak open source compliance)
SSPL (server-side public license - restricted)
```

---

## 4. Policy Enforcement Rules

### 4.1 Merge Gate Rules

| Finding Type | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| SAST Finding | 🛑 BLOCK | 🛑 BLOCK | ⚠️ WARN | ℹ️ INFO |
| Vulnerable Dependency | 🛑 BLOCK | 🛑 BLOCK | ⚠️ WARN | ℹ️ INFO |
| License Issue | ❌ FAIL (if forbidden) | ⚠️ WARN | ℹ️ INFO | - |
| Outdated Dependency | ⚠️ WARN (if HIGH risk) | ⚠️ WARN | ℹ️ INFO | - |

### 4.2 Enforcement Configuration

```yaml
# GitHub Branch Protection
branch-protection-rules:
  required_status_checks:
    - SAST Scan (required, no dismissal)
    - SCA Scan (required, no dismissal)
    - Lint (required)
    - Build (required)
    - Tests (required)
    
  dismiss_stale_reviews: false
  require_code_review: 1
  require_status_checks_to_pass_before_merge: true
```

### 4.3 Auto-Remediation

**Automatic fixes available for:**

1. ✅ Vulnerable dependency updates
   - Auto-create PR with updated version
   - Auto-merge if tests pass

2. ✅ License issues
   - Auto-flag and notify
   - Manual review required

3. ⚠️ SAST findings
   - Suggest fix (not auto-applied)
   - Manual developer action required

---

## 5. Baseline SAST Rules by Language

### 5.1 TypeScript/JavaScript Baseline

**Enabled Rules:**
```
CWE-89: SQL Injection
CWE-78: OS Command Injection
CWE-79: Cross-site Scripting (XSS)
CWE-95: Eval
CWE-327: Weak Cryptography
CWE-338: Use of Cryptographically Weak Random
CWE-347: Improper Verification of Cryptographic Signature
CWE-434: Unrestricted Upload
CWE-502: Deserialization of Untrusted Data
CWE-503: Using the Wrong API
```

**Severity Mapping:**
```
CRITICAL: SQL Injection, OS Command Injection, XXE, Deserialization
HIGH: XSS, Hardcoded Secrets, Weak Crypto, Missing Auth
MEDIUM: Missing Input Validation, Error Handling
LOW: Code Quality, Performance
```

### 5.2 C# / .NET Baseline

**Enabled Rules:**
```
CWE-89: SQL Injection (use parameterized queries)
CWE-78: OS Command Injection
CWE-327: Weak Cryptography (use SHA256+)
CWE-347: Signature Verification
CWE-502: Unsafe Deserialization
CWE-522: Weak Password Storage
CWE-565: Reliance on Cookies
```

### 5.3 Python Baseline

**Enabled Rules:**
```
CWE-78: OS Command Injection (use subprocess, not eval)
CWE-89: SQL Injection (use ORM or parameterized)
CWE-327: Weak Cryptography
CWE-502: Pickle Deserialization
CWE-506: Logging of Sensitive Information
```

---

## 6. SCA Baseline Rules

### 6.1 Dependency Quality Criteria

```
✅ Actively Maintained
   - Latest version released within 90 days
   - Responds to security issues within 30 days
   
✅ No Known Critical Vulnerabilities
   - NVD/CVE database checked
   - No CRITICAL or unpatched HIGH severity

✅ License Compliance
   - Approved license (Apache 2.0, MIT, BSD-3)
   - Not GPL/AGPL for proprietary code
   
✅ Community Adoption
   - npm downloads > 1M/week (for frontend)
   - npm downloads > 100k/week (for backend)
```

### 6.2 Exempted Packages

**Some packages allowed without license restriction:**

```
Development Dependencies Only:
- jest, vitest, mocha (testing)
- typescript, eslint (dev tools)
- webpack, vite (build tools)

Rationale: Only used during development, not shipped
```

---

## 7. Configuration Files

### 7.1 Semgrep Config (.semgrep.yml)

```yaml
rules:
  - id: sql-injection
    patterns:
      - pattern-either:
          - pattern: $DB.query($STR + $VAR)
          - pattern: $QUERY = "SELECT " + $VAR
    message: SQL injection vulnerability - use parameterized queries
    severity: CRITICAL
    languages: [csharp, javascript, python]
    
  - id: hardcoded-credentials
    patterns:
      - pattern-either:
          - pattern-regex: password\s*=\s*["'](.*?)["']
          - pattern-regex: api_key\s*=\s*["'](sk-.*?)["']
    message: Hardcoded credentials found - move to env var
    severity: CRITICAL

  - id: weak-crypto
    patterns:
      - pattern-either:
          - pattern: MD5(...)
          - pattern: SHA1(...)
    message: Weak cryptography - use SHA256+
    severity: HIGH
```

### 7.2 Snyk Config (.snyk)

```yaml
version: v1.0.0
ignore: {}
patch: {}
policies:
  - identifier: high-severity
    rules:
      - type: license
        rule: AGPL-3.0
        action: fail
      - type: vulnerability
        rule: CVSS >= 7
        action: block
```

### 7.3 GitHub Actions Workflow

```yaml
name: Security Scanning

on:
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  sast:
    name: SAST Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit
          generateSarif: true
      - uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: semgrep.sarif

  sca:
    name: Dependency Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm audit --audit-level=high
      - uses: snyk/actions/setup@master
      - run: snyk test --severity-threshold=high
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  license:
    name: License Compliance
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: fossas/fossa-action@main
        with:
          fossa-api-key: ${{ secrets.FOSSA_API_KEY }}
      - run: fossa test
```

---

## 8. Success Criteria

For SEC-1 completion, verify:

- [ ] SAST severity thresholds defined (CRITICAL, HIGH, MEDIUM, LOW)
- [ ] Gate behavior configured (BLOCK, WARN, INFO)
- [ ] SCA policy defined for dependencies
- [ ] Vulnerability SLA established (24h critical, 7d high)
- [ ] SAST rules configured for all languages
- [ ] SCA tools integrated (npm audit, Snyk, FOSSA)
- [ ] License scanning enabled
- [ ] GitHub Actions workflows created
- [ ] Auto-remediation configured for dependencies
- [ ] Baseline rules documented per language

---

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CWE/CVSS Severity: https://nvd.nist.gov/vuln/detail/CVE-2021-44228
- Semgrep: https://semgrep.dev/
- Snyk: https://snyk.io/
- npm Audit: https://docs.npmjs.com/cli/v8/commands/npm-audit

**Next:** [SEC-2: Waiver and Exception Workflow](sec-waiver-exception-workflow.md)

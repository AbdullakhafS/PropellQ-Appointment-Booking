# CI-1: Required Check Workflow Design

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, CI/CD platform teams, DevOps

---

## 1. Overview

This document defines the required quality gates and check workflow that must pass before a pull request can be merged. All checks follow a **fail-fast strategy** with parallel execution where possible to minimize feedback latency.

**Objectives:**
- Define mandatory checks that block merge on failure
- Implement fail-fast strategy for quick feedback
- Parallelize independent checks
- Provide actionable error messaging
- Ensure consistent quality across all code changes

---

## 2. Required Check Categories

### 2.1 Check Taxonomy

```
PR Merge Checks
├─ Code Quality Checks (FAIL-FAST)
│  ├─ Linting (ESLint, Pylint, etc.)
│  ├─ Type Checking (TypeScript, mypy)
│  └─ Code Formatting (Prettier, Black)
│
├─ Build & Compilation (FAIL-FAST)
│  ├─ Build Success
│  ├─ Artifact Generation
│  └─ Package Creation
│
├─ Test Coverage (FAIL-FAST)
│  ├─ Unit Tests
│  ├─ Integration Tests
│  └─ Contract Tests
│
├─ Security Scanning (BLOCKING)
│  ├─ SAST (Static Application Security Testing)
│  ├─ SCA (Software Composition Analysis)
│  └─ Secrets Detection
│
└─ Governance Checks
   ├─ Commit Message Format
   ├─ Branch Name Format
   └─ Documentation Coverage
```

---

## 3. PR Pipeline Stages

### 3.1 Pipeline Architecture

```
┌──────────────────────────────────────────────────────┐
│ Trigger: PR Created/Updated                          │
└────────────────────┬─────────────────────────────────┘
                     │
         ┌───────────▼─────────────┐
         │ STAGE-1: LINT/FORMAT    │ (2-3 min)
         │ (Fail-fast)             │
         └───────────┬─────────────┘
                     │ ✅ PASS → Continue
                     │ ❌ FAIL → BLOCK + Annotation
                     │
         ┌───────────▼─────────────┐
         │ STAGE-2: BUILD          │ (3-5 min)
         │ (Parallel with tests)   │
         └───────────┬─────────────┘
                     │ ✅ PASS → Continue
                     │ ❌ FAIL → BLOCK + Annotation
                     │
     ┌───────────────┴────────────────┐
     │                                 │
 ┌───▼──────┐             ┌──────────▼──┐
 │STAGE-3a: │             │STAGE-3b:    │
 │UNIT TESTS│             │SEC SCANNING │
 │(2-4 min) │             │(3-6 min)    │
 └───┬──────┘             └──────────┬──┘
     │ ✅ PASS/SKIP        │ ✅ PASS
     │ ❌ FAIL → BLOCK     │ ⚠️ WARNING
     │                     │ ❌ CRITICAL → BLOCK
     │                     │
     └───────────┬─────────┘
                 │
         ┌───────▼──────────┐
         │STAGE-4: SUMMARY  │
         │Check Required    │
         │All Passed?       │
         └───────┬──────────┘
                 │
         ┌───────▼──────────────┐
         │ Can Merge? (Green)   │
         │ Or Block? (Red)      │
         └──────────────────────┘
```

### 3.2 Execution Strategy

**Fail-Fast:**
- All quality checks execute in **sequence** (not parallel)
- First critical failure stops pipeline
- Reduces CI resource consumption
- Provides immediate feedback

**Example timing:**
- Lint failure at 1 min → STOP, give feedback
- Build failure at 4 min → STOP, give feedback
- Test failure at 7 min → STOP, give feedback
- All pass → Continue to security scanning

---

## 4. Required Checks by Language

### 4.1 TypeScript / Node.js / React

**Mandatory Checks (ALL MUST PASS):**

```yaml
lint:
  - tool: ESLint
    rules: .eslintrc.json
    severity: error  # Fail on error
    timeout: 120s

type-check:
  - tool: TypeScript
    strict: true
    version: "^5.1"
    timeout: 180s

format-check:
  - tool: Prettier
    config: .prettierrc
    check-only: true  # Don't auto-fix in CI
    timeout: 60s

test:
  - tool: Jest / Vitest
    coverage-threshold: 80%
    timeout: 300s
    retry: "none"  # No retry for flaky tests (unless explicitly tagged)

build:
  - tool: Webpack / Vite / TypeScript Compiler
    output: dist/
    timeout: 300s
```

**Example ESLint Configuration:**
```json
{
  "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
  "rules": {
    "no-console": ["warn", { "allow": ["warn", "error"] }],
    "no-debugger": "error",
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/strict-boolean-expressions": "error",
    "@typescript-eslint/explicit-function-return-types": "warn"
  },
  "plugins": ["@typescript-eslint"]
}
```

### 4.2 C# / .NET

**Mandatory Checks (ALL MUST PASS):**

```yaml
lint:
  - tool: StyleCop / Roslyn Analyzers
    rules: .editorconfig
    severity: error
    timeout: 180s

build:
  - tool: dotnet build
    configuration: Release
    target-framework: net9.0
    timeout: 300s

test:
  - tool: xUnit / NUnit
    filter: "Category!=Slow"
    coverage-threshold: 80%
    timeout: 300s
    retry: "none"

format-check:
  - tool: dotnet format --verify-no-changes
    timeout: 120s
```

**Example .editorconfig:**
```ini
[*.cs]
csharp_indent_case_contents = true
indent_style = space
indent_size = 4
dotnet_style_predefined_type_for_locals_parameters_members = true:warning
csharp_prefer_braces = true:silent
```

### 4.3 Python

**Mandatory Checks (ALL MUST PASS):**

```yaml
lint:
  - tool: Pylint
    min-score: 8.0
    timeout: 180s

type-check:
  - tool: mypy
    strict: true
    timeout: 120s

format-check:
  - tool: Black
    check: true
    line-length: 100
    timeout: 60s

test:
  - tool: pytest
    coverage-threshold: 80%
    timeout: 300s
    markers: "not slow"
```

---

## 5. Fail-Fast Implementation

### 5.1 GitHub Actions Fail-Fast Example

```yaml
name: PR Quality Gates
on:
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run lint
        # Failure here stops the job immediately
        # No continue-on-error flag

  build:
    needs: lint  # Only run if lint passes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
        # Failure here stops the job

  test:
    needs: build  # Only run if build passes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test:coverage
        # Failure here stops the job

  security:
    needs: test  # Only run if tests pass
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
```

**Key patterns:**
- `needs: <previous-job>` — Enforces sequence
- No `continue-on-error: true` — Fail immediately
- Each job runs only if previous passes

### 5.2 Parallel Execution Where Safe

For **independent** checks, parallelize:

```yaml
test-unit:
  runs-on: ubuntu-latest
  # Independent of test-integration

test-integration:
  runs-on: ubuntu-latest
  # Independent of test-unit

sast-scan:
  runs-on: ubuntu-latest
  # Can run in parallel with tests

# Final check that all required jobs passed
merge-readiness:
  needs: [lint, build, test-unit, test-integration, sast-scan]
  if: always()  # Run even if previous jobs failed
  runs-on: ubuntu-latest
  steps:
    - name: Check all required checks passed
      run: |
        if [ "${{ needs.lint.result }}" != "success" ]; then
          echo "Lint failed"
          exit 1
        fi
        if [ "${{ needs.build.result }}" != "success" ]; then
          echo "Build failed"
          exit 1
        fi
        exit 0
```

---

## 6. Check Configuration by Project Type

### 6.1 Frontend (React/Angular/Vue)

**All mandatory:**
```
✅ ESLint
✅ TypeScript (strict mode)
✅ Prettier formatting
✅ Unit tests (Jest/Vitest)
✅ Build (Webpack/Vite)
✅ SCA (npm audit / Snyk)
✅ SAST (Semgrep)
⚠️ E2E tests (optional, separate job)
```

### 6.2 Backend (.NET / Node.js / Python)

**All mandatory:**
```
✅ Code linter (ESLint/Pylint/StyleCop)
✅ Type checking
✅ Unit tests
✅ Integration tests (if applicable)
✅ Build
✅ SCA (dependencies)
✅ SAST (code analysis)
✅ Secrets detection
```

### 6.3 Infrastructure (Terraform / Bicep)

**All mandatory:**
```
✅ Terraform/Bicep format check
✅ Terraform validate
✅ tflint
✅ Terraform plan
✅ SAST (checkov/tfsec)
✅ Secrets detection
```

---

## 7. Timeout Configuration

**Strict timeouts prevent hanging jobs:**

| Check | Timeout | Rationale |
|---|---|---|
| Lint | 2 min | Should be fast |
| Build | 5-10 min | Compilation can be slow |
| Unit Tests | 5 min | Should run fast |
| Integration Tests | 10 min | May require setup |
| SAST Scan | 10 min | Security scans can be thorough |
| SCA Scan | 5 min | Dependency analysis |

**Implementation:**
```yaml
- name: Run ESLint
  run: npm run lint
  timeout-minutes: 2
  
- name: Build Project
  run: npm run build
  timeout-minutes: 10
```

---

## 8. Check Result Format

**All checks must report results in standardized format:**

### 8.1 JSON Output (for parsing)

```json
{
  "check_name": "ESLint",
  "status": "failed",
  "severity": "error",
  "timestamp": "2026-06-22T10:00:00Z",
  "duration_seconds": 45,
  "errors": [
    {
      "file": "src/App.tsx",
      "line": 42,
      "column": 15,
      "message": "Unexpected console.log",
      "rule": "no-console"
    }
  ],
  "error_count": 1,
  "warning_count": 3
}
```

### 8.2 Exit Codes

```
0 = All checks passed
1 = Critical failure (blocks merge)
2 = Warning (merge allowed but flagged)
```

---

## 9. Check Dependencies Matrix

| Check | Depends On | Blocks Merge | Retryable |
|---|---|---|---|
| Lint | SCM | ✅ Yes | ❌ No |
| Build | Lint | ✅ Yes | ❌ No |
| Unit Test | Build | ✅ Yes | ⚠️ With retry limit |
| Integration Test | Build | ⚠️ Warns only | ✅ Yes (up to 2x) |
| SAST Scan | Lint | ✅ Yes (High/Critical) | ❌ No |
| SCA Scan | Build | ✅ Yes (High/Critical) | ❌ No |

---

## 10. Execution Order (Strict Sequence)

```
1. Code checkout
2. Lint/Format check          (2-3 min) → FAIL-FAST
3. Build                      (3-5 min) → FAIL-FAST
4. Run Tests                  (2-4 min) → FAIL-FAST
5. Security scanning          (3-6 min)
6. Merge readiness check      (1 min)
───────────────────
Total: 14-23 minutes
```

---

## 11. Configuration Files Reference

**Example `.github/workflows/pr-checks.yml`:**

```yaml
name: PR Quality Gates

on:
  pull_request:
    branches: [main, develop]
    types: [opened, synchronize, reopened]

jobs:
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run format:check

  build:
    name: Build
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

  test:
    name: Unit Tests
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage/coverage-final.json
          min-coverage-percentage: 80

  sast:
    name: SAST Scanning
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g semgrep
      - run: semgrep --config=p/security-audit .

  sca:
    name: SCA Scanning
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high

  check-ready-to-merge:
    name: Ready to Merge
    needs: [lint, build, test, sast, sca]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Check all required checks passed
        run: |
          echo "Checking all required checks..."
          if [ "${{ needs.lint.result }}" != "success" ]; then
            echo "❌ Lint check failed"
            exit 1
          fi
          if [ "${{ needs.build.result }}" != "success" ]; then
            echo "❌ Build check failed"
            exit 1
          fi
          if [ "${{ needs.test.result }}" != "success" ]; then
            echo "❌ Test check failed"
            exit 1
          fi
          if [ "${{ needs.sast.result }}" != "success" ]; then
            echo "❌ SAST scan failed"
            exit 1
          fi
          if [ "${{ needs.sca.result }}" != "success" ]; then
            echo "❌ SCA scan failed"
            exit 1
          fi
          echo "✅ All required checks passed!"
```

---

## 12. Success Criteria

For CI-1 completion, verify:

- [ ] Required checks defined for each language (TypeScript, C#, Python)
- [ ] Fail-fast strategy implemented (sequential execution)
- [ ] Timeout configured for each check (max 2-10 min per check)
- [ ] Check dependencies defined and enforced
- [ ] Result format standardized (JSON, exit codes)
- [ ] Total pipeline time < 25 minutes
- [ ] GitHub Actions workflow file created and tested

---

## References

- GitHub Actions Documentation: https://docs.github.com/en/actions
- ESLint Configuration: https://eslint.org/docs/latest/use/configure/configuration-files
- Prettier: https://prettier.io/docs/en/
- Jest: https://jestjs.io/docs/configuration

**Next:** [CI-2: PR Annotation and Result Reporting](ci-pr-annotation-reporting.md)

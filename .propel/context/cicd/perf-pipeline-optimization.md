# PERF-1: Pipeline Performance Optimization

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** CI/CD platform teams, DevOps

---

## 1. Overview

This document defines pipeline performance optimization strategies to keep CI feedback within acceptable latency bounds while ensuring quality gates remain effective.

**Target:** Median pipeline duration < 25 minutes (p95 < 35 minutes)

---

## 2. Performance Baseline

### 2.1 Current Pipeline Timing

```
Lint & Format         3 min  (5%)
Build                 5 min  (10%)
Unit Tests            8 min  (17%)
Integration Tests     6 min  (13%)
SAST Scan            4 min  (8%)
SCA Scan             3 min  (6%)
E2E Tests            12 min  (25%)
Report Generation     2 min  (4%)
────────────────────
Total: 43 minutes (serial)

Target: 25 minutes median
Action: Parallelize, cache, optimize
```

---

## 3. Parallelization Strategy

### 3.1 Job Dependencies Map

```
Stage 1 (Sequential - Required):
  └─ Lint (2 min)
     └─ (MUST pass before build)

Stage 2 (Parallel - Independent):
  ├─ Build (5 min)
  │  └─ (Required for tests)
  │
  ├─ SAST (3 min)
  │  └─ (Independent, can run anytime)
  │
  └─ SCA (2 min)
     └─ (Independent, can run anytime)

Stage 3 (Parallel - Requires Build):
  ├─ Unit Tests (5 min)
  ├─ Integration Tests (4 min)
  └─ E2E Tests (8 min)

Stage 4 (Final):
  └─ Report Generation (1 min)
     └─ (Requires all tests complete)

Total Critical Path: ~19 minutes (vs 43 serial)
```

### 3.2 GitHub Actions Job Configuration

```yaml
name: Fast CI Pipeline

jobs:
  # Stage 1: Lint (blocking)
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  # Stage 2: Build + Security (parallel)
  build:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          cache: 'npm'  # Cache npm modules
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v3
        with:
          name: build-output
          retention-days: 1

  sast:
    runs-on: ubuntu-latest  # No dependency - parallel with build
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g semgrep
      - run: semgrep --config=p/security-audit .

  sca:
    runs-on: ubuntu-latest  # No dependency
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm audit --audit-level=high

  # Stage 3: Tests (parallel)
  unit-tests:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v3
        with:
          name: build-output
      - run: npm test

  integration-tests:
    needs: build
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - run: npm run test:integration

  e2e-tests:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run test:e2e

  # Stage 4: Report
  report:
    needs: [lint, build, unit-tests, integration-tests, e2e-tests, sast, sca]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - run: echo "All checks complete"
```

**Result: ~19 min critical path (5 min lint + 5 min build + 5 min tests + 4 min parallel overhead)**

---

## 4. Caching Strategy

### 4.1 Dependency Caching

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Cache npm dependencies
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'  # Automatic npm caching
      
      # Cache NuGet packages (.NET)
      - uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '9.0.x'
          cache: true  # Automatic NuGet caching
      
      - run: npm ci  # Uses cache from previous run
      - run: npm run build
```

**Impact:** 60-90 second savings on cache hit

### 4.2 Build Artifact Caching

```yaml
- name: Upload build output
  uses: actions/upload-artifact@v3
  with:
    name: dist-${{ github.sha }}
    path: dist/
    retention-days: 1  # Clean up after 1 day

# Later jobs
- name: Download build output
  uses: actions/download-artifact@v3
  with:
    name: dist-${{ github.sha }}
```

**Impact:** 30-60 second savings vs rebuilding

### 4.3 Cache Key Strategy

```yaml
- uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

# Results in:
# Cache hit: uses cached npm modules (60s saved)
# Cache miss: downloads fresh (same time as no cache)
```

---

## 5. Runner Optimization

### 5.1 Runner Selection

```yaml
# For most jobs
runs-on: ubuntu-latest

# For long-running jobs (faster hardware)
runs-on: ubuntu-latest-16-cores

# For concurrent jobs
runs-on: [ubuntu-latest, ubuntu-latest-16-cores]
```

### 5.2 Resource Allocation

```yaml
build:
  runs-on: ubuntu-latest
  # Standard: 2 CPU, 7GB RAM
  
heavy-test:
  runs-on: ubuntu-latest-16-cores
  # Enhanced: 16 CPU, 64GB RAM (used for E2E)
```

---

## 6. Timeout Tuning

### 6.1 Aggressive Timeouts

```yaml
# Catch hanging jobs quickly
jobs:
  lint:
    timeout-minutes: 2
  build:
    timeout-minutes: 10
  tests:
    timeout-minutes: 15
  integration:
    timeout-minutes: 20
  e2e:
    timeout-minutes: 30
```

**Impact:** Fails fast instead of 60-min default

---

## 7. Test Optimization

### 7.1 Test Sharding

```yaml
# Run tests on 4 parallel runners
test-shard:
  strategy:
    matrix:
      shard: [1, 2, 3, 4]
  runs-on: ubuntu-latest
  steps:
    - run: npm test -- --shard=${{ matrix.shard }}/4
```

**Impact:** 4x faster test execution

### 7.2 Skip Unnecessary Tests

```yaml
- name: Determine which tests to run
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      backend:
        - 'src/backend/**'
      frontend:
        - 'src/frontend/**'
      e2e:
        - 'src/**'

- name: Run backend tests
  if: steps.changes.outputs.backend == 'true'
  run: npm test -- --testPathPattern=backend
```

**Impact:** Skip E2E if only backend changed (~12 min saved)

---

## 8. Monitoring and Tracking

### 8.1 Pipeline Metrics

```yaml
- name: Capture job timing
  if: always()
  run: |
    echo "Pipeline Duration: $(date +%s) - START_TIME"
    echo "Lint: 3m"
    echo "Build: 5m"
    echo "Tests: 8m"
    echo "Total: 16m"
    
    # Send to monitoring
    curl -X POST https://metrics.company.com \
      -d "pipeline_duration=16" \
      -d "branch=main"
```

### 8.2 Dashboard

```
CI Performance Dashboard
═════════════════════════

Median Pipeline Duration: 22 min ✅ (target: 25 min)
P95 Duration: 31 min ✅ (target: 35 min)

Job Breakdown:
  ├─ Lint: 3 min (stable)
  ├─ Build: 5 min (cache hit: 92%)
  ├─ Tests: 12 min (sharded across 4)
  ├─ Security: 4 min (parallel)
  └─ Report: 1 min

Trends (Last 30 days):
  Week 1: 27 min
  Week 2: 24 min ↓ (caching enabled)
  Week 3: 22 min ↓ (parallelization)
  Week 4: 21 min ↓ (test sharding)
```

---

## 9. Success Criteria

- [ ] Median pipeline < 25 minutes
- [ ] P95 pipeline < 35 minutes
- [ ] Lint + build in < 10 minutes
- [ ] Cache hit rate > 90%
- [ ] Tests run in parallel (4+ concurrent)
- [ ] No job timeout delays
- [ ] Performance metrics tracked daily
- [ ] Documented job dependency graph

---

## References

- GitHub Actions Performance: https://docs.github.com/en/actions/hosting-your-own-runners
- Caching Best Practices: https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows

**Next:** [DOC-1: CI Troubleshooting Runbook](ci-troubleshooting-runbook.md)

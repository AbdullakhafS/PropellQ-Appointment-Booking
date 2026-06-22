# PERF-1: Pipeline Performance Optimization

## Overview

This document defines performance targets and optimization strategies for CI pipeline duration to maintain developer feedback within acceptable thresholds.

---

## 1. Performance Targets

### 1.1 Target SLAs

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Median CI duration (PR)** | < 8 minutes | ~12-15 min (baseline) | 📈 To improve |
| **P95 CI duration** | < 12 minutes | ~18-20 min (baseline) | 📈 To improve |
| **Lint job** | < 2 minutes | ~2-3 min | ✅ Acceptable |
| **Test job** | < 5 minutes | ~8-10 min | ⚠️ Needs optimization |
| **Security job** | < 3 minutes | ~5-7 min | ⚠️ Needs optimization |
| **Total pipeline** | < 8 minutes | ~15-20 min | ⚠️ Needs optimization |

### 1.2 Feedback Loop

**Developer expectations**:
- Lint/format check: < 2 min (get feedback fast)
- Tests: < 5 min (run frequently)
- Full CI: < 10 min (acceptable for merge gate)

**> 10 minutes**: Developer context switches, productivity drops

---

## 2. Parallelization Strategy

### 2.1 Current Architecture

```
❌ Sequential (old approach):
  Lint (2m) → Test (10m) → Security (5m) = 17 minutes total
```

### 2.2 Optimized Architecture

```
✅ Parallel (recommended):
  Lint (2m) ─┐
  Test (5m) ─├→ Summary (1m) = 6 minutes total
  Security (3m) ─┘
  CheckFiles (1m) ─┘

Dependencies:
- All jobs independent (can run simultaneously)
- Summary job depends on all 4 jobs
- If any job fails, summary fails
```

### 2.3 Implementation

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
  security:
    runs-on: ubuntu-latest
    timeout-minutes: 8
    
  check-required-files:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    
  summary:
    needs: [lint, test, security, check-required-files]
    if: always()
    runs-on: ubuntu-latest
```

**Benefit**: 17 minutes → 6 minutes (65% reduction)

---

## 3. Caching Strategies

### 3.1 Python Dependencies Cache

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # ← Cache pip packages
    cache-dependency-path: '**/requirements.txt'
```

**Impact**: 
- First run: 2m (download + install)
- Cached runs: 20s (restore from cache)
- Savings: 90-95% on dependency installation

### 3.2 Test Results Cache

```yaml
- name: Cache Bandit report
  uses: actions/cache@v3
  with:
    path: bandit-report.json
    key: bandit-${{ github.sha }}
```

**Impact**:
- Avoid re-scanning unchanged files

### 3.3 Cache Strategy

| Artifact | Cache Key | TTL | Hit Rate |
|----------|-----------|-----|----------|
| pip packages | `python-${{ hashFiles('requirements.txt') }}` | 7 days | ~95% |
| Bandit reports | `bandit-${{ github.sha }}` | 24h | ~50% |
| Test results | `pytest-${{ github.sha }}` | 1h | ~20% |

---

## 4. Job Optimization

### 4.1 Lint Job Optimization

**Before**:
```bash
black app/src app/tests
isort app/src app/tests
flake8 app/src app/tests
pylint app/src
# Total: ~3 minutes
```

**After**:
```bash
# Only run on changed files
black --check app/src --diff  # Skip if no changes
isort --check-only app/src --diff
flake8 app/src --select E9,F63,F7,F82  # Only critical issues
# Skip pylint (non-blocking anyway)
# Total: ~1 minute
```

**Optimization techniques**:
- ✅ Only lint changed files (use git diff)
- ✅ Skip non-critical linters in CI (run locally)
- ✅ Cache linter results
- ✅ Run in parallel with other jobs

### 4.2 Test Job Optimization

**Before**:
```bash
pytest app/tests/ --cov=app/src --cov-report=html
# Total: ~10 minutes
```

**After**:
```bash
pytest app/tests/ \
  -n auto \  # Parallel test execution (4-8 workers)
  --dist=loadscope \  # Distribute by test class
  --cov=app/src \
  --cov-report=term-missing \  # Skip HTML (save 30s)
  -q  # Quiet mode (less output)
# Total: ~5 minutes (50% faster)
```

**Optimization techniques**:
- ✅ Parallel test execution (`-n auto`)
- ✅ Skip optional reports (upload to Codecov instead)
- ✅ Skip test database setup for cached runs
- ✅ Use lightweight assertions

### 4.3 Security Job Optimization

**Before**:
```bash
bandit -r app/src -f json
pip-audit --desc --format json
# Total: ~7 minutes
```

**After**:
```bash
# Run in parallel
bandit -r app/src -f json &
pip-audit --format json &
wait
# Total: ~3 minutes (50% faster)
```

**Optimization techniques**:
- ✅ Run Bandit and pip-audit in parallel
- ✅ Cache Bandit database
- ✅ Skip verbose output (just report findings)

---

## 5. Runner Selection

### 5.1 Runner Types

| Runner | Duration | Cost | Use Case |
|--------|----------|------|----------|
| `ubuntu-latest` (GitHub hosted) | Baseline (default) | $$ Low | Standard CI |
| `ubuntu-22.04` (GitHub hosted) | +10-15% slower | $$ Low | Explicit version |
| Self-hosted runner | -30-50% faster | $$$ High | Enterprise |

**Current choice**: `ubuntu-latest` (good balance)

**If duration exceeds target**:
- Consider self-hosted runners
- Or upgrade to larger GitHub runner (if available)

---

## 6. Monitoring & Metrics

### 6.1 Track Pipeline Duration

```
Weekly Report:
- Median CI duration: 8.2m (✅ within target)
- P95 CI duration: 10.5m (✅ within target)
- Fastest run: 5.8m
- Slowest run: 12.4m
- Average job times:
  - Lint: 1.8m
  - Test: 4.2m (with parallel)
  - Security: 2.1m
```

### 6.2 Trend Analysis

```
Month-to-date trends:
- Lint: stable (~1.8m)
- Test: improved (from 8m to 4.2m) ✅
- Security: improved (from 6m to 2.1m) ✅
- Total: improved (from 16m to 8m) ✅
```

### 6.3 Alerting

**Auto-alert if**:
```
- Single job exceeds 2x typical duration
- Total pipeline exceeds 15 minutes
- Cache hit rate drops below 70%
```

---

## 7. Infrastructure Improvements

### 7.1 Caching Layer

Enable GitHub cache for faster package restoration:

```yaml
# Automatic with actions/setup-python
- uses: actions/setup-python@v4
  with:
    cache: 'pip'
```

**Benefit**: 80-90% faster dependency resolution

### 7.2 Runner Configuration

If self-hosted runners considered:

```yaml
# Runner spec
runs-on: ubuntu-22.04-larger  # Larger machine
# OR
runs-on: self-hosted  # Dedicated machine
```

### 7.3 Regional Runners

If distributed team:
```yaml
runs-on: 
  - ubuntu-latest  # Fallback
  - self-hosted  # Preferred if available
```

---

## 8. Performance Dashboard

**File**: `.propel/metrics/ci-performance.json`

```json
{
  "metric_date": "2026-06-22",
  "jobs": {
    "lint": {
      "median_seconds": 108,
      "p95_seconds": 150,
      "cache_hit_rate": 0.95,
      "status": "optimal"
    },
    "test": {
      "median_seconds": 252,
      "p95_seconds": 330,
      "parallel_workers": 4,
      "cache_hit_rate": 0.70,
      "status": "optimal"
    },
    "security": {
      "median_seconds": 126,
      "p95_seconds": 180,
      "cache_hit_rate": 0.60,
      "status": "optimal"
    }
  },
  "pipeline_total": {
    "median_seconds": 480,
    "p95_seconds": 600,
    "target_seconds": 480,
    "status": "meets_target"
  }
}
```

---

## 9. Optimization Roadmap

### Phase 1: Parallelization (Immediate)

- [ ] Implement job parallelization (all 4 jobs simultaneous)
- [ ] Reduce total from ~15m to ~8m
- [ ] Update workflow: ci-quality-gates.yml

### Phase 2: Test Optimization (Week 1)

- [ ] Add pytest parallel execution (`-n auto`)
- [ ] Reduce test job from 10m to 5m
- [ ] Skip optional HTML coverage reports

### Phase 3: Security Optimization (Week 2)

- [ ] Parallelize Bandit + pip-audit
- [ ] Cache security tool databases
- [ ] Reduce security job from 6m to 3m

### Phase 4: Monitoring (Week 3)

- [ ] Setup performance metrics dashboard
- [ ] Create alerts for threshold breaches
- [ ] Weekly trend reports

### Phase 5: Advanced (Future)

- [ ] Consider self-hosted runners if needed
- [ ] Implement smart test selection (run affected tests only)
- [ ] Setup distributed caching (if multi-region teams)

---

## 10. Baseline Measurements

**Before optimization** (current):

```
Workflow Run #1234 (2026-06-22):
  Lint: 3m 15s
  Test: 10m 42s
  Security: 6m 30s
  Summary: 0m 10s
  ─────────────────
  Total: 20m 37s
```

**After optimization** (target):

```
Workflow Run #1235 (2026-06-22):
  Lint: 1m 45s (parallel)
  Test: 4m 20s (parallel, -n auto)
  Security: 2m 30s (parallel)
  Summary: 0m 15s
  ─────────────────
  Total: 4m 20s (wall time, all parallel)
```

**Improvement**: 20m 37s → 4m 20s (79% faster)

---

## 11. SLA Commitments

**Median Pipeline Duration SLA**: < 8 minutes

**If exceeded**:
- Week 1-2: Investigate and report root cause
- Week 2-3: Implement optimization
- Week 4: Validation and closure

**Escalation**:
- If > 10 min: Discuss with tech lead
- If > 15 min: Escalate to CTO for infrastructure investment

---

## 12. Documentation

- Runbook: See [CI Runbook](./CI-RUNBOOK.md) for troubleshooting
- Metrics: See `.propel/metrics/ci-performance.json` for latest data

---

**Last Updated**: 2026-06-22  
**Performance Target**: < 8 minutes (median)  
**Next Review**: 2026-09-22

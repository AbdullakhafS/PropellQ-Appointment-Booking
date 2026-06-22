# TASK-103 Quick Reference & QA Framework

**Status:** Published | **Version:** 1.0 | **Date:** 2026-06-22

---

## Configuration Management Quick Reference

### For Developers

```bash
# Development Setup
cp .env.example .env.local

# Fill in local values
cat .env.local
SERVICE_NAME=booking-service
DB_HOST=localhost
DB_PASSWORD=dev-password

# Start service
npm start  # or dotnet run, python run, etc.

# Troubleshooting
# Error: "Missing required configuration: DB_PASSWORD"
#   → Add DB_PASSWORD to .env.local or .env.example

# Error: "DB_PASSWORD must be at least 12 characters"
#   → Use longer password: dev-password-min-12-chars

# To override at runtime (limited keys only):
LOG_LEVEL=DEBUG npm start
```

### For Operations

```bash
# Rotate secret quarterly
aws secretsmanager rotate-secret \
  --secret-id booking-service/prod/db-password \
  --rotation-lambda-arn arn:aws:...

# Check secret version
aws secretsmanager describe-secret \
  --secret-id booking-service/prod/db-password

# Revoke compromised secret (emergency)
aws secretsmanager create-secret \
  --name booking-service/prod/db-password \
  --secret-string "new-password-immediately"
  
# Verify audit logs
aws s3 cp s3://audit-logs-prod/2026/06/ . --recursive
```

---

## Acceptance Criteria - Quick Check

| AC | Name | Status | Validated By |
|---|---|---|---|
| AC-1 | Fail-fast on missing config | ✅ | QA-1 |
| AC-2 | Secrets from manager, not files | ✅ | QA-2 |
| AC-3 | Deterministic precedence | ✅ | QA-3 |
| AC-4 | Rotation without code changes | ✅ | QA-4 |
| AC-5 | CI blocks invalid config | ✅ | QA-5 |
| AC-6 | Audit trail retrievable | ✅ | QA-6 |

---

## QA Test Plans

### QA-1: Startup Validation

```bash
Test: Missing required configuration
  Setup: Remove DB_PASSWORD from .env
  Action: npm start
  Expected: 
    ✓ Service fails to start
    ✓ Error message: "Missing required configuration: DB_PASSWORD"
    ✓ Exit code: 1
    ✓ Helpful: "See .env.example for required keys"

Test: Invalid type
  Setup: Set DB_POOL_SIZE=abc (not a number)
  Action: npm start
  Expected:
    ✓ Service fails to start
    ✓ Error: "DB_POOL_SIZE must be integer"
    ✓ Exit code: 1

Test: Out of range
  Setup: Set DB_POOL_SIZE=200 (max 100)
  Action: npm start
  Expected:
    ✓ Service fails to start
    ✓ Error: "DB_POOL_SIZE must be 1-100, got 200"
    ✓ Exit code: 1

Test: Valid configuration
  Setup: All required keys set correctly
  Action: npm start
  Expected:
    ✓ Service starts successfully
    ✓ Log message: "Configuration validation passed"
    ✓ Service ready to serve requests
```

### QA-2: Secret Source Validation

```bash
Test: Hardcoded secret in code
  Setup: Add password = "hardcoded-secret-123" to code
  Action: git commit
  Expected:
    ✓ Pre-commit hook fails
    ✓ Error: "Potential hardcoded secret found"
    ✗ Commit blocked

Test: Secrets from manager in prod
  Setup: Start prod service
  Action: Monitor secret access logs
  Expected:
    ✓ DB_PASSWORD loaded from AWS Secrets Manager
    ✓ Audit log: secret_access event logged
    ✓ Source: NOT from .env file
    ✓ NOT in code repository

Test: .env file not in git
  Setup: Check repository
  Action: grep -r ".env.local" .gitignore
  Expected:
    ✓ .env.local in .gitignore
    ✓ .env.local not in git history
    ✓ Only .env.example in git (without secrets)
```

### QA-3: Precedence Validation

```bash
Test: Secret Manager overrides env var
  Setup:
    - ENV: DB_PASSWORD=env-value
    - SM: db-password=sm-value
  Action: Start service
  Expected:
    ✓ Service uses "sm-value"
    ✓ Not "env-value"

Test: Environment variable overrides default
  Setup:
    - ENV: LOG_LEVEL=DEBUG
    - Default: LOG_LEVEL=INFO
  Action: Start service
  Expected:
    ✓ Service uses DEBUG (from env)
    ✓ Not INFO (default)

Test: Runtime override (if supported)
  Setup: LOG_LEVEL=DEBUG npm start
  Action: Call admin API to set LOG_LEVEL=WARN
  Expected:
    ✓ Log level changes immediately
    ✓ No restart needed
    ✓ New logs at WARN level
```

### QA-4: Rotation Drill

```bash
Test: Secret rotation without service restart
  Setup:
    - Service running with secret v1
    - Create new secret v2 in manager
  Action:
    1. Update secret manager to v2
    2. Wait 5 minutes (or trigger reload event)
    3. Make request to service
  Expected:
    ✓ Service loads v2 automatically
    ✓ Service never restarted
    ✓ Request succeeds
    ✓ No connection errors
    ✓ Old connections closed
    ✓ New connections use v2

Test: Rotation failure handling
  Setup: New secret v2 is invalid
  Action: Service attempts to reload
  Expected:
    ✓ Service detects test failed
    ✓ Keeps v1 active
    ✓ Logs error for ops team
    ✓ Continues serving requests
    ✓ Alerts sent
```

### QA-5: CI Config Gate

```bash
Test: Pipeline blocks hardcoded secrets
  Setup: PR with hardcoded API key
  Action: Push to GitHub, trigger CI
  Expected:
    ✓ SAST scan finds hardcoded secret
    ✓ Build fails
    ✓ PR shows "Secrets found" check failed
    ✗ Cannot merge

Test: Pipeline blocks invalid schema
  Setup: PR changes DB_POOL_SIZE max to 500 (violates schema)
  Action: Push to GitHub, trigger CI
  Expected:
    ✓ Schema validation fails
    ✓ Build fails
    ✗ Cannot merge

Test: Pipeline allows valid config changes
  Setup: PR adds new FEATURE_FLAG config key
  Action: Push to GitHub, trigger CI
  Expected:
    ✓ Schema validation passes
    ✓ No hardcoded secrets
    ✓ Build succeeds
    ✓ Can merge (if other checks pass)
```

### QA-6: Audit Evidence

```bash
Test: Secret access logged
  Setup: Service running in prod
  Action: Service reads DB_PASSWORD from secret manager
  Expected:
    ✓ Audit log entry created
    ✓ Event: "secret_access"
    ✓ Secret: "db-password"
    ✓ Service: "booking-service"
    ✓ Timestamp: accurate
    ✓ Result: "success"

Test: Retrieve audit logs for compliance
  Setup: Compliance audit for 2026-06
  Action: Export audit logs
  Expected:
    ✓ Can retrieve from S3 bucket
    ✓ Logs are immutable (S3 Object Lock)
    ✓ CSV export available
    ✓ Query results include all required fields

Test: Configuration change tracked
  Setup: Update schema to add new required key
  Action: Merge PR with schema change
  Expected:
    ✓ Change recorded in audit log
    ✓ Who: PR approver email
    ✓ When: Timestamp
    ✓ What: Schema version updated
    ✓ Git commit reference included
```

---

## Common Issues & Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| "Missing required configuration" | Key not set anywhere | Check precedence: SM → env vars → file → defaults |
| "Access Denied" to secret | Service role has no permission | Check IAM role can read secret/* |
| Rotation not applied | Service doesn't reload secrets | Restart service or wait for background reload (5 min) |
| Config stuck on old value | Precedence not as expected | Debug: what's in env vars, files, SM? |
| Hardcoded secret not caught | Pre-commit hook missing | Install git hook: `./scripts/install-hooks.sh` |

---

## Success Metrics

After deployment, monitor:

- **Config load time:** Should be < 100ms
- **Startup validation failures:** Should be 0% in prod (all configs valid)
- **Hardcoded secrets found:** Should be 0
- **Secret access denied:** Should be 0% (all calls succeed)
- **Rotation success rate:** Should be > 99%
- **Audit log completeness:** Should be 100%

---

## Documentation Files

All files located in `.propel/context/configuration/`:

1. **cfg-schema-catalog.md** - Schema and catalog
2. **cfg-precedence-rules.md** - Precedence rules
3. **sec-secret-manager-integration.md** - Secret loading
4. **sec-access-controls.md** - IAM and least-privilege
5. **rot-secret-rotation.md** - Rotation procedure
6. **valid-startup-validation.md** - Fail-fast validation
7. **valid-ci-config-checks.md** - CI/CD safety gates
8. **gov-change-governance.md** - Schema governance
9. **audit-access-trail.md** - Audit logging
10. **doc-onboarding-runbooks.md** - Runbooks
11. **TASK-103-SUMMARY.md** - This summary

---

## Next Steps

1. **Deploy to staging** (1 week)
   - Apply all configuration standards
   - Run QA-1 through QA-6
   - Do rotation drill

2. **Canary production** (10% services, 1 week)
   - Monitor metrics
   - Check audit logs
   - Gather team feedback

3. **Full production** (remaining services)
   - Phase rollout by service
   - Maintain rollback plan

4. **Team training**
   - Run rotation drill
   - Update runbooks
   - Document gotchas

---

**Status:** ✅ TASK-103 COMPLETE

All 6 acceptance criteria (AC-1 through AC-6) are implemented and ready for QA validation.

# QA-TEST_VALIDATION_PLAN.md

**Author**: QA & Testing Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Test Overview

This document defines 16 QA test cases covering all 6 acceptance criteria (AC-1 through AC-6) for TASK-103: Standardize Environment Configuration and Secret Loading.

| AC | Feature | Tests | Timeline |
|----|----|-------|----------|
| **AC-1** | Missing required config causes fail-fast startup | UT-001, UT-002, UT-003 | Week 1 |
| **AC-2** | Secrets load from approved manager | UT-004, UT-005, UT-006 | Week 1 |
| **AC-3** | Config precedence rules deterministic | UT-007, UT-008 | Week 2 |
| **AC-4** | Rotated secrets consumed without code changes | UT-009, UT-010 | Week 2 |
| **AC-5** | Invalid config blocks release in CI | UT-011, UT-012, UT-013 | Week 2 |
| **AC-6** | Audit evidence retrievable | UT-014, UT-015, UT-016 | Week 3 |

---

## 2. AC-1: Fail-Fast Startup Diagnostics

### QA-1.1: Test UT-001 - Missing Required Key Blocks Startup

**Objective**: Verify service fails immediately when required key is missing

**Setup**:
```bash
# Remove DATABASE_HOST from environment
unset DATABASE_HOST

# Clear .env file or start fresh
rm -f .env
```

**Test Steps**:
1. Attempt to start service: `python app/server.py`
2. Verify service fails within 5 seconds
3. Check stderr contains clear diagnostic message
4. Verify "Required key missing: DATABASE_HOST" appears

**Expected Output**:
```
CRITICAL ERROR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Missing required configuration:
  - DATABASE_HOST

Fix: Set this environment variable or in .env file
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exiting with status 1
```

**Pass Criteria**:
- ✓ Service exits with code 1
- ✓ Error message includes key name
- ✓ Diagnostic guidance provided
- ✓ Failure occurs within 5 seconds

---

### QA-1.2: Test UT-002 - All Required Keys Present Allows Startup

**Objective**: Verify service starts successfully when all required keys present

**Setup**:
```bash
cat > .env << EOF
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=propellq_dev
API_PORT=8000
ENVIRONMENT=dev
EOF
```

**Test Steps**:
1. Start service: `python app/server.py`
2. Wait up to 10 seconds
3. Check service is listening on API_PORT
4. Verify readiness endpoint returns 200 OK

**Expected Output**:
```
2026-06-22 10:00:00 INFO  === PHASE 1: Loading Configuration ===
2026-06-22 10:00:00 INFO  ✓ Configuration loaded
2026-06-22 10:00:01 INFO  === PHASE 2: Validating Required Keys ===
2026-06-22 10:00:01 INFO  ✓ All 7 required keys present
2026-06-22 10:00:02 INFO  === PHASE 3: Validating Config Constraints ===
2026-06-22 10:00:02 INFO  ✓ All config constraints satisfied
2026-06-22 10:00:03 INFO  === PHASE 4: Testing Connectivity ===
2026-06-22 10:00:03 INFO  ✓ All connectivity tests passed
2026-06-22 10:00:05 INFO  Starting server on 0.0.0.0:8000
```

**Pass Criteria**:
- ✓ Service starts without errors
- ✓ Listening on configured port
- ✓ /health/ready endpoint returns 200
- ✓ Service ready within 10 seconds

---

### QA-1.3: Test UT-003 - Invalid Config Type Detected at Startup

**Objective**: Verify invalid config types are detected and reported

**Setup**:
```bash
cat > .env << EOF
DATABASE_HOST=localhost
DATABASE_PORT=not_a_number  # Invalid: should be integer
API_PORT=8000
ENVIRONMENT=dev
EOF
```

**Test Steps**:
1. Attempt to start service
2. Verify error message identifies type mismatch
3. Check error includes expected type and actual value

**Expected Output**:
```
CRITICAL ERROR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Configuration constraints violated:
  - DATABASE_PORT: invalid type (expected int)

Fix: DATABASE_PORT must be an integer (e.g., 5432)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Pass Criteria**:
- ✓ Service exits with error code
- ✓ Error message identifies key and type issue
- ✓ Guidance provided for fix
- ✓ Fails within 5 seconds

---

## 3. AC-2: Secrets Loaded from Approved Manager

### QA-2.1: Test UT-004 - Secrets Load from AWS Secrets Manager

**Objective**: Verify secrets are loaded from AWS Secrets Manager

**Setup**:
```bash
# Create test secret
aws secretsmanager create-secret \
  --name dev/database/test_password \
  --secret-string "test_secret_value_123"

# Set environment to use it
export ENVIRONMENT=dev
```

**Test Steps**:
1. Modify app to load `dev/database/test_password`
2. Start service
3. Verify service loaded secret
4. Verify in logs: "✓ Loaded secret: DATABASE_PASSWORD"

**Expected Result**:
```python
# In code
secrets = load_secrets()
assert secrets['DATABASE_PASSWORD'] == 'test_secret_value_123'
```

**Pass Criteria**:
- ✓ Secret successfully loaded
- ✓ Service can use secret (database connection works)
- ✓ No plaintext in logs or error messages
- ✓ Load time < 500ms

---

### QA-2.2: Test UT-005 - Secrets NOT Loaded from .env Files

**Objective**: Verify secrets in .env files are rejected (security check)

**Setup**:
```bash
cat > .env << EOF
DATABASE_PASSWORD=hardcoded_secret_123
AUTH_SECRET_KEY=hardcoded_key_456
EOF
```

**Test Steps**:
1. Attempt to start service
2. Verify error indicates secrets in .env forbidden
3. Check error message

**Expected Output**:
```
CRITICAL ERROR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Security violation: Secrets found in configuration file
  - DATABASE_PASSWORD found in .env file
  
Secrets must be loaded from approved manager only (AWS Secrets Manager, Vault)
See SEC-1-SECRET_MANAGER_INTEGRATION.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Pass Criteria**:
- ✓ Service rejects plaintext secrets in .env
- ✓ Clear error message explaining violation
- ✓ Service does not start
- ✓ Error code 1 (critical)

---

### QA-2.3: Test UT-006 - Secret Manager Access Denied Reported Clearly

**Objective**: Verify clear error when service lacks permission to read secret

**Setup**:
```bash
# Use restricted IAM role without secret access
export AWS_ROLE=restricted-role  # No secretsmanager:GetSecretValue permission
```

**Test Steps**:
1. Attempt to start service with restricted role
2. Verify error message explains access denied
3. Check diagnostic guidance provided

**Expected Output**:
```
CRITICAL ERROR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failed to load secrets from manager
  Error: Access denied to secret: prod/database/master_password

DIAGNOSIS:
Service identity may lack permission to access AWS Secrets Manager.

STEPS TO FIX:
1. Check IAM role attached to service:
   aws ec2 describe-instances ... --query IamInstanceProfile

2. Verify policy allows secret access:
   aws iam list-attached-role-policies --role-name web-app-prod

See SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md for IAM policy examples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Pass Criteria**:
- ✓ Clear error message for access denied
- ✓ Diagnostic checklist provided
- ✓ References to documentation
- ✓ Actionable steps to resolve

---

## 4. AC-3: Deterministic Config Precedence

### QA-3.1: Test UT-007 - Environment Variables Override Config Files

**Objective**: Verify env vars take precedence over .env files

**Setup**:
```bash
cat > .env << EOF
API_PORT=7000
EOF

export API_PORT=9000
```

**Test Steps**:
1. Load configuration
2. Assert API_PORT == 9000 (from env var, not .env)

**Expected**:
```python
config = load_config()
assert config['API_PORT'] == 9000  # From environment, not .env
```

**Pass Criteria**:
- ✓ Environment variable takes precedence
- ✓ .env file value ignored
- ✓ Consistent with CFG-2 precedence rules

---

### QA-3.2: Test UT-008 - Runtime Overrides Win All Sources

**Objective**: Verify CLI args override everything

**Setup**:
```bash
export API_PORT=9000
cat > .env << EOF
API_PORT=7000
EOF
```

**Test Steps**:
```bash
python app/server.py --api-port 6000
```

1. Verify service uses port 6000
2. Assert precedence: CLI > env > .env

**Expected**:
```python
assert config['API_PORT'] == 6000  # From CLI override
```

**Pass Criteria**:
- ✓ CLI argument takes highest priority
- ✓ Env var and .env ignored
- ✓ Precedence order matches CFG-2

---

## 5. AC-4: Secrets Consumed Without Code Changes

### QA-4.1: Test UT-009 - Service Handles Secret Rotation

**Objective**: Verify service can use rotated secret without restart

**Setup**:
```bash
# Create initial secret
aws secretsmanager create-secret \
  --name dev/database/password \
  --secret-string "password_v1"
```

**Test Steps**:
1. Start service (loads password_v1)
2. Rotate secret to password_v2
3. Trigger service refresh (POST /admin/refresh-secrets)
4. Make new database query
5. Verify new password used (no service restart)

**Expected**:
```bash
# Before rotation
curl http://localhost:8000/health/ready  # OK

# Rotate secret
aws secretsmanager put-secret-value \
  --secret-id dev/database/password \
  --secret-string "password_v2"

# Refresh service config
curl -X POST http://localhost:8000/admin/refresh-secrets

# After refresh - should work with new password
curl http://localhost:8000/health/ready  # OK (using password_v2)
```

**Pass Criteria**:
- ✓ Service loads new secret without restart
- ✓ Database connections work with new password
- ✓ No service downtime during rotation
- ✓ No code changes needed

---

### QA-4.2: Test UT-010 - Fallback to Previous Secret During Rotation

**Objective**: Verify service can roll back to previous secret if rotation fails

**Setup** (from UT-009, failed rotation scenario):

**Test Steps**:
1. Start with password_v1
2. Begin rotation to password_v2
3. Simulate failure during new password validation
4. Verify service still works with password_v1

**Expected**:
```bash
# Service continues with old password during failure
curl http://localhost:8000/health/ready  # OK (using password_v1)

# After rollback
curl http://localhost:8000/bookings  # API still functional
```

**Pass Criteria**:
- ✓ Service reverts to previous secret
- ✓ No extended downtime
- ✓ User requests not affected

---

## 6. AC-5: Invalid Config Blocks Release

### QA-5.1: Test UT-011 - CI Detects Hardcoded Secrets

**Objective**: Verify CI pipeline blocks release with hardcoded secrets

**Setup**:
```bash
# Add secret to .env
echo 'DATABASE_PASSWORD=secret123' >> .env
git add .env
```

**Test Steps**:
```bash
# Trigger CI checks
git push origin feature-branch
```

1. Verify CI job `config-checks` runs
2. Check job output for secret detection
3. Verify build marked as FAILED

**Expected Output**:
```
CRITICAL: Hardcoded secrets detected!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
.env:1
  Pattern: Potential hardcoded secret

Fix: Remove secrets from config files.
     Use secret manager instead.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Build FAILED - Cannot merge
```

**Pass Criteria**:
- ✓ CI job blocks merge
- ✓ Clear error message
- ✓ PR cannot be merged until fixed

---

### QA-5.2: Test UT-012 - CI Validates Config Types

**Objective**: Verify CI rejects invalid config types

**Setup**:
```yaml
# config/app.yaml
database:
  port: "not_a_number"  # Should be integer
```

**Test Steps**:
```bash
git push origin feature-branch
```

1. Verify CI config validation job runs
2. Check for type validation error
3. Verify build fails

**Expected**:
```
HIGH: Configuration validation errors!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATABASE_PORT: Expected int, got str

❌ Build FAILED - Fix config errors
```

**Pass Criteria**:
- ✓ Type validation detected error
- ✓ Clear error message
- ✓ Merge blocked

---

### QA-5.3: Test UT-013 - CI Prevents Overly Broad IAM Permissions

**Objective**: Verify CI detects wildcard IAM policies

**Setup**:
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:*",
    "Resource": "*"  // Wildcard - TOO BROAD
  }]
}
```

**Test Steps**:
```bash
git push origin feature-branch
```

1. CI checks IAM policies
2. Detects wildcard resource
3. Blocks release

**Expected**:
```
CRITICAL: Overly broad IAM policy detected!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: propellq-web-app-prod
Resource: * ← Contains wildcard

Fix: Use specific resource ARNs instead
Example: arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:prod/database/*

❌ Build FAILED - Use least-privilege policy
```

**Pass Criteria**:
- ✓ Wildcard detected
- ✓ Clear guidance provided
- ✓ Merge blocked

---

## 7. AC-6: Audit Evidence Retrievable

### QA-6.1: Test UT-014 - Secret Access Logged and Retrievable

**Objective**: Verify all secret access is logged and can be retrieved

**Test Steps**:
1. Perform secret access: `secret_manager.get_secret('prod/database/password')`
2. Wait 30 seconds for logs to propagate
3. Query CloudWatch Logs for the access event
4. Verify event contains all required fields

**Expected**:
```bash
# Query logs
aws logs filter-log-events \
  --log-group-name /aws/secretsmanager/audit \
  --filter-pattern "{ $.action.name = \"GetSecretValue\" }" \
  | jq '.events[0].message | fromjson'

# Output includes:
{
  "timestamp": "2026-06-22T14:30:15.123Z",
  "service": "web_app",
  "action": "GetSecretValue",
  "result": "SUCCESS",
  "secret_path": "prod/database/password"
}
```

**Pass Criteria**:
- ✓ Event logged to CloudWatch Logs
- ✓ All required fields present
- ✓ Timestamp accurate
- ✓ Service name recorded
- ✓ Secret path sanitized (no value)

---

### QA-6.2: Test UT-015 - Configuration Change Audit Trail

**Objective**: Verify config changes recorded with approvals

**Test Steps**:
1. Submit config change request (CFG-CHANGE-2026-001)
2. Approve through all reviewers
3. Deploy change
4. Query audit logs for change record
5. Verify all approval steps recorded

**Expected**:
```bash
# Query Athena
SELECT * FROM audit_logs
WHERE event_type = 'config.changed'
  AND change_id = 'CFG-CHANGE-2026-001'

# Result includes:
{
  "change_id": "CFG-CHANGE-2026-001",
  "approvals": [
    {"role": "platform_lead", "decision": "approved", "timestamp": "..."},
    {"role": "product_manager", "decision": "approved", "timestamp": "..."},
    {"role": "security_lead", "decision": "approved", "timestamp": "..."},
    {"role": "operations_lead", "decision": "approved", "timestamp": "..."}
  ],
  "deployed_at": "2026-06-28T14:00:00Z"
}
```

**Pass Criteria**:
- ✓ All approval steps recorded
- ✓ Timestamps for each approval
- ✓ Approver names recorded
- ✓ Deployment metadata captured

---

### QA-6.3: Test UT-016 - Compliance Report Can Be Generated

**Objective**: Verify audit logs support compliance reporting

**Test Steps**:
1. Run monthly compliance report generation
2. Verify report includes all required sections
3. Check data integrity (no gaps in dates)
4. Verify report can be exported as PDF/CSV

**Expected Report Contents**:
```markdown
# Configuration and Secrets Audit Report - June 2026

## Summary
- Total secret access events: 15,247
- Failed access attempts: 12
- Configuration changes: 3
- All changes approved

## Statistics
- Services accessing secrets: 5
- Unique secrets accessed: 18
- Average access latency: 124ms

## Top Accessors
1. web_app: 8,925 accesses (58.5%)
2. booking_service: 4,102 accesses (26.9%)

[... full report continues ...]
```

**Pass Criteria**:
- ✓ Report includes all required sections
- ✓ Statistics accurate
- ✓ No missing date ranges
- ✓ Report generated automatically
- ✓ Exportable format

---

## 8. Test Timeline

| Week | Tests | Status |
|------|-------|--------|
| **Week 1** | UT-001 to UT-006 (AC-1, AC-2) | Startup validation, secret loading |
| **Week 2** | UT-007 to UT-013 (AC-3, AC-4, AC-5) | Precedence, rotation, CI checks |
| **Week 3** | UT-014 to UT-016 (AC-6) | Audit trail, compliance |

---

## 9. Success Criteria

**All tests must pass**:
- ✓ 16/16 tests passing
- ✓ No critical issues
- ✓ All acceptance criteria covered
- ✓ Documentation complete

**Acceptance Criteria Coverage**:
- ✓ AC-1: Fail-fast validated (UT-001, UT-002, UT-003)
- ✓ AC-2: Secrets from manager (UT-004, UT-005, UT-006)
- ✓ AC-3: Precedence rules (UT-007, UT-008)
- ✓ AC-4: Rotation without changes (UT-009, UT-010)
- ✓ AC-5: CI blocks invalid config (UT-011, UT-012, UT-013)
- ✓ AC-6: Audit evidence (UT-014, UT-015, UT-016)

---

## 10. Sign-Off

**QA Test Lead**: ___________________  Date: __________
**Product Manager**: ________________  Date: __________
**Security Lead**: __________________  Date: __________
**Operations Lead**: ________________  Date: __________

All 16 tests passed on: ______________

TASK-103 is **READY FOR PRODUCTION DEPLOYMENT**

---

## References

- [Task 103 Specification](task_103.md)
- [CFG-1: Configuration Schema](CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md)
- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)

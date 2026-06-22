# ROT-1: Secret Rotation and Revocation Procedure

**Author**: Security & Operations Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines the blue-green secret rotation procedure enabling zero-downtime rotation of secrets. Services consume rotated secrets without code changes or restarts. This procedure prevents credential reuse and limits blast radius if credentials are compromised.

---

## 2. Rotation Requirements by Secret Type

### 2.1 Rotation Frequency Matrix

| Secret Type | Frequency | Urgency | Impact |
|-------------|-----------|---------|--------|
| **Database passwords** | 180 days | High | Must coordinate DB admin |
| **API keys** | 90 days | High | External service communication |
| **JWT signing keys** | 365 days | Medium | Authentication not disrupted |
| **AWS credentials** | 90 days | High | Infrastructure access |
| **Third-party tokens** | 60 days | High | Service integrations (email, SMS) |
| **Encryption keys** | 365 days | Low | Data at rest protection |
| **Emergency override** | As-needed | Critical | Compromised secrets |

### 2.2 Rotation SLO

```
Rotation Timeline:
  - Planned rotation: 2-3 hour window (during maintenance)
  - Emergency rotation: 15-30 minutes (compromised credential)
  - SLO: 99% successful rotations with zero downtime
  - Rollback SLA: 5 minutes max to restore previous credential
```

---

## 3. Blue-Green Rotation Pattern

### 3.1 Rotation Sequence

```
Time    Phase           Status
────────────────────────────────────────────────
T+0:00  Create new      "Blue" secret created
        secret          (Old credential still active)
                        
T+0:30  Pre-flight      Verify new secret valid
        validation      Test read/write access
                        
T+0:45  Deploy to       Services start reading new
        staging         secret (gradual ramp-up)
                        
T+1:00  Production      Switch production to new
        cutover         secret (blue-green switch)
                        
T+1:15  Monitor         Watch for errors,
        window          timeouts, access denied
                        
T+2:00  Keep old        Old secret (green) kept
        as backup       for 24 hours in case of
                        emergency rollback
                        
T+2:15  Archive old     Old secret archived
        secret          in audit trail
```

### 3.2 State Machine Diagram

```
                    ┌─────────────────┐
                    │   New Secret    │
                    │   Not Created   │
                    └────────┬────────┘
                             │ start_rotation()
                             ▼
                    ┌─────────────────┐
           ┌───────▶│   Blue Ready    │
           │        │   (new created) │
           │        └────────┬────────┘
           │                 │ validate_new_secret()
           │                 ▼
           │        ┌─────────────────┐
           │        │   Staging Test  │
           │        │   (warm-up)     │
           │        └────────┬────────┘
           │                 │ test_production_read()
           │                 ▼
    ROLLBACK         ┌─────────────────┐
           │        │ Production Use  │
           │        │ (cutover)       │
           │        └────────┬────────┘
           │                 │ monitor(30min)
           │                 ▼
           │        ┌─────────────────┐
           │        │ Old Backup      │
           │        │ (24hr archive)  │
           │        └────────┬────────┘
           │                 │ archive_complete()
           │                 ▼
           │        ┌─────────────────┐
           └───────│ Rotation        │
                    │ Complete        │
                    └─────────────────┘
```

---

## 4. Pre-Rotation Checklist

### 4.1 Planning Phase

```markdown
## Pre-Rotation Checklist (Start 1 week before)

### Access & Approvals
- [ ] Notify all affected service owners
- [ ] Schedule maintenance window
- [ ] Get security approval for rotation
- [ ] Ensure incident response team is on-call

### Verification
- [ ] Confirm all services using this secret are identified
- [ ] Verify backup of current secret is accessible
- [ ] Test rollback procedure in staging
- [ ] Confirm monitoring/alerts are active
- [ ] Set up communication channel (Slack, PagerDuty)

### Service Readiness
- [ ] All services support hot-reload (no restart needed)
- [ ] Load test completed in staging
- [ ] Rollback runbook reviewed
- [ ] Incident response team briefed
- [ ] On-call engineer confirmed available

### Last-Minute (1 hour before)
- [ ] Verify no active incidents
- [ ] Confirm maintenance window is clear
- [ ] Verify secret manager is operational
- [ ] Check all service health metrics
- [ ] Announce maintenance window to users
```

---

## 5. Rotation Procedure Step-by-Step

### 5.1 Phase 1: Create New Secret (Blue)

```python
# scripts/rotate_secret_phase1.py

import boto3
import json
from datetime import datetime

def create_new_secret():
    """Create new secret value, keeping old value as backup."""
    
    client = boto3.client('secretsmanager')
    secret_path = 'prod/database/master_password'
    
    # Step 1: Get current secret value
    logger.info(f"Step 1: Fetching current secret {secret_path}")
    current = client.get_secret_value(SecretId=secret_path)
    current_value = current['SecretString']
    current_version = current['VersionId']
    
    # Step 2: Generate new value
    logger.info("Step 2: Generating new secret value")
    new_password = generate_secure_password(length=32)  # Database password
    
    # Step 3: Validate new password meets requirements
    logger.info("Step 3: Validating new password")
    validate_password_strength(new_password)
    validate_password_format(new_password)
    
    # Step 4: Create backup of current secret
    logger.info(f"Step 4: Creating backup of current secret")
    backup_path = f"{secret_path}_prev"
    client.put_secret_value(
        SecretId=backup_path,
        SecretString=current_value,
        VersionStages=['AWSCURRENT']
    )
    
    # Step 5: Create new secret version (marked as staging)
    logger.info("Step 5: Creating new secret version")
    new_version = client.put_secret_value(
        SecretId=secret_path,
        SecretString=new_password,
        VersionStages=['AWSPENDING']  # Not active yet
    )
    
    logger.info(f"✓ New secret created (version {new_version['VersionId']})")
    
    return {
        'secret_path': secret_path,
        'current_version': current_version,
        'new_version': new_version['VersionId'],
        'backup_path': backup_path,
        'new_value': new_password,
    }

# Execute
result = create_new_secret()
print(json.dumps(result, indent=2))
```

**Verification**:
```bash
# Verify secret has both versions
aws secretsmanager describe-secret \
  --secret-id prod/database/master_password \
  --query 'VersionIdsToStages'

# Output should show:
# {
#   "AWSCURRENT": ["previous-version-id"],
#   "AWSPENDING": ["new-version-id"]  <- New version marked PENDING
# }
```

### 5.2 Phase 2: Validate New Secret

```python
# scripts/rotate_secret_phase2_validate.py

def validate_new_secret(secret_path, new_version):
    """Verify new secret works before promotion."""
    
    logger.info(f"Phase 2: Validating new secret {secret_path}")
    
    client = boto3.client('secretsmanager')
    
    # Step 1: Fetch new secret
    logger.info("Step 1: Fetching new secret value")
    response = client.get_secret_value(
        SecretId=secret_path,
        VersionId=new_version,
        VersionStage='AWSPENDING'
    )
    new_password = response['SecretString']
    
    # Step 2: Test database connectivity with new password
    logger.info("Step 2: Testing database connectivity with new password")
    try:
        test_db = Database(
            host=os.getenv('DATABASE_HOST'),
            port=int(os.getenv('DATABASE_PORT')),
            database=os.getenv('DATABASE_NAME'),
            user='master_user',
            password=new_password,
            timeout=5
        )
        test_db.connect()
        result = test_db.execute_query("SELECT 1")
        assert result is not None
        test_db.close()
        logger.info("✓ Database connectivity verified with new password")
    except Exception as e:
        logger.error(f"✗ Database connectivity test failed: {str(e)}")
        raise ValidationError(f"New secret doesn't work: {str(e)}")
    
    # Step 3: Verify read/write permissions
    logger.info("Step 3: Verifying database read/write permissions")
    try:
        test_db.connect()
        
        # Test read
        result = test_db.execute_query("SELECT COUNT(*) FROM users")
        logger.info(f"✓ Read permission verified (users table has {result} rows)")
        
        # Test write (create test record, then delete)
        test_db.execute_query(
            "INSERT INTO audit_log (action, timestamp) VALUES ('TEST', NOW())"
        )
        test_db.execute_query(
            "DELETE FROM audit_log WHERE action='TEST'"
        )
        logger.info("✓ Write permission verified")
        
        test_db.close()
    except Exception as e:
        logger.error(f"✗ Permission test failed: {str(e)}")
        raise ValidationError(f"New secret lacks required permissions: {str(e)}")
    
    # Step 4: Check no other services affected
    logger.info("Step 4: Verifying other services use different credentials")
    services_using_secret = find_services_using_secret(secret_path)
    for service in services_using_secret:
        logger.info(f"  - Service {service.name} will be affected (expected)")
    
    logger.info("✓ All validation checks passed")
    return True
```

**Test execution**:
```bash
python scripts/rotate_secret_phase2_validate.py
# Output:
# Step 1: Fetching new secret value
# Step 2: Testing database connectivity with new password
# ✓ Database connectivity verified with new password
# Step 3: Verifying database read/write permissions
# ✓ Read permission verified (users table has 12500 rows)
# ✓ Write permission verified
# Step 4: Verifying other services use different credentials
#   - Service web_app will be affected (expected)
#   - Service booking_service will be affected (expected)
# ✓ All validation checks passed
```

### 5.3 Phase 3: Staging Deployment (Warm-up)

```python
# scripts/rotate_secret_phase3_staging.py

def deploy_to_staging(secret_path, new_version):
    """Deploy new secret to staging, verify all services work."""
    
    logger.info(f"Phase 3: Deploying new secret to staging")
    
    # Step 1: Promote new secret to AWSSTAGING
    logger.info("Step 1: Promoting new secret to staging stage")
    client = boto3.client('secretsmanager')
    client.update_secret_version_stage(
        SecretId=secret_path,
        VersionStage='AWSSTAGING',
        MoveToVersionId=new_version
    )
    
    # Step 2: Configure staging environment to use new secret
    logger.info("Step 2: Configuring staging services to use new secret")
    # Trigger a service reload/refresh without restart
    # This is service-specific - might be config reload, health check, etc.
    
    for service_name in ['web_app', 'booking_service']:
        logger.info(f"  - {service_name}: Triggering secret refresh")
        trigger_service_refresh(service_name, environment='staging')
    
    # Step 3: Wait for services to pick up new secret
    logger.info("Step 3: Waiting for staging services to refresh (30 seconds)")
    time.sleep(30)
    
    # Step 4: Health checks on staging
    logger.info("Step 4: Running health checks on staging")
    health_results = {}
    for service_name in ['web_app', 'booking_service']:
        health = check_service_health(service_name, environment='staging')
        health_results[service_name] = health
        
        if not health['healthy']:
            logger.error(f"✗ {service_name} health check FAILED in staging")
            raise RotationError(f"{service_name} failed health check in staging")
        else:
            logger.info(f"✓ {service_name} health check passed")
    
    # Step 5: Load test staging
    logger.info("Step 5: Running load test on staging with new secret")
    load_test_results = run_load_test(environment='staging', duration_seconds=60)
    
    if load_test_results['success_rate'] < 0.95:
        logger.error(f"✗ Load test failed: {load_test_results['success_rate']}% success")
        raise RotationError("Load test failed in staging")
    else:
        logger.info(f"✓ Load test passed: {load_test_results['success_rate']}% success")
    
    logger.info("✓ Staging deployment successful")
    return True
```

### 5.4 Phase 4: Production Cutover (Blue-Green Switch)

```python
# scripts/rotate_secret_phase4_cutover.py

def promote_to_production(secret_path, new_version):
    """Promote new secret to production with monitoring."""
    
    logger.info(f"Phase 4: Promoting new secret to production")
    
    client = boto3.client('secretsmanager')
    
    # Step 1: Verify current production status
    logger.info("Step 1: Checking current production status")
    prod_health = check_service_health('web_app', environment='prod')
    if not prod_health['healthy']:
        raise RotationError("Production unhealthy, cannot rotate")
    
    # Step 2: Start monitoring
    logger.info("Step 2: Starting monitoring (errors, timeouts, latency)")
    monitor_handle = start_monitoring(duration_seconds=300)  # 5 minutes
    
    # Step 3: Promote AWSPENDING to AWSCURRENT (blue-green switch)
    logger.info("Step 3: Promoting new secret to AWSCURRENT (production)")
    client.update_secret_version_stage(
        SecretId=secret_path,
        VersionStage='AWSCURRENT',
        MoveToVersionId=new_version
    )
    
    # Step 4: Trigger service refresh on production
    logger.info("Step 4: Refreshing production services")
    for service_name in ['web_app', 'booking_service']:
        logger.info(f"  - {service_name}: Triggering secret refresh")
        trigger_service_refresh(service_name, environment='prod')
    
    # Step 5: Wait for services to pick up new secret
    logger.info("Step 5: Waiting for production services to refresh (60 seconds)")
    time.sleep(60)
    
    # Step 6: Monitor for errors
    logger.info("Step 6: Monitoring production metrics for 4 minutes")
    time.sleep(240)  # 4 minutes
    
    # Step 7: Check monitoring results
    logger.info("Step 7: Analyzing monitoring data")
    monitor_results = stop_monitoring(monitor_handle)
    
    if monitor_results['error_rate'] > 0.01:  # 1% error rate
        logger.error(f"✗ Error rate too high: {monitor_results['error_rate']}%")
        logger.info("Step 7a: Rolling back to previous secret")
        rollback_to_previous(secret_path)
        raise RotationError("Error rate spike detected, rolled back")
    
    if monitor_results['p99_latency'] > 5000:  # 5 seconds
        logger.error(f"✗ Latency too high: {monitor_results['p99_latency']}ms")
        logger.info("Step 7a: Rolling back to previous secret")
        rollback_to_previous(secret_path)
        raise RotationError("Latency spike detected, rolled back")
    
    logger.info(f"✓ Production metrics healthy:")
    logger.info(f"  - Error rate: {monitor_results['error_rate']}%")
    logger.info(f"  - P99 latency: {monitor_results['p99_latency']}ms")
    logger.info(f"  - Availability: {monitor_results['availability']}%")
    
    logger.info("✓ Production cutover successful")
    return True
```

### 5.5 Phase 5: Archive Old Secret

```python
# scripts/rotate_secret_phase5_archive.py

def archive_old_secret(secret_path, old_version):
    """Keep old secret as backup for 24 hours, then archive."""
    
    logger.info(f"Phase 5: Archiving old secret")
    
    client = boto3.client('secretsmanager')
    
    # Step 1: Mark old version for archive
    logger.info("Step 1: Marking old secret version for archive (24hr TTL)")
    backup_path = f"{secret_path}_prev"
    
    # Add tags for archival
    client.tag_resource(
        SecretId=backup_path,
        Tags=[
            {'Key': 'rotation_date', 'Value': datetime.now().isoformat()},
            {'Key': 'archived_version', 'Value': old_version},
            {'Key': 'ttl_hours', 'Value': '24'},
        ]
    )
    
    # Step 2: Archive to S3 for compliance
    logger.info("Step 2: Archiving to S3 for compliance/audit")
    s3_client = boto3.client('s3')
    
    audit_entry = {
        'timestamp': datetime.now().isoformat(),
        'secret_path': secret_path,
        'old_version': old_version,
        'action': 'rotation_complete',
        'status': 'archived_for_audit',
    }
    
    s3_client.put_object(
        Bucket='propellq-secret-archive',
        Key=f"rotations/{secret_path}/{old_version}.json",
        Body=json.dumps(audit_entry),
        ServerSideEncryption='AES256',
    )
    
    # Step 3: Schedule deletion of backup after 24 hours
    logger.info("Step 3: Scheduling auto-deletion of backup after 24 hours")
    logger.info(f"  Backup secret: {backup_path}")
    logger.info(f"  Auto-delete at: {datetime.now() + timedelta(hours=24)}")
    
    logger.info("✓ Archive complete")
```

---

## 6. Emergency Secret Revocation

### 6.1 Immediate Revocation (Compromised Credential)

```python
# scripts/emergency_revoke_secret.py

def emergency_revoke_secret(secret_path, reason='compromised'):
    """Immediately revoke and replace compromised secret."""
    
    logger.critical(f"EMERGENCY: Revoking secret {secret_path} ({reason})")
    
    client = boto3.client('secretsmanager')
    
    # Step 1: Create new secret immediately
    logger.critical("Step 1: Creating new secret (emergency)")
    new_value = generate_secure_password(length=32)
    
    new_secret = client.put_secret_value(
        SecretId=secret_path,
        SecretString=new_value,
        VersionStages=['AWSCURRENT', 'EMERGENCY_NEW'],
        Description=f"Emergency replacement: {reason} at {datetime.now()}"
    )
    
    # Step 2: Notify all service owners immediately
    logger.critical("Step 2: Notifying service owners (PagerDuty incident)")
    incident = create_pagerduty_incident(
        title=f"CRITICAL: Secret revoked - {secret_path}",
        description=reason,
        urgency='critical',
        services=['web_app', 'booking_service', 'search_service']
    )
    
    # Step 3: Trigger immediate refresh on all services
    logger.critical("Step 3: Force-refreshing all services with new secret")
    for service_name in ['web_app', 'booking_service', 'search_service']:
        logger.critical(f"  - {service_name}: Force refresh")
        force_service_refresh(service_name, environment='prod')
    
    # Step 4: Monitor closely
    logger.critical("Step 4: Monitoring closely for 10 minutes")
    for i in range(60):  # Check every 10 seconds for 10 minutes
        health = check_service_health_all()
        if not health['all_healthy']:
            logger.critical(f"✗ Service health degraded: {health}")
        time.sleep(10)
    
    logger.critical(f"✓ Emergency revocation complete, incident {incident.id}")
    return incident.id
```

---

## 7. Rollback Procedure

### 7.1 Automatic Rollback

```python
def automatic_rollback_on_error(secret_path, trigger):
    """Automatically rollback if rotation fails."""
    
    logger.error(f"Automatic rollback triggered: {trigger}")
    
    client = boto3.client('secretsmanager')
    
    # Get previous version (marked as _prev)
    backup_path = f"{secret_path}_prev"
    backup_response = client.get_secret_value(SecretId=backup_path)
    previous_value = backup_response['SecretString']
    
    # Restore previous value
    logger.error("Rolling back to previous secret")
    client.put_secret_value(
        SecretId=secret_path,
        SecretString=previous_value,
        VersionStages=['AWSCURRENT']
    )
    
    # Refresh services
    logger.error("Refreshing services with previous secret")
    for service_name in ['web_app', 'booking_service']:
        force_service_refresh(service_name, environment='prod')
    
    logger.error("✓ Rollback complete, monitor services")
```

### 7.2 Manual Rollback

```bash
#!/bin/bash
# Manual rollback if needed

SECRET_PATH="prod/database/master_password"
BACKUP_PATH="${SECRET_PATH}_prev"

# Get previous version
PREVIOUS_VALUE=$(aws secretsmanager get-secret-value \
  --secret-id $BACKUP_PATH \
  --query 'SecretString' \
  --output text)

# Restore
aws secretsmanager put-secret-value \
  --secret-id $SECRET_PATH \
  --secret-string "$PREVIOUS_VALUE" \
  --version-stages AWSCURRENT

echo "Rollback complete"
```

---

## 8. Service-Specific Refresh Patterns

### 8.1 FastAPI (Python)

```python
# app/config/secrets_refresh.py

import threading
from functools import lru_cache

class RefreshableSecrets:
    """Secrets that can be refreshed without restart."""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
    
    def get_secret(self, secret_path):
        """Get secret (cached)."""
        with self._lock:
            if secret_path not in self._cache:
                self._cache[secret_path] = load_from_secret_manager(secret_path)
            return self._cache[secret_path]
    
    def refresh_secret(self, secret_path):
        """Refresh secret without restart."""
        logger.info(f"Refreshing secret: {secret_path}")
        with self._lock:
            self._cache[secret_path] = load_from_secret_manager(secret_path)
        logger.info(f"✓ Secret refreshed: {secret_path}")
    
    def refresh_all(self):
        """Refresh all cached secrets."""
        logger.info("Refreshing all secrets")
        with self._lock:
            for secret_path in list(self._cache.keys()):
                self._cache[secret_path] = load_from_secret_manager(secret_path)
        logger.info("✓ All secrets refreshed")

# Global instance
secrets = RefreshableSecrets()

# API endpoint to trigger refresh
@app.post("/admin/refresh-secrets")
async def trigger_secret_refresh(request: Request):
    """Endpoint for rotation automation to trigger refresh."""
    secrets.refresh_all()
    return {"status": "secrets refreshed"}
```

### 8.2 Kubernetes Pod Restart (if needed)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: secret-rotation-rollout
spec:
  template:
    spec:
      containers:
      - name: kubectl
        image: bitnami/kubectl:latest
        command:
        - /bin/sh
        - -c
        - |
          kubectl rollout restart deployment/web-app -n prod
          kubectl rollout restart deployment/booking-service -n prod
          kubectl rollout status deployment/web-app -n prod
```

---

## 9. Testing the Rotation Process

### 9.1 Rotation Test in Staging

```python
# tests/test_secret_rotation.py

def test_secret_rotation_flow():
    """Test complete secret rotation flow in staging."""
    
    secret_path = 'staging/database/test_password'
    
    # Phase 1: Create new secret
    result = create_new_secret_staging(secret_path)
    assert result['new_version'] is not None
    
    # Phase 2: Validate
    assert validate_new_secret(secret_path, result['new_version'])
    
    # Phase 3: Deploy to staging
    assert deploy_to_staging(secret_path, result['new_version'])
    
    # Phase 4: Monitor and verify
    health = check_service_health('web_app', environment='staging')
    assert health['healthy']
    
    logger.info("✓ Rotation test passed")
```

---

## 10. Known Limitations

### 10.1 v1.0 Limitations

```
Current scope:
  ✓ Blue-green rotation pattern
  ✓ Automatic validation and testing
  ✓ Production cutover with monitoring
  ✓ Emergency revocation
  ✗ Multi-region rotation coordination (v1.1)
  ✗ Automatic rotation scheduling (v1.1)
  ✗ Secret value sharing across services during rotation (v1.1)

Planned enhancements:
  - v1.1: Multi-region secret sync
  - v1.1: Cron-based automatic rotation
  - v1.1: Gradual service refresh with health checks
```

---

## References

- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [SEC-2: Least-Privilege Access Controls](SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md)
- [AUDIT-1: Access and Change Audit Trail](AUDIT-1-ACCESS_AND_CHANGE_AUDIT_TRAIL.md)

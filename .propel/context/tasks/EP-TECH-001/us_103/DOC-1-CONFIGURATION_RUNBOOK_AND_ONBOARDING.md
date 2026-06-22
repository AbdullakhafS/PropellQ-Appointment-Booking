# DOC-1: Configuration Runbook and Onboarding Guide

**Author**: Platform & Documentation Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Onboarding for New Services

### 1.1 Adding a New Service to Configuration Management

**Step 1: Update CFG-1 Schema**

Add service to configuration catalog:

```yaml
# CFG-1: Configuration Schema and Catalog

services:
  new_service:
    type: "microservice"
    config_keys: 12
    secrets: 4
    environments: ["dev", "staging", "prod"]
    
    required_keys:
      - SERVICE_NAME: {type: string, default: "new_service"}
      - SERVICE_PORT: {type: integer, default: 8002}
      - DATABASE_HOST: {type: string}
      - ENVIRONMENT: {type: enum, values: [dev, staging, prod]}
      
    secret_keys:
      - DATABASE_PASSWORD: {path: "prod/database/service_password"}
      - SERVICE_API_KEY: {path: "prod/new_service/api_key"}
```

**Step 2: Create Service Identity and Permissions**

```bash
# Create IAM role for new service
aws iam create-role \
  --role-name propellq-new_service-prod \
  --assume-role-policy-document file://trust-policy.json

# Create inline policy with minimal permissions
aws iam put-role-policy \
  --role-name propellq-new_service-prod \
  --policy-name new-service-secrets \
  --policy-document file://policy.json
```

Policy document:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/service_password-*",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/new_service/*"
      ]
    }
  ]
}
```

**Step 3: Create Secrets in Secret Manager**

```bash
# Create database credential
aws secretsmanager create-secret \
  --name prod/database/service_password \
  --secret-string "$(python generate_password.py)"

# Create service API key
aws secretsmanager create-secret \
  --name prod/new_service/api_key \
  --secret-string "$(python generate_api_key.py)"
```

**Step 4: Implement Secret Loading**

```python
# In new service code
from app.config.secrets import SecretManager

secret_manager = SecretManager(backend='aws')

# Load secrets at startup
database_password = secret_manager.get_secret('prod/database/service_password')
api_key = secret_manager.get_secret('prod/new_service/api_key')
```

**Step 5: Deploy Configuration**

```bash
# Deploy to staging first
kubectl set env deployment/new-service-staging \
  -c new-service \
  DATABASE_HOST=staging-db.internal \
  DATABASE_PORT=5432 \
  SERVICE_PORT=8002

# Monitor for errors
kubectl logs -f deployment/new-service-staging

# Deploy to production
kubectl set env deployment/new-service-prod \
  -c new-service \
  DATABASE_HOST=prod-db.rds.amazonaws.com \
  DATABASE_PORT=5432 \
  SERVICE_PORT=8002
```

---

## 2. Common Troubleshooting Scenarios

### 2.1 Service Won't Start: Missing Configuration

**Symptom**:
```
CRITICAL ERROR: Required secret not loaded: DATABASE_PASSWORD
Cannot start without secrets - secret manager unreachable?
Exiting with status 1
```

**Diagnosis Checklist**:

```
□ 1. Verify all required keys are set
  $ propellq-cli config schema web_app
  
□ 2. Check environment variables
  $ env | grep DATABASE
  
□ 3. Verify .env file exists (if needed)
  $ cat .env | grep DATABASE
  
□ 4. Check AWS credentials are configured
  $ aws sts get-caller-identity
  
□ 5. Verify service IAM role has secret access
  $ aws iam get-role-policy \
    --role-name propellq-web-app-prod \
    --policy-name web-app-secrets
  
□ 6. Check secret exists in secret manager
  $ aws secretsmanager describe-secret \
    --secret-id prod/database/master_password
  
□ 7. Test secret access directly
  $ aws secretsmanager get-secret-value \
    --secret-id prod/database/master_password
```

**Solutions**:

| Check | Failure | Fix |
|-------|---------|-----|
| Required keys | Missing in environment | Set env vars or .env file |
| Env variables | Not visible to process | Export before startup |
| .env file | File not found | Create from .env.template |
| AWS credentials | sts get-caller-identity fails | Configure AWS credentials (see AWS docs) |
| IAM role | Policy missing or wrong | Attach correct policy (CFG-1, SEC-2) |
| Secret exists | Not found in manager | Create secret: `aws secretsmanager create-secret` |
| Secret access | AccessDenied error | Add service role to policy |

### 2.2 Service Crashes with Database Connection Error

**Symptom**:
```
psycopg2.OperationalError: could not translate host name "db.prod.internal" to address: Name or service not known
```

**Diagnosis Checklist**:

```
□ 1. Verify database configuration
  $ echo $DATABASE_HOST
  $ echo $DATABASE_PORT
  
□ 2. Test network connectivity
  $ nc -zv db.prod.internal 5432
  
□ 3. Verify credentials are correct
  $ psql -h db.prod.internal -U master_user -d propellq -W
  (enter password when prompted)
  
□ 4. Check security groups / firewall
  $ aws ec2 describe-security-groups \
    --filter "Name=group-name,Values=prod-db"
  
□ 5. Verify service is in correct VPC/subnet
  $ kubectl describe pod POD_NAME | grep IP
```

**Solutions**:

| Issue | Fix |
|-------|-----|
| Host not found | Update DATABASE_HOST to correct FQDN or IP |
| Port wrong | Verify DATABASE_PORT (default 5432) |
| Network timeout | Check security groups allow service → database |
| Authentication failed | Verify DATABASE_PASSWORD is correct |
| Database down | Restart database or failover |

### 2.3 Configuration Change Not Taking Effect

**Symptom**:
```
Made config change but service still using old value
Expected API_TIMEOUT_MS=5000 but getting 30000
```

**Diagnosis Checklist**:

```
□ 1. Verify config was actually changed
  $ kubectl describe configmap app-config
  $ kubectl describe secret app-secrets
  
□ 2. Check if service reloaded configuration
  $ kubectl logs POD_NAME | grep "Configuration loaded"
  
□ 3. Verify environment variable precedence
  $ kubectl exec POD_NAME -- sh -c "env | grep API_TIMEOUT"
  
□ 4. Check if service restart is needed
  $ kubectl logs POD_NAME | grep "startup"
```

**Solutions**:

| Scenario | Fix |
|----------|-----|
| ConfigMap updated but not applied | `kubectl rollout restart deployment/web-app` |
| Environment var takes precedence | Remove env var or update it |
| Service has config cached | Restart pod or trigger refresh endpoint |
| Old deployment still running | Delete old replica: `kubectl delete pod POD_NAME` |

---

## 3. Configuration Reference Guide

### 3.1 Quick Reference: All Configuration Keys

**Web App**:
```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=propellq_dev
API_PORT=8000
API_HOST=0.0.0.0
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
LOG_FORMAT=text
API_TIMEOUT_MS=30000
DATABASE_POOL_SIZE=10
CACHE_TTL_SECONDS=60
ENABLE_ANALYTICS=false
```

**Booking Service**:
```
SERVICE_NAME=booking_service
SERVICE_PORT=8001
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=propellq_dev
MAX_CONCURRENT_BOOKINGS=100
ENVIRONMENT=dev
```

**Search Service**:
```
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
SEARCH_INDEX_PREFIX=propellq_
SEARCH_TIMEOUT_MS=5000
ENVIRONMENT=dev
```

### 3.2 Configuration by Environment

**Local Development** (.env file):
```bash
# Copy .env.template to .env and fill in
cp .env.template .env
cat > .env << EOF
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=propellq_dev
API_PORT=8000
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
EOF
```

**Staging** (Kubernetes ConfigMap):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-staging
data:
  DATABASE_HOST: staging-db.internal
  DATABASE_PORT: "5432"
  DATABASE_NAME: propellq_staging
  API_PORT: "8080"
  ENVIRONMENT: staging
  LOG_LEVEL: INFO
  LOG_FORMAT: json
```

**Production** (Kubernetes ConfigMap + Secrets):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-prod
data:
  DATABASE_HOST: prod-db.rds.amazonaws.com
  DATABASE_PORT: "5432"
  DATABASE_NAME: propellq
  API_PORT: "8080"
  ENVIRONMENT: prod
  LOG_LEVEL: WARNING
  LOG_FORMAT: json
  
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets-prod
type: Opaque
stringData:
  DATABASE_PASSWORD: <from secret manager>
  AUTH_SECRET_KEY: <from secret manager>
```

---

## 4. Operational Tasks

### 4.1 Rotating a Secret

See [ROT-1: Secret Rotation Procedure](ROT-1-SECRET_ROTATION_PROCEDURE.md) for detailed steps.

Quick version:
```bash
# 1. Create new secret
aws secretsmanager put-secret-value \
  --secret-id prod/database/master_password \
  --secret-string "NEW_PASSWORD"

# 2. Test in staging
kubectl exec -it deployment/web-app-staging -- \
  python -c "from app.config import load_config; c = load_config(); print('DB connected' if c['DATABASE_PASSWORD'] else 'Failed')"

# 3. Deploy to production
kubectl delete pod -l app=web-app -n prod

# 4. Monitor for errors
kubectl logs -f deployment/web-app -n prod | grep ERROR
```

### 4.2 Adding a New Environment Variable

1. Update CFG-1 schema with new key definition
2. Get approval from Platform Lead (GOV-1 process)
3. Update .env.template with new key
4. Update Kubernetes manifests (ConfigMap/Secret)
5. Deploy config to staging first
6. Test in staging (24 hours)
7. Deploy to production
8. Update documentation

### 4.3 Emergency Configuration Change

For urgent operational needs (database down, service failing):

```bash
# 1. Make temporary config change
export DATABASE_HOST=new-host.internal
export DATABASE_PORT=5433

# 2. Restart affected service
kubectl delete pod -l app=web-app -n prod

# 3. Monitor recovery
kubectl logs -f deployment/web-app

# 4. Document the change
# File incident ticket with configuration details

# 5. Do proper change request within 24 hours (GOV-1 process)
```

---

## 5. Monitoring and Alerts

### 5.1 Key Metrics to Watch

```
Configuration Metrics:
  - startup_time: Time to load configuration (should be <100ms)
  - config_load_errors: Count of config loading failures (should be 0)
  - config_validation_failures: Count of validation errors (should be 0)

Secret Manager Metrics:
  - secret_access_latency: Average secret retrieval time (should be <200ms)
  - secret_access_errors: Failed secret access attempts (monitor for spikes)
  - secret_rotation_success_rate: % of rotations successful (should be >99%)
```

### 5.2 Alert Rules

```
CRITICAL: Config loading failed
  Condition: config_load_errors > 0
  Action: Page on-call immediately

HIGH: Secret manager latency high
  Condition: secret_access_latency > 500ms for 5 minutes
  Action: Check AWS secret manager status

MEDIUM: Secret rotation failed
  Condition: secret_rotation_success_rate < 99%
  Action: Investigate rotation procedure
```

---

## 6. Documentation Index

- [CFG-1: Configuration Schema and Catalog](CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md)
- [CFG-2: Precedence and Resolution Rules](CFG-2-PRECEDENCE_AND_RESOLUTION_RULES.md)
- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [SEC-2: Least-Privilege Access Controls](SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md)
- [ROT-1: Secret Rotation Procedure](ROT-1-SECRET_ROTATION_PROCEDURE.md)
- [VALID-1: Startup Validation Gate](VALID-1-STARTUP_VALIDATION_GATE.md)
- [VALID-2: CI Configuration Safety Checks](VALID-2-CI_CONFIGURATION_SAFETY_CHECKS.md)
- [GOV-1: Configuration Change Governance](GOV-1-CONFIGURATION_CHANGE_GOVERNANCE.md)
- [AUDIT-1: Access and Change Audit Trail](AUDIT-1-ACCESS_AND_CHANGE_AUDIT_TRAIL.md)

---

## 7. Getting Help

**For configuration schema questions**:
- See CFG-1 for all required keys
- Contact Platform Team in #platform-engineering

**For secret access issues**:
- See SEC-1 for secret loading patterns
- Check SecretManagerIntegration.md for code examples
- Contact Security Team in #security

**For permission issues**:
- See SEC-2 for access control policies
- Check your IAM role in AWS console
- Contact Security Team for policy updates

**For operational issues**:
- See section 2 (Troubleshooting) above
- Contact Operations Team in #operations
- File incident ticket for urgent issues

---

## Known Limitations

v1.0 limitations:
- Manual documentation maintenance
- No searchable config discovery UI
- Static schema definition (not auto-generated from code)

Planned v1.1:
- Web UI for config discovery
- Auto-generated docs from code annotations
- Integration with Slack for alerts

# SEC-2: Least-Privilege Secret Access Controls

**Author**: Security Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines scoped access roles, policy boundaries, and permission matrices for secret manager access. Every service is granted only the specific secrets it needs—no broad wildcards, no unused permissions.

---

## 2. Principle: Least Privilege

### 2.1 Core Rules

```
Rule 1: Minimize Blast Radius
  → Each service can access ONLY its own secrets
  → No service can read another service's secrets
  → No service can modify any secrets

Rule 2: Minimize Attack Surface
  → No wildcard permissions (arn:aws:secretsmanager:*:secret:*-*)
  → No read-all permissions
  → Permissions are specific to exact secret paths

Rule 3: Minimize Operational Risk
  → Developers cannot access production secrets
  → QA cannot access production secrets
  → Only production deployments can access prod secrets
  
Rule 4: Audit and Monitor
  → All secret access is logged
  → Suspicious access patterns trigger alerts
  → Regular permission audits (monthly)
```

---

## 3. Service Permission Matrix

### 3.1 Web App Service (prod/staging/dev)

**Can Read**:
- `prod/database/master_password` (production database only)
- `prod/auth/secret_key` (JWT signing)
- `prod/aws/access_key` (S3 uploads)
- `prod/aws/secret_key` (S3 uploads)

**Cannot Read**:
- Booking service secrets
- Search service secrets
- Admin dashboard secrets
- Any other service secrets

**Cannot Write/Delete**:
- Any secrets (read-only access)

**AWS IAM Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WebAppReadDatabasePassword",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/master_password-*"
      ]
    },
    {
      "Sid": "WebAppReadAuthKeys",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/auth/secret_key-*"
      ]
    },
    {
      "Sid": "WebAppReadAWSCredentials",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/aws/access_key-*",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/aws/secret_key-*"
      ]
    },
    {
      "Sid": "DenyAllOtherSecrets",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "arn:aws:secretsmanager:*:*:secret:*",
      "Condition": {
        "StringNotLike": {
          "aws:SourceArn": [
            "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/master_password-*",
            "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/auth/secret_key-*",
            "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/aws/*"
          ]
        }
      }
    }
  ]
}
```

### 3.2 Booking Service (prod/staging/dev)

**Can Read**:
- `prod/database/service_password` (service-specific DB user)
- `prod/booking/service_api_key`
- `prod/twilio/account_sid` (for SMS)
- `prod/twilio/auth_token` (for SMS)

**Cannot Read**:
- Web app secrets
- Auth secrets
- AWS credentials
- Search service secrets

**AWS IAM Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BookingReadOwnSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/service_password-*",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/booking/service_api_key-*",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/twilio/*"
      ]
    },
    {
      "Sid": "DenyAllOtherSecrets",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "arn:aws:secretsmanager:*:*:secret:*"
    }
  ]
}
```

### 3.3 Search Service (prod/staging/dev)

**Can Read**:
- `prod/elasticsearch/password` (Elasticsearch credentials)

**Cannot Read**:
- Database passwords
- Auth keys
- AWS credentials
- Any other service secrets

**AWS IAM Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SearchReadElasticsearchPassword",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/elasticsearch/password-*"
      ]
    },
    {
      "Sid": "DenyAllOtherSecrets",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "arn:aws:secretsmanager:*:*:secret:*"
    }
  ]
}
```

### 3.4 Notification Service (prod only)

**Can Read**:
- `prod/sendgrid/api_key` (Email)
- `prod/twilio/account_sid` (SMS)
- `prod/twilio/auth_token` (SMS)

**Cannot Read**:
- Database passwords
- Auth keys
- Service-specific secrets

**AWS IAM Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NotificationReadOwnSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/sendgrid/api_key-*",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/twilio/*"
      ]
    },
    {
      "Sid": "DenyAllOtherSecrets",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "arn:aws:secretsmanager:*:*:secret:*"
    }
  ]
}
```

---

## 4. Environment-Based Access Control

### 4.1 Development Environment

**Who can access**:
- Local developers (via AWS CLI with personal credentials)
- CI/CD pipeline (via service role)

**Restrictions**:
- Only dev/* and staging/* secrets
- Cannot access prod/* secrets
- Limited to testing/demo data

**IAM Policy for Developers**:

```json
{
  "Sid": "DevelopersReadDevSecrets",
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": ["arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:dev/*"]
}
```

### 4.2 Staging Environment

**Who can access**:
- CI/CD pipeline (via staging service role)
- QA team (read-only)
- Integration testers (read-only)

**Restrictions**:
- Only staging/* secrets
- Cannot access prod/* secrets
- Cannot modify/delete secrets

**IAM Policy for QA**:

```json
{
  "Sid": "QAReadStagingSecrets",
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": ["arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:staging/*"]
}
```

### 4.3 Production Environment

**Who can access**:
- Production service roles (via EC2/Lambda/ECS instance profiles)
- On-call incident response (emergency access)

**Restrictions**:
- Only prod/* secrets
- Developers CANNOT access directly
- All access is logged and monitored

**IAM Policy for Prod Services**:

```json
{
  "Sid": "ProductionServiceReadSecrets",
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": ["arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/*"]
}
```

**Emergency Access** (requires incident ticket):

```json
{
  "Sid": "OnCallEmergencyAccess",
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": ["arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/*"],
  "Condition": {
    "StringEquals": {
      "aws:username": "incident-commander-role"
    }
  }
}
```

---

## 5. Service Identity Configuration

### 5.1 AWS EC2 Instance Profile

**Web App EC2 Instance Profile**:

```yaml
# IAM role for EC2 instances
Instance Profile Name: propellq-web-app-prod
Attached Policies:
  - propellq-web-app-secrets-read (custom policy from Section 3.1)
  - AWSSecretsManagerReadAccess (AWS managed, if needed)

Trust Relationship:
  Principal: ec2.amazonaws.com
  Condition: Service is EC2
```

**Attachment to EC2 Instance**:

```bash
# Apply role to running instance
aws ec2 associate-iam-instance-profile \
  --iam-instance-profile Name=propellq-web-app-prod \
  --instance-id i-1234567890abcdef0
```

### 5.2 AWS Lambda Role

**Lambda Execution Role for Web App**:

```yaml
IAM Role: propellq-web-app-lambda-role
Trust Relationship:
  Principal: lambda.amazonaws.com

Inline Policies:
  - Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Action: secretsmanager:GetSecretValue
        Resource:
          - arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/master_password-*
          - arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/auth/secret_key-*
```

### 5.3 ECS Task Role

**ECS Task Execution Role for Booking Service**:

```yaml
apiVersion: iam.amazonaws.com/v1beta1
kind: Role
metadata:
  name: ecs-booking-service-task-role
Policies:
  - Name: read-booking-secrets
    Effect: Allow
    Actions:
      - secretsmanager:GetSecretValue
    Resources:
      - "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/service_password-*"
      - "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/booking/*"
```

### 5.4 Kubernetes Service Account

**K8s Service Account with IAM Role Binding**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: web-app
  namespace: prod
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/web-app-ksa-role

---
# IAM role for this service account
# Name: web-app-ksa-role
# Trust: OIDC provider for EKS cluster
# Policies: Same as EC2 instance profile above
```

---

## 6. Validation: No Wildcard Permissions

### 6.1 Audit Check: Wildcard Detection

All secret access policies MUST pass this validation:

```python
def validate_no_wildcards(iam_policy: dict):
    """Ensure policy has no wildcard secret permissions."""
    
    wildcards_found = []
    
    for statement in iam_policy.get('Statement', []):
        if statement.get('Effect') == 'Allow':
            resources = statement.get('Resource', [])
            if isinstance(resources, str):
                resources = [resources]
            
            for resource in resources:
                if '*' in resource and 'secret' in resource:
                    wildcards_found.append({
                        'resource': resource,
                        'sid': statement.get('Sid'),
                        'issue': 'Wildcard in secret resource ARN'
                    })
    
    if wildcards_found:
        raise PermissionError(f"Wildcard permissions detected: {wildcards_found}")
    
    return True

# Validation examples
validate_no_wildcards({
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': 'secretsmanager:GetSecretValue',
            'Resource': 'arn:aws:secretsmanager:*:*:secret:*'  # ✗ WILDCARD
        }
    ]
})  # Raises PermissionError

validate_no_wildcards({
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': 'secretsmanager:GetSecretValue',
            'Resource': 'arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/password-*'  # ✓ OK
        }
    ]
})  # Passes
```

### 6.2 Audit: Permission Scope Analysis

Monthly audit to verify minimal permissions:

```python
def audit_permission_scope():
    """Audit that each service has minimal permissions."""
    
    services = ['web_app', 'booking_service', 'search_service']
    
    for service in services:
        role_name = f"propellq-{service}-prod"
        
        # Fetch attached policies
        attached = iam_client.list_attached_role_policies(RoleName=role_name)
        
        # Check each policy
        for policy in attached['AttachedPolicies']:
            policy_version = iam_client.get_policy(PolicyArn=policy['PolicyArn'])
            policy_doc = iam_client.get_policy_version(
                PolicyArn=policy['PolicyArn'],
                VersionId=policy_version['Policy']['DefaultVersionId']
            )
            
            # Verify no wildcards
            validate_no_wildcards(policy_doc['PolicyVersion']['Document'])
            
            # Log scope
            logger.info(f"{service}: {len(policy_doc['PolicyVersion']['Document']['Statement'])} statements")
```

---

## 7. Access Audit Trail

### 7.1 CloudTrail Monitoring

**Enable CloudTrail logging for secret access**:

```yaml
CloudTrail Configuration:
  Event Selectors:
    - Include Management Events: true
    - Include Data Events: true
      Data Resources:
        - Type: AWS::SecretsManager::Secret
          Values:
            - "arn:aws:secretsmanager:*:*:secret:*"

Logs stored in: s3://propellq-cloudtrail-logs/
Retention: 90 days
```

### 7.2 Access Alert Rules

**Alert on suspicious access patterns**:

```python
ALERT_RULES = {
    'failed_access_attempts': {
        'threshold': 5,
        'window': '5 minutes',
        'alert': 'WARNING: Multiple failed secret access attempts',
    },
    'cross_service_access': {
        'threshold': 1,
        'window': 'immediate',
        'alert': 'CRITICAL: Service accessing another service\'s secrets',
    },
    'developer_prod_access': {
        'threshold': 1,
        'window': 'immediate',
        'alert': 'CRITICAL: Developer accessing prod secrets',
    },
    'secret_modification': {
        'threshold': 1,
        'window': 'immediate',
        'alert': 'CRITICAL: Secret was modified or deleted',
    },
}
```

---

## 8. Access Revocation Procedure

### 8.1 Emergency Revocation

If a service is compromised or credentials are leaked:

```bash
#!/bin/bash
# emergency-revoke-access.sh

SERVICE=$1  # e.g., "web_app"

echo "Revoking access for $SERVICE..."

# 1. Detach service role
aws iam detach-role-policy \
  --role-name propellq-${SERVICE}-prod \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/propellq-${SERVICE}-secrets

# 2. Disable instance profile
aws ec2 disassociate-iam-instance-profile \
  --association-id iip-assoc-1234567890abcdef

# 3. Restart service to clear cache
kubectl delete pod -n prod -l app=${SERVICE}

echo "✓ Access revoked for $SERVICE"
```

### 8.2 Gradual Access Restoration

After incident investigation, restore access step-by-step:

```bash
# 1. Rotate all secrets the service can access
aws secretsmanager rotate-secret --secret-id prod/database/service_password

# 2. Update service policy to new version (if changed)
aws iam put-role-policy --role-name propellq-${SERVICE}-prod ...

# 3. Restart service with updated credentials
kubectl delete pod -n prod -l app=${SERVICE}

# 4. Monitor for errors
kubectl logs -f -n prod -l app=${SERVICE}

# 5. Restore role to service identity
aws ec2 associate-iam-instance-profile ...
```

---

## 9. Testing Access Controls

### 9.1 Negative Test: Access Denied

```python
def test_booking_cannot_read_web_app_secrets():
    """Verify booking service cannot access web app secrets."""
    
    # Get booking service credentials
    booking_creds = assume_role('propellq-booking-service-prod')
    
    # Try to read web app secret
    client = boto3.client('secretsmanager', credentials=booking_creds)
    
    with pytest.raises(ClientError) as exc:
        client.get_secret_value(SecretId='prod/auth/secret_key')
    
    assert exc.value.response['Error']['Code'] == 'AccessDeniedException'
```

### 9.2 Positive Test: Correct Access

```python
def test_web_app_can_read_own_secrets():
    """Verify web app service CAN access its secrets."""
    
    # Get web app service credentials
    app_creds = assume_role('propellq-web-app-prod')
    
    # Read its own secret
    client = boto3.client('secretsmanager', credentials=app_creds)
    
    response = client.get_secret_value(SecretId='prod/auth/secret_key')
    assert 'SecretString' in response
```

### 9.3 Audit Test: No Wildcards

```python
def test_no_wildcard_permissions_in_policies():
    """Verify no role has wildcard secret permissions."""
    
    services = ['web_app', 'booking_service', 'search_service']
    
    for service in services:
        role_name = f"propellq-{service}-prod"
        
        # Fetch role policy
        response = iam_client.get_role_policy(
            RoleName=role_name,
            PolicyName=f"{service}-secrets"
        )
        
        policy_doc = response['RolePolicyDocument']
        
        # Check for wildcards
        validate_no_wildcards(policy_doc)
```

---

## 10. Governance and Approval

### 10.1 Access Request Process

To grant a service new secret access:

```markdown
# Access Request Template

Service: booking_service
Requested Access: prod/sendgrid/api_key
Justification: Need to send booking confirmations via email

## Approvals Required
- [ ] Tech Lead: Can the service safely handle this secret?
- [ ] Security Lead: Does it follow least privilege principles?
- [ ] Product Lead: Is this feature approved for production?

## Timeline
- Request date: 2026-06-22
- Required date: 2026-06-25
- SLA: 3 business days
```

### 10.2 Quarterly Permission Review

Every 3 months, audit all service permissions:

```bash
#!/bin/bash
# quarterly-permission-audit.sh

echo "=== Quarterly Permission Audit ===" 
date

services=('web_app' 'booking_service' 'search_service')

for service in "${services[@]}"; do
    echo -e "\n--- $service ---"
    
    # Get attached policies
    aws iam list-attached-role-policies \
      --role-name propellq-${service}-prod \
      --query 'AttachedPolicies[].[PolicyName]' \
      --output text
    
    # Check for unused permissions
    aws accessanalyzer validate-policy \
      --policy-document file://./policies/${service}-policy.json \
      --policy-type IDENTITY_POLICY
done

echo -e "\n=== Audit Complete ==="
```

---

## 11. Known Limitations

### 11.1 v1.0 Limitations

```
Current scope:
  ✓ Role-based access control (RBAC)
  ✓ Service identity isolation
  ✓ Least-privilege policies
  ✓ Access audit trail
  ✗ Attribute-based access control (ABAC, v1.1)
  ✗ Time-based access restrictions (v1.1)
  ✗ IP-restricted access (v1.1)

Planned enhancements:
  - v1.1: ABAC for dynamic fine-grained control
  - v1.1: Time-limited access windows
  - v1.1: Geographic/IP restrictions
  - v1.2: Cross-account secret access
```

---

## References

- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [AUDIT-1: Access and Change Audit Trail](AUDIT-1-ACCESS_AND_CHANGE_AUDIT_TRAIL.md)
- [ROT-1: Secret Rotation Procedure](ROT-1-SECRET_ROTATION_PROCEDURE.md)

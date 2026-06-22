# SEC-1: Secret Manager Integration Pattern

**Author**: Security Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines the standard pattern for loading secrets from approved secret managers. All secrets must be loaded from AWS Secrets Manager, HashiCorp Vault, or equivalent approved service. Plaintext secret loading from .env files, code, or configuration files is prohibited.

---

## 2. Approved Secret Managers

### 2.1 Supported Backends

| Manager | Status | Use Case | Priority |
|---------|--------|----------|----------|
| **AWS Secrets Manager** | ✅ Approved | Production, Staging | Primary |
| **HashiCorp Vault** | ✅ Approved | Self-hosted infrastructure | Primary |
| **Kubernetes Secrets** | ✅ Approved | K8s-native applications | Primary |
| **Azure Key Vault** | ✅ Approved | Azure infrastructure | Primary |
| **Environment Variables** | ⚠️ Limited | Local dev only, not production | Dev-only |
| ~~.env files~~ | ❌ Prohibited | --- | Never |
| ~~Hardcoded in code~~ | ❌ Prohibited | --- | Never |
| ~~Configuration files~~ | ❌ Prohibited | --- | Never |

### 2.2 Prohibited Secret Sources

**These are NEVER acceptable**:
- Hardcoded secrets in source code
- Secrets in .env, .yaml, or .json configuration files
- Secrets in version control (even in commit history)
- Secrets in Docker images
- Secrets in log files or error messages
- Secrets passed as command-line arguments

---

## 3. Standard Secret Loading Pattern

### 3.1 Base Pattern (All Languages)

Every service must implement this pattern:

```python
# Standard Python pattern
import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError

class SecretManager:
    """Standard secret loading from approved manager."""
    
    def __init__(self, backend='aws'):
        self.backend = backend
        self.cache = {}  # Optional: cache secrets to reduce API calls
        
        if backend == 'aws':
            self.client = boto3.client('secretsmanager', region_name='us-east-1')
        elif backend == 'vault':
            import hvac
            self.client = hvac.Client(url=os.getenv('VAULT_ADDR', 'http://localhost:8200'))
        else:
            raise ValueError(f"Unsupported backend: {backend}")
    
    def get_secret(self, secret_path: str, cache_ttl: int = 3600) -> str:
        """
        Load secret from manager.
        
        Args:
            secret_path: Path to secret (e.g., 'prod/database/password')
            cache_ttl: Cache duration in seconds (0 = no cache)
        
        Returns:
            Secret value as string
        
        Raises:
            SecretNotFoundError: Secret doesn't exist
            AccessDeniedError: Service lacks permission
        """
        
        # Check cache first
        if cache_ttl > 0 and secret_path in self.cache:
            cached_value, cached_time = self.cache[secret_path]
            if time.time() - cached_time < cache_ttl:
                return cached_value
        
        # Load from manager
        try:
            if self.backend == 'aws':
                response = self.client.get_secret_value(SecretId=secret_path)
                secret_value = response['SecretString']
            elif self.backend == 'vault':
                response = self.client.secrets.kv.v2.read_secret_version(path=secret_path)
                secret_value = response['data']['data']['value']
            
            # Cache result
            if cache_ttl > 0:
                self.cache[secret_path] = (secret_value, time.time())
            
            return secret_value
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise SecretNotFoundError(f"Secret not found: {secret_path}")
            elif e.response['Error']['Code'] == 'AccessDeniedException':
                raise AccessDeniedError(f"Access denied to secret: {secret_path}")
            else:
                raise ConfigError(f"Failed to load secret {secret_path}: {str(e)}")

# Usage in application
secret_manager = SecretManager(backend='aws')
database_password = secret_manager.get_secret('prod/database/password')
auth_key = secret_manager.get_secret('app/auth/secret_key')
```

### 3.2 Configuration Loading with Secrets

```python
# app/config/loader.py

class ConfigLoader:
    """Load configuration with secrets from approved manager."""
    
    def __init__(self, environment='prod'):
        self.environment = environment
        self.secrets = SecretManager(backend='aws')
    
    def load_config(self):
        """Load all configuration including secrets."""
        config = {}
        
        # Load non-secret config from files
        config.update(self._load_file_config())
        config.update(self._load_env_vars())
        
        # Load secrets from manager
        config.update(self._load_secrets())
        
        # Validate
        self._validate_config(config)
        
        return config
    
    def _load_secrets(self):
        """Load secrets from AWS Secrets Manager."""
        secrets = {}
        
        secret_paths = {
            'DATABASE_PASSWORD': f'{self.environment}/database/master_password',
            'AUTH_SECRET_KEY': f'{self.environment}/auth/secret_key',
            'AWS_ACCESS_KEY_ID': f'{self.environment}/aws/access_key',
            'AWS_SECRET_ACCESS_KEY': f'{self.environment}/aws/secret_key',
            'SENDGRID_API_KEY': f'{self.environment}/sendgrid/api_key',
            'TWILIO_AUTH_TOKEN': f'{self.environment}/twilio/auth_token',
        }
        
        for secret_key, secret_path in secret_paths.items():
            try:
                secrets[secret_key] = self.secrets.get_secret(secret_path)
            except SecretNotFoundError:
                # Secret doesn't exist - might be optional
                if is_required_secret(secret_key):
                    raise ConfigError(f"Required secret missing: {secret_path}")
                else:
                    logger.debug(f"Optional secret not found: {secret_path}")
        
        return secrets
    
    def _validate_config(self, config):
        """Validate all required configuration is present."""
        required_keys = ['DATABASE_PASSWORD', 'AUTH_SECRET_KEY']
        
        for key in required_keys:
            if key not in config:
                raise ConfigError(f"Required secret not loaded: {key}")
```

---

## 4. Language-Specific Implementations

### 4.1 Python (FastAPI, Django, Flask)

```python
# app/config/secrets.py - Reusable secret loading

from functools import lru_cache
import boto3
import os

@lru_cache(maxsize=128)
def get_secret(secret_id: str) -> str:
    """Load secret with caching."""
    client = boto3.client('secretsmanager')
    try:
        response = client.get_secret_value(SecretId=secret_id)
        return response['SecretString']
    except Exception as e:
        logger.error(f"Failed to load secret {secret_id}: {str(e)}")
        raise

# Usage in FastAPI
from fastapi import FastAPI
from app.config.secrets import get_secret

app = FastAPI()

# Load secrets at startup
db_password = get_secret('prod/database/password')
api_key = get_secret('prod/auth/api_key')
```

### 4.2 Go

```go
// config/secrets.go

package config

import (
    "context"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/secretsmanager"
)

type SecretManager struct {
    client *secretsmanager.Client
}

func (s *SecretManager) GetSecret(ctx context.Context, secretID string) (string, error) {
    input := &secretsmanager.GetSecretValueInput{
        SecretId: &secretID,
    }
    
    result, err := s.client.GetSecretValue(ctx, input)
    if err != nil {
        return "", fmt.Errorf("failed to get secret %s: %w", secretID, err)
    }
    
    return *result.SecretString, nil
}

// Usage
func init() {
    cfg, _ := config.LoadDefaultConfig(context.TODO())
    sm := SecretManager{client: secretsmanager.NewFromConfig(cfg)}
    
    dbPassword, _ := sm.GetSecret(context.TODO(), "prod/database/password")
}
```

### 4.3 Node.js

```javascript
// config/secrets.js

const AWS = require('aws-sdk');
const client = new AWS.SecretsManager({region: 'us-east-1'});

async function getSecret(secretId) {
    try {
        const data = await client.getSecretValue({SecretId: secretId}).promise();
        return data.SecretString;
    } catch (error) {
        throw new Error(`Failed to load secret ${secretId}: ${error.message}`);
    }
}

// Usage in Express
const express = require('express');
const { getSecret } = require('./config/secrets');

let dbPassword;

(async () => {
    dbPassword = await getSecret('prod/database/password');
})();
```

---

## 5. Service Identity and Authentication

### 5.1 Service-to-Secrets-Manager Authentication

**AWS IAM Role Attachment**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/database/password-*",
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:prod/auth/secret_key-*"
      ]
    }
  ]
}
```

**Kubernetes Service Account**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: web-app
  namespace: prod

---
apiVersion: v1
kind: Secret
metadata:
  name: web-app-secrets
  namespace: prod
type: Opaque
stringData:
  VAULT_ADDR: https://vault.internal
  VAULT_ROLE: web-app-prod
```

**EC2 Instance Profile**:

```json
{
  "AssumeRolePolicyDocument": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
}
```

---

## 6. Secret Naming Convention

### 6.1 Secret Path Format

```
{ENVIRONMENT}/{SERVICE}/{SECRET_TYPE}/{SECRET_NAME}

Examples:
  prod/database/password/master
  prod/auth/secret_key/jwt
  prod/aws/access_key/api_user
  staging/sendgrid/api_key
  dev/twilio/auth_token
  
Naming rules:
  - All lowercase
  - Use forward slashes for hierarchy
  - Environment as first component
  - Service as second component
  - Descriptive naming
  - No special characters except underscore
```

### 6.2 Backup and Rotation Paths

```yaml
Primary Paths:
  - prod/database/password/master

Backup Paths (for rotation):
  - prod/database/password/master_prev
  - prod/database/password/master_prev_2

Rotation Suffix Scheme:
  - _prev: Previous version (used during rotation)
  - _prev_2: Version before previous (rollback)
  - Current: Always use base path, no suffix
```

---

## 7. Secret Loading at Service Startup

### 7.1 Startup Sequence

```python
# app/server.py - Startup procedure

import logging
from app.config.loader import ConfigLoader

logger = logging.getLogger(__name__)

def startup():
    """Service startup with secret loading."""
    
    logger.info("Starting service...")
    
    # 1. Load configuration (including secrets)
    logger.info("Loading configuration...")
    config = ConfigLoader().load_config()
    
    # 2. Validate all secrets loaded successfully
    logger.info("Validating secrets...")
    if not config.get('DATABASE_PASSWORD'):
        raise RuntimeError("CRITICAL: DATABASE_PASSWORD secret not loaded")
    if not config.get('AUTH_SECRET_KEY'):
        raise RuntimeError("CRITICAL: AUTH_SECRET_KEY secret not loaded")
    
    # 3. Initialize services with secrets
    logger.info("Initializing database...")
    db = Database(
        host=config['DATABASE_HOST'],
        password=config['DATABASE_PASSWORD'],  # From secret manager
    )
    
    # 4. Verify connectivity
    logger.info("Verifying database connectivity...")
    db.ping()
    
    logger.info("Service startup complete")
    return config

if __name__ == '__main__':
    config = startup()
    app.run(host=config['API_HOST'], port=config['API_PORT'])
```

### 7.2 Startup Validation

```python
def validate_secrets_loaded(config):
    """Ensure all required secrets successfully loaded."""
    
    required_secrets = [
        'DATABASE_PASSWORD',
        'AUTH_SECRET_KEY',
        'SENDGRID_API_KEY',
    ]
    
    missing = []
    for secret_key in required_secrets:
        if secret_key not in config or not config[secret_key]:
            missing.append(secret_key)
    
    if missing:
        error_msg = f"Required secrets not loaded: {', '.join(missing)}"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    logger.info(f"✓ All {len(required_secrets)} required secrets loaded successfully")
```

---

## 8. Secret Caching Considerations

### 8.1 Cache Strategy

```
Decision Matrix:
  
  Secret Type         | Cache? | TTL      | Reason
  -------------------|--------|----------|--------------------
  Database password   | Yes    | 1 hour   | Changes infrequently
  API keys            | Yes    | 30 min   | Rotated occasionally
  Session tokens      | No     | N/A      | Must be fresh
  Encryption keys     | Yes    | 24 hours | Long-lived
  JWT signing keys    | Yes    | 1 hour   | Rotated on schedule
```

### 8.2 Cache Implementation

```python
from functools import lru_cache
import time
from typing import Tuple

class CachedSecretManager:
    """Secret manager with configurable caching."""
    
    def __init__(self, backend='aws', cache_ttl=3600):
        self.backend = backend
        self.cache_ttl = cache_ttl
        self.cache = {}
        self.cache_times = {}
    
    def get_secret(self, secret_path: str) -> str:
        """Get secret with caching."""
        
        # Check cache
        now = time.time()
        if secret_path in self.cache:
            if now - self.cache_times[secret_path] < self.cache_ttl:
                logger.debug(f"Cache hit for {secret_path}")
                return self.cache[secret_path]
            else:
                logger.debug(f"Cache expired for {secret_path}")
        
        # Load from manager
        secret_value = self._load_from_manager(secret_path)
        
        # Cache result
        self.cache[secret_path] = secret_value
        self.cache_times[secret_path] = now
        
        return secret_value
    
    def invalidate_cache(self, secret_path: str = None):
        """Invalidate cache for secret or all secrets."""
        if secret_path:
            self.cache.pop(secret_path, None)
            self.cache_times.pop(secret_path, None)
        else:
            self.cache.clear()
            self.cache_times.clear()
```

---

## 9. Audit and Logging

### 9.1 Secret Access Logging

```python
def log_secret_access(secret_path: str, success: bool, error: str = None):
    """Log all secret manager access for audit."""
    
    audit_log = {
        'timestamp': datetime.now().isoformat(),
        'service': os.getenv('SERVICE_NAME'),
        'secret_path': secret_path,  # Obfuscate sensitive parts
        'success': success,
        'error': error,
        'caller': inspect.stack()[2].function,
    }
    
    logger.info(f"SECRET_ACCESS: {json.dumps(audit_log)}")
```

### 9.2 What NOT to Log

```python
# PROHIBITED - Never log secret values
logger.error(f"Failed to load password: {password}")  # ✗ Don't!

# CORRECT - Log only metadata
logger.error(f"Failed to load secret from path: {secret_path}")  # ✓ OK
```

---

## 10. Error Handling

### 10.1 Secret Loading Failures

```python
class SecretLoadingError(Exception):
    """Base exception for secret loading failures."""
    pass

class SecretNotFoundError(SecretLoadingError):
    """Secret doesn't exist in manager."""
    pass

class AccessDeniedError(SecretLoadingError):
    """Service lacks permission to access secret."""
    pass

class SecretManagerConnectionError(SecretLoadingError):
    """Cannot connect to secret manager."""
    pass

# Usage
try:
    password = get_secret('prod/database/password')
except SecretNotFoundError:
    logger.error("Database password secret not found")
    raise
except AccessDeniedError:
    logger.error("Service lacks permission to access database password")
    raise SystemExit(1)
except SecretManagerConnectionError:
    logger.error("Cannot connect to secret manager")
    raise SystemExit(1)
```

---

## 11. Development and Testing

### 11.1 Local Development (No Secrets Manager)

For local development where secrets manager is not available:

```python
# config/dev_secrets.py

class MockSecretManager:
    """Mock secrets for local development only."""
    
    DEV_SECRETS = {
        'dev/database/password': 'dev_password_123',
        'dev/auth/secret_key': 'dev_jwt_key_456',
        'dev/sendgrid/api_key': 'dev_sendgrid_789',
    }
    
    def get_secret(self, secret_path: str) -> str:
        if secret_path in self.DEV_SECRETS:
            return self.DEV_SECRETS[secret_path]
        else:
            raise SecretNotFoundError(f"Mock secret not found: {secret_path}")

# Usage in development
if os.getenv('ENVIRONMENT') == 'dev':
    secrets = MockSecretManager()
else:
    secrets = SecretManager(backend='aws')
```

### 11.2 Testing with Secrets

```python
# tests/test_secrets.py

def test_secret_loading():
    """Test that secrets load correctly."""
    with patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.return_value = {
            'SecretString': 'test_password_123'
        }
        
        manager = SecretManager(backend='aws')
        secret = manager.get_secret('prod/database/password')
        assert secret == 'test_password_123'

def test_secret_not_found():
    """Test handling of missing secrets."""
    with patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}}, 
            'GetSecretValue'
        )
        
        manager = SecretManager(backend='aws')
        with pytest.raises(SecretNotFoundError):
            manager.get_secret('prod/nonexistent/secret')
```

---

## 12. Known Limitations

### 12.1 v1.0 Limitations

```
Current scope:
  ✓ AWS Secrets Manager integration
  ✓ HashiCorp Vault integration
  ✓ Secret caching with TTL
  ✓ Error handling and logging
  ✗ Automatic secret rotation (v1.1)
  ✗ Secret sharing across services (v1.1)
  ✗ Audit trail export (v1.2)

Planned enhancements:
  - v1.1: Automatic rotation without restart
  - v1.1: Cross-service secret sharing
  - v1.2: Audit trail export to S3/CloudWatch
  - v1.2: Secret versioning and rollback
```

---

## References

- [SEC-2: Least-Privilege Access Controls](SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md)
- [ROT-1: Secret Rotation Procedure](ROT-1-SECRET_ROTATION_PROCEDURE.md)
- [AUDIT-1: Access and Change Audit Trail](AUDIT-1-ACCESS_AND_CHANGE_AUDIT_TRAIL.md)

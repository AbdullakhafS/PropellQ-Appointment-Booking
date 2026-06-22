# SEC-1: Secret Manager Integration Pattern

**Status:** Published | **Version:** 1.0 | **Date:** 2026-06-22

---

## 1. Overview

Define standard secret loading path from approved secret manager, removing plaintext secret patterns from service bootstrap.

**Principles:**
- Secrets never in source control
- Only approved managers accepted
- Plaintext only in memory
- Service identity-based access

---

## 2. Approved Secret Managers

| Manager | Cloud | Pattern | Status |
|---|---|---|---|
| AWS Secrets Manager | AWS | `aws-secretsmanager://secret-name` | ✅ Production |
| Azure Key Vault | Azure | `azurekv://vault/secret-name` | ✅ Production |
| HashiCorp Vault | Multi | `vault://path/to/secret` | ✅ Production |

---

## 3. Secret Loading Pattern

### 3.1 Bootstrap Flow

```
Service starts
  ↓
Load service identity (IAM role, certificate)
  ↓
Authenticate with Secret Manager
  ↓
Fetch required secrets:
  ├─ DATABASE_PASSWORD
  ├─ API_KEY
  └─ JWT_SECRET
  ↓
Secrets loaded into memory (plaintext only here)
  ↓
Service ready to use secrets from memory
  
** Key: Never write secrets to disk or config files **
```

### 3.2 C# Implementation

```csharp
public static class SecretManagerExtensions
{
    public static IConfigurationBuilder AddSecretsManager(
        this IConfigurationBuilder builder,
        string environment)
    {
        // Use AWS Secrets Manager in production
        if (environment == "production")
        {
            var secretsManager = new SecretsManager(
                "us-east-1",
                assumeRoleArn: "arn:aws:iam::ACCOUNT:role/booking-service"
            );
            
            builder.AddInMemoryCollection(
                secretsManager.LoadSecrets(
                    $"booking-service/{environment}"
                )
            );
        }
        // Use local .env for development
        else
        {
            builder.AddUserSecrets<Program>();
        }
        
        return builder;
    }
}

// Secrets Manager wrapper
public class SecretsManager
{
    private readonly IAmazonSecretsManager _client;
    private readonly Dictionary<string, string> _cache;
    
    public Dictionary<string, string> LoadSecrets(string secretPath)
    {
        try
        {
            var secretValue = _client.GetSecretValueAsync(
                new GetSecretValueRequest { SecretId = secretPath }
            ).Result;
            
            // Parse JSON secret: {"DB_PASSWORD": "...", "API_KEY": "..."}
            var secrets = JsonConvert.DeserializeObject<Dictionary<string, string>>(
                secretValue.SecretString
            );
            
            _cache = secrets;
            return secrets;
        }
        catch (ResourceNotFoundException)
        {
            throw new ConfigurationException($"Secret not found: {secretPath}");
        }
    }
}
```

### 3.3 TypeScript Implementation

```typescript
import * as AWS from 'aws-sdk';

class SecretsManager {
  private client = new AWS.SecretsManager();
  private cache: Record<string, string> = {};
  
  async loadSecrets(secretPath: string): Promise<Record<string, string>> {
    try {
      const response = await this.client
        .getSecretValue({ SecretId: secretPath })
        .promise();
      
      if (!response.SecretString) {
        throw new Error('Secret is binary');
      }
      
      this.cache = JSON.parse(response.SecretString);
      return this.cache;
    } catch (error) {
      throw new Error(`Failed to load secret ${secretPath}: ${error.message}`);
    }
  }
  
  getSecret(key: string): string {
    if (!this.cache[key]) {
      throw new Error(`Secret not loaded: ${key}`);
    }
    return this.cache[key];
  }
}

export async function initializeConfiguration() {
  const environment = process.env.ENVIRONMENT || 'development';
  
  if (environment === 'production') {
    const sm = new SecretsManager();
    await sm.loadSecrets(`booking-service/${environment}`);
  } else {
    // Use .env files for local development
    require('dotenv').config({ path: '.env.local' });
  }
}
```

---

## 4. Secret Path Convention

```
AWS Secrets Manager:
  booking-service/production/database_password
  booking-service/production/oauth_client_secret
  booking-service/staging/database_password
  
Structure:
  service/{environment}/{secret-name}
  
Format: snake_case for consistency
```

---

## 5. Hardcoded Secret Detection

```bash
# Pre-commit hook to catch hardcoded secrets
#!/bin/bash

# Scan for patterns that look like secrets
git diff --cached | grep -E '(password|secret|key|token).*=' && {
  echo "❌ ERROR: Potential hardcoded secret found in staged changes"
  echo "Use secret manager instead"
  exit 1
}

# Check for common secret patterns
git diff --cached | grep -E 'sk_[a-zA-Z0-9]{20,}|pk_[a-zA-Z0-9]{20,}' && {
  echo "❌ ERROR: AWS key pattern detected"
  exit 1
}

exit 0
```

---

## 6. Failure Modes

| Scenario | Action |
|---|---|
| Secret manager unavailable | Fail startup with clear error |
| Secret not found | Fail startup with helpful message |
| Invalid credentials | Fail startup, check IAM permissions |
| Timeout | Retry with exponential backoff |

---

## References

- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/
- Azure Key Vault: https://learn.microsoft.com/en-us/azure/key-vault/
- Vault: https://www.vaultproject.io/

**Next:** [SEC-2: Least-Privilege Secret Access Controls](sec-access-controls.md)

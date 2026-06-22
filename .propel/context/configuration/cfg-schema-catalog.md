# CFG-1: Configuration Schema and Catalog

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects

---

## 1. Overview

This document defines the standardized configuration schema and environment catalog for all services, ensuring consistent, discoverable, and validated configuration across environments.

**Principles:**
- All configuration is explicitly cataloged
- Schema defines required vs optional keys
- Non-secret configuration is documented
- Catalog drives validation and defaults

---

## 2. Configuration Taxonomy

### 2.1 Configuration Types

| Type | Storage | Sensitive | Example |
|---|---|---|---|
| **Feature Flags** | Git-tracked config | ❌ No | debug_logging: true |
| **Environment Vars** | Git-tracked template | ❌ No | log_level: INFO |
| **Secrets** | Secret manager | ✅ Yes | database_password |
| **Compliance Rules** | Git-tracked schema | ❌ No | require_tls: true |
| **Feature Config** | Dynamic config service | ❌ No | max_booking_size: 100 |

---

## 3. Global Configuration Schema

### 3.1 Common Configuration Keys

```yaml
# config-schema.yaml
ConfigurationSchema:
  Version: "1.0"
  LastUpdated: "2026-06-22"
  
  Global:
    # Application identity
    SERVICE_NAME:
      Type: string
      Required: true
      Pattern: "^[a-z][a-z0-9-]*$"
      Examples:
        - booking-service
        - payment-gateway
        - search-service
      
    SERVICE_VERSION:
      Type: string
      Required: true
      Pattern: "^\\d+\\.\\d+\\.\\d+(-[a-z0-9]+)?$"
      Examples:
        - "1.0.0"
        - "1.2.3-beta.1"
    
    # Execution environment
    ENVIRONMENT:
      Type: enum
      Values: [development, staging, production]
      Required: true
      Description: "Deployment target environment"
    
    # Logging
    LOG_LEVEL:
      Type: enum
      Values: [DEBUG, INFO, WARN, ERROR]
      Required: true
      Default: "INFO"
      Overridable: true  # Can be changed at runtime
    
    LOG_FORMAT:
      Type: enum
      Values: [json, text]
      Required: false
      Default: "json"
    
    # Server
    HTTP_PORT:
      Type: integer
      Min: 1024
      Max: 65535
      Required: false
      Default: 8080
      Overridable: false
    
    # Observability
    TRACE_ENABLED:
      Type: boolean
      Required: false
      Default: false
      Overridable: true
    
    METRICS_ENABLED:
      Type: boolean
      Required: false
      Default: true
      Overridable: false

  Database:
    DB_HOST:
      Type: string
      Required: true
      Sensitive: false
      Examples:
        - "localhost"
        - "postgres.default.svc.cluster.local"
        - "db.myregion.rds.amazonaws.com"
    
    DB_PORT:
      Type: integer
      Min: 1024
      Max: 65535
      Required: false
      Default: 5432
    
    DB_NAME:
      Type: string
      Required: true
      Pattern: "^[a-z][a-z0-9_]*$"
      Examples:
        - "appointment_booking"
        - "user_db"
    
    DB_USER:
      Type: string
      Required: true
      Sensitive: false
      Examples:
        - "service_account"
        - "booking_svc"
    
    DB_PASSWORD:
      Type: string
      Required: true
      Sensitive: true  # Loaded from secret manager
      MinLength: 12
    
    DB_POOL_SIZE:
      Type: integer
      Min: 1
      Max: 100
      Required: false
      Default: 10
    
    DB_CONNECTION_TIMEOUT:
      Type: integer
      Unit: seconds
      Min: 1
      Max: 60
      Required: false
      Default: 10
    
    DB_SSL_ENABLED:
      Type: boolean
      Required: false
      Default: true

  Cache:
    CACHE_BACKEND:
      Type: enum
      Values: [redis, memcached, in-memory]
      Required: false
      Default: "redis"
    
    CACHE_HOST:
      Type: string
      Required: false
      Examples:
        - "localhost"
        - "redis.default.svc.cluster.local"
    
    CACHE_PORT:
      Type: integer
      Default: 6379
      Required: false
    
    CACHE_TTL:
      Type: integer
      Unit: seconds
      Min: 1
      Max: 86400  # 1 day
      Required: false
      Default: 3600

  Auth:
    AUTH_PROVIDER:
      Type: enum
      Values: [oauth2, jwt, ldap, none]
      Required: true
    
    OAUTH_CLIENT_ID:
      Type: string
      Required: "{{ .AUTH_PROVIDER == 'oauth2' }}"
      Sensitive: false
    
    OAUTH_CLIENT_SECRET:
      Type: string
      Required: "{{ .AUTH_PROVIDER == 'oauth2' }}"
      Sensitive: true
    
    JWT_SECRET:
      Type: string
      Required: "{{ .AUTH_PROVIDER == 'jwt' }}"
      Sensitive: true
      MinLength: 32

  External APIs:
    PAYMENT_API_URL:
      Type: string
      Pattern: "^https?://"
      Required: false
      Examples:
        - "https://api.stripe.com"
        - "https://api-sandbox.stripe.com"
    
    PAYMENT_API_KEY:
      Type: string
      Required: "{{ defined(PAYMENT_API_URL) }}"
      Sensitive: true
      MinLength: 20
```

---

## 4. Environment Catalog

### 4.1 Environment Definitions

```yaml
# environments-catalog.yaml
environments:
  development:
    description: "Local development environment"
    traits:
      - ephemeral
      - unsafe-to-use-for-real-data
    database:
      host: localhost
      port: 5432
    cache:
      enabled: false
    logging:
      level: DEBUG
      pretty_print: true
    auth:
      provider: oauth2
      skip_validation: true  # For local testing
  
  staging:
    description: "Pre-production environment"
    traits:
      - persistent
      - ok-to-test-with-safe-data
    database:
      host: "postgres-staging.internal"
      ssl_enabled: true
    cache:
      enabled: true
      backend: redis
    logging:
      level: INFO
      pretty_print: false
    auth:
      provider: oauth2
      skip_validation: false
  
  production:
    description: "Production environment"
    traits:
      - mission-critical
      - real-customer-data
    database:
      host: "postgres-prod.internal"
      ssl_enabled: true
      replica_read: true
    cache:
      enabled: true
      backend: redis
      replicated: true
    logging:
      level: WARN
      pretty_print: false
    auth:
      provider: oauth2
      skip_validation: false
      enforce_mfa: true
```

---

## 5. Service-Specific Configuration

### 5.1 Booking Service Config

```yaml
# booking-service-schema.yaml
ServiceName: booking-service

RequiredKeys:
  - SERVICE_NAME
  - SERVICE_VERSION
  - ENVIRONMENT
  - DB_HOST
  - DB_NAME
  - DB_USER
  - DB_PASSWORD
  - AUTH_PROVIDER
  - OAUTH_CLIENT_ID
  - OAUTH_CLIENT_SECRET

OptionalKeys:
  - LOG_LEVEL: INFO
  - CACHE_BACKEND: redis
  - TRACE_ENABLED: false
  - METRICS_ENABLED: true

ServiceSpecific:
  BOOKING_MAX_SIZE:
    Type: integer
    Min: 1
    Max: 1000
    Default: 100
    Description: "Maximum appointment duration in minutes"
  
  BOOKING_CANCELLATION_WINDOW:
    Type: integer
    Unit: hours
    Min: 0
    Max: 720  # 30 days
    Default: 24
    Description: "Hours before appointment to allow cancellation"
  
  PAYMENT_RETRY_MAX:
    Type: integer
    Min: 1
    Max: 10
    Default: 3
    Description: "Maximum payment retry attempts"
  
  NOTIFICATION_QUEUE:
    Type: string
    Required: true
    Examples:
      - "sqs://booking-notifications-dev"
      - "sqs://booking-notifications-prod"
```

---

## 6. Configuration Template Files

### 6.1 Non-Secret Template (Git-Tracked)

```bash
# .env.example
# This file is checked into version control
# Copy to .env and fill in values for local development

# Global
SERVICE_NAME=booking-service
SERVICE_VERSION=1.0.0
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=appointment_booking
DB_USER=postgres
DB_PASSWORD=CHANGE_ME_IN_.ENV_LOCAL  # Do NOT commit real password
DB_POOL_SIZE=10
DB_SSL_ENABLED=false

# Cache
CACHE_BACKEND=redis
CACHE_HOST=localhost
CACHE_PORT=6379
CACHE_TTL=3600

# Auth
AUTH_PROVIDER=oauth2
OAUTH_CLIENT_ID=dev-client-id
OAUTH_CLIENT_SECRET=CHANGE_ME_IN_.ENV_LOCAL  # Secret loaded from manager in prod

# External APIs
PAYMENT_API_URL=https://api-sandbox.stripe.com
PAYMENT_API_KEY=CHANGE_ME_IN_.ENV_LOCAL

# Business Logic
BOOKING_MAX_SIZE=100
BOOKING_CANCELLATION_WINDOW=24
PAYMENT_RETRY_MAX=3
```

### 6.2 Secret Template (NOT Git-Tracked)

```bash
# .env.local (NOT in git)
# Local development secrets
# Never commit this file

DB_PASSWORD=dev-postgres-password
OAUTH_CLIENT_SECRET=dev-oauth-secret-12345
PAYMENT_API_KEY=sk_test_sandbox_key_12345
JWT_SECRET=dev-jwt-secret-min-32-chars-long-key-here
```

---

## 7. Configuration Discovery and Validation

### 7.1 Schema Registry

```json
{
  "schemaRegistry": {
    "version": "1.0",
    "services": [
      {
        "name": "booking-service",
        "schemaFile": "config/booking-service-schema.yaml",
        "schemaVersion": "1.2.3",
        "lastUpdated": "2026-06-22",
        "maintainer": "backend-team",
        "documentation": "https://wiki/config/booking-service"
      },
      {
        "name": "search-service",
        "schemaFile": "config/search-service-schema.yaml",
        "schemaVersion": "1.0.0",
        "lastUpdated": "2026-06-20",
        "maintainer": "search-team"
      }
    ]
  }
}
```

### 7.2 Configuration Loader (C#)

```csharp
public class ConfigurationCatalog
{
    private readonly IConfigurationRoot _config;
    private readonly ILogger<ConfigurationCatalog> _logger;
    private readonly ConfigurationSchema _schema;
    
    public ConfigurationCatalog(
        IConfiguration config,
        ILogger<ConfigurationCatalog> logger)
    {
        _config = config;
        _logger = logger;
        _schema = LoadSchema();
    }
    
    public async Task<Configuration> LoadAsync()
    {
        var requiredKeys = _schema.RequiredKeys;
        var missingKeys = new List<string>();
        
        foreach (var key in requiredKeys)
        {
            var value = _config[key];
            if (string.IsNullOrEmpty(value))
            {
                missingKeys.Add(key);
            }
        }
        
        if (missingKeys.Any())
        {
            throw new ConfigurationException(
                $"Missing required configuration keys: {string.Join(", ", missingKeys)}"
            );
        }
        
        // Load and validate
        var config = new Configuration();
        ValidateConfiguration(config);
        return config;
    }
    
    private void ValidateConfiguration(Configuration config)
    {
        foreach (var schema in _schema.Keys)
        {
            var value = _config[schema.Name];
            
            // Type validation
            if (!TryParseType(value, schema.Type, out var parsed))
            {
                throw new ConfigurationException(
                    $"Configuration '{schema.Name}' has invalid type. " +
                    $"Expected {schema.Type}, got {value?.GetType().Name ?? "null"}"
                );
            }
            
            // Range validation
            if (schema.Min.HasValue && parsed < schema.Min)
            {
                throw new ConfigurationException(
                    $"Configuration '{schema.Name}' value {parsed} is below minimum {schema.Min}"
                );
            }
        }
    }
}
```

### 7.3 Configuration Loader (TypeScript)

```typescript
import { z } from 'zod';

const configSchema = z.object({
  SERVICE_NAME: z.string().min(1),
  SERVICE_VERSION: z.string().regex(/^\d+\.\d+\.\d+/),
  ENVIRONMENT: z.enum(['development', 'staging', 'production']),
  DB_HOST: z.string().min(1),
  DB_NAME: z.string().regex(/^[a-z][a-z0-9_]*$/),
  DB_USER: z.string().min(1),
  DB_PASSWORD: z.string().min(12),
  LOG_LEVEL: z.enum(['DEBUG', 'INFO', 'WARN', 'ERROR']).default('INFO'),
});

export type Configuration = z.infer<typeof configSchema>;

export function loadConfiguration(): Configuration {
  const parsed = configSchema.safeParse(process.env);
  
  if (!parsed.success) {
    const errors = parsed.error.errors
      .map(e => `${e.path.join('.')}: ${e.message}`)
      .join('\n');
    
    throw new Error(`Configuration validation failed:\n${errors}`);
  }
  
  return parsed.data;
}
```

---

## 8. Testing Configuration Loading

### 8.1 Unit Test

```csharp
[TestClass]
public class ConfigurationTests
{
    [TestMethod]
    public async Task LoadConfiguration_MissingRequired_ThrowsException()
    {
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string>
            {
                { "SERVICE_NAME", "booking-service" },
                // Missing DB_HOST, DB_NAME, etc.
            })
            .Build();
        
        var logger = new Mock<ILogger<ConfigurationCatalog>>();
        var catalog = new ConfigurationCatalog(config, logger.Object);
        
        await Assert.ThrowsExceptionAsync<ConfigurationException>(
            () => catalog.LoadAsync()
        );
    }
    
    [TestMethod]
    public async Task LoadConfiguration_ValidConfig_Succeeds()
    {
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string>
            {
                { "SERVICE_NAME", "booking-service" },
                { "DB_HOST", "localhost" },
                { "DB_NAME", "test_db" },
                { "DB_USER", "test_user" },
                { "DB_PASSWORD", "test_pass_12345" },
            })
            .Build();
        
        var logger = new Mock<ILogger<ConfigurationCatalog>>();
        var catalog = new ConfigurationCatalog(config, logger.Object);
        
        var loaded = await catalog.LoadAsync();
        Assert.IsNotNull(loaded);
    }
}
```

---

## 9. Success Criteria

- [ ] Configuration schema defined for all services
- [ ] Environment catalog published
- [ ] Non-secret template (.env.example) checked into git
- [ ] Configuration discovery system operational
- [ ] Validation tests passing
- [ ] Documentation with examples
- [ ] Service-specific schema catalogs defined

---

## References

- 12-Factor App - Config: https://12factor.net/config
- OWASP: Configuration Security: https://cheatsheetseries.owasp.org/

**Next:** [CFG-2: Precedence and Resolution Rules](cfg-precedence-rules.md)

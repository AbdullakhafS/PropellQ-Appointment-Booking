# CFG-1: Configuration Schema and Catalog

**Author**: Architecture Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines the standardized configuration schema, required configuration keys by service/environment, and the non-secret template format for local/dev bootstrap. This ensures all services have a deterministic, auditable configuration baseline.

---

## 2. Configuration Scope and Governance

### 2.1 Configuration Categories

All configuration falls into one of these categories:

| Category | Definition | Example | Storage | Human-Editable |
|----------|-----------|---------|---------|-----------------|
| **Runtime Constants** | Immutable application parameters | `MAX_BOOKING_SLOTS=100`, `API_TIMEOUT_MS=5000` | Environment variable or config file | Yes (with validation) |
| **Derived Values** | Computed from other config | `DATABASE_POOL_SIZE=MAX(2, CPU_CORES * 2)` | Code or config file | No (computed) |
| **Secrets** | Sensitive data requiring protection | Database password, API keys | Secret manager only | No (never in code) |
| **Feature Flags** | Boolean toggles for features | `ENABLE_SMS_NOTIFICATIONS=true` | Feature flag service | Yes (with governance) |
| **Runtime Tuning** | Performance parameters | `CACHE_TTL_SECONDS=3600` | Environment variable | Yes (with safety limits) |

### 2.2 Service Inventory

| Service | Type | Config Keys | Secrets | Environments |
|---------|------|-------------|---------|--------------|
| web_app | FastAPI backend | 15 | 8 | dev, staging, prod |
| booking_service | Business logic | 12 | 6 | dev, staging, prod |
| search_service | Query engine | 10 | 4 | dev, staging, prod |
| notification_service | Async messaging | 8 | 5 | staging, prod |
| admin_dashboard | Web frontend | 6 | 2 | dev, staging, prod |

---

## 3. Required Configuration Schema by Service

### 3.1 Web App (web_app) - 23 Total Keys

#### Required Keys (Startup Blocking)

```yaml
# Database connectivity
DATABASE_HOST: 
  type: string
  required: true
  env_var: DATABASE_HOST
  description: "PostgreSQL host (e.g., db.example.com or localhost:5432)"
  validation: "hostname|IP + port"
  
DATABASE_PORT:
  type: integer
  required: true
  env_var: DATABASE_PORT
  default: 5432
  validation: "port range 1-65535"
  
DATABASE_NAME:
  type: string
  required: true
  env_var: DATABASE_NAME
  description: "Database name (e.g., propellq_prod)"
  validation: "alphanumeric + underscore"

# API Server Configuration
API_PORT:
  type: integer
  required: true
  env_var: API_PORT
  default_dev: 8000
  default_prod: 8080
  validation: "port range 1-65535"
  
API_HOST:
  type: string
  required: true
  env_var: API_HOST
  default: "0.0.0.0"
  validation: "IP address or hostname"

# Authentication
AUTH_SECRET_KEY:
  type: secret
  required: true
  secret_path: "app/auth/secret_key"
  description: "JWT signing key (32+ bytes)"
  rotation_frequency: "90 days"
  
# Environment Identifier
ENVIRONMENT:
  type: enum
  required: true
  env_var: ENVIRONMENT
  allowed_values: ["dev", "staging", "prod"]
  validation: "must match deployment environment"
```

#### Optional Keys (Non-Blocking)

```yaml
# Logging Configuration
LOG_LEVEL:
  type: enum
  required: false
  env_var: LOG_LEVEL
  default: "INFO"
  allowed_values: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
  
LOG_FORMAT:
  type: enum
  required: false
  env_var: LOG_FORMAT
  default: "json"
  allowed_values: ["json", "text"]

# Performance Tuning
API_TIMEOUT_MS:
  type: integer
  required: false
  env_var: API_TIMEOUT_MS
  default: 30000
  validation: "500-300000"
  
DATABASE_POOL_SIZE:
  type: integer
  required: false
  env_var: DATABASE_POOL_SIZE
  default: 10
  validation: "2-100"

# Feature Flags
ENABLE_ANALYTICS:
  type: boolean
  required: false
  env_var: ENABLE_ANALYTICS
  default_dev: false
  default_prod: true
```

#### Secret Keys (Always from Secret Manager)

```yaml
DATABASE_PASSWORD:
  type: secret
  required: true
  secret_path: "prod/database/master_password"
  backup_paths:
    - "prod/database/master_password_prev"
  rotation_frequency: "180 days"
  description: "PostgreSQL database password"

REDIS_PASSWORD:
  type: secret
  required: true
  secret_path: "prod/redis/auth_token"
  rotation_frequency: "90 days"

AWS_ACCESS_KEY_ID:
  type: secret
  required: false
  secret_path: "prod/aws/access_key"
  rotation_frequency: "90 days"

AWS_SECRET_ACCESS_KEY:
  type: secret
  required: false
  secret_path: "prod/aws/secret_key"
  rotation_frequency: "90 days"

SENDGRID_API_KEY:
  type: secret
  required: false
  secret_path: "prod/sendgrid/api_key"
  rotation_frequency: "60 days"

TWILIO_ACCOUNT_SID:
  type: secret
  required: false
  secret_path: "prod/twilio/account_sid"
  rotation_frequency: "120 days"

TWILIO_AUTH_TOKEN:
  type: secret
  required: false
  secret_path: "prod/twilio/auth_token"
  rotation_frequency: "120 days"
```

### 3.2 Booking Service - 18 Total Keys

#### Required Keys

```yaml
SERVICE_NAME:
  type: string
  required: true
  env_var: SERVICE_NAME
  default: "booking_service"

SERVICE_PORT:
  type: integer
  required: true
  env_var: SERVICE_PORT
  default: 8001
  
DATABASE_HOST:
  type: string
  required: true
  env_var: DATABASE_HOST

DATABASE_NAME:
  type: string
  required: true
  env_var: DATABASE_NAME

MAX_CONCURRENT_BOOKINGS:
  type: integer
  required: true
  env_var: MAX_CONCURRENT_BOOKINGS
  default: 100
  validation: "10-1000"

ENVIRONMENT:
  type: enum
  required: true
  env_var: ENVIRONMENT
  allowed_values: ["dev", "staging", "prod"]
```

#### Secrets

```yaml
DATABASE_PASSWORD:
  type: secret
  required: true
  secret_path: "prod/database/service_password"
  
SERVICE_API_KEY:
  type: secret
  required: true
  secret_path: "prod/booking/service_api_key"
  rotation_frequency: "90 days"
```

### 3.3 Search Service - 16 Total Keys

#### Required Keys

```yaml
ELASTICSEARCH_HOST:
  type: string
  required: true
  env_var: ELASTICSEARCH_HOST

ELASTICSEARCH_PORT:
  type: integer
  required: true
  env_var: ELASTICSEARCH_PORT
  default: 9200

SEARCH_INDEX_PREFIX:
  type: string
  required: true
  env_var: SEARCH_INDEX_PREFIX
  default: "propellq_"
  validation: "alphanumeric + underscore"

SEARCH_TIMEOUT_MS:
  type: integer
  required: true
  env_var: SEARCH_TIMEOUT_MS
  default: 5000
  validation: "100-30000"

ENVIRONMENT:
  type: enum
  required: true
  env_var: ENVIRONMENT
  allowed_values: ["dev", "staging", "prod"]
```

#### Secrets

```yaml
ELASTICSEARCH_PASSWORD:
  type: secret
  required: true
  secret_path: "prod/elasticsearch/password"
```

---

## 4. Environment-Specific Defaults

### 4.1 Development Environment

```yaml
ENVIRONMENT: dev
LOG_LEVEL: DEBUG
LOG_FORMAT: text
API_TIMEOUT_MS: 30000
DATABASE_POOL_SIZE: 5
ENABLE_ANALYTICS: false
ENABLE_SMS_NOTIFICATIONS: false
CACHE_TTL_SECONDS: 60

# Development uses local/ephemeral resources
DATABASE_HOST: localhost
DATABASE_PORT: 5432
REDIS_HOST: localhost
REDIS_PORT: 6379
ELASTICSEARCH_HOST: localhost
ELASTICSEARCH_PORT: 9200
```

### 4.2 Staging Environment

```yaml
ENVIRONMENT: staging
LOG_LEVEL: INFO
LOG_FORMAT: json
API_TIMEOUT_MS: 15000
DATABASE_POOL_SIZE: 20
ENABLE_ANALYTICS: true
ENABLE_SMS_NOTIFICATIONS: true
CACHE_TTL_SECONDS: 3600

# Staging uses production-like infrastructure
DATABASE_HOST: staging-db.internal
REDIS_HOST: staging-redis.internal
ELASTICSEARCH_HOST: staging-es.internal
```

### 4.3 Production Environment

```yaml
ENVIRONMENT: prod
LOG_LEVEL: WARNING
LOG_FORMAT: json
API_TIMEOUT_MS: 8000
DATABASE_POOL_SIZE: 50
ENABLE_ANALYTICS: true
ENABLE_SMS_NOTIFICATIONS: true
CACHE_TTL_SECONDS: 7200

# Production uses managed services
DATABASE_HOST: prod-db.rds.amazonaws.com
REDIS_HOST: prod-redis.elasticache.amazonaws.com
ELASTICSEARCH_HOST: prod-es.amazonaws.com
```

---

## 5. Configuration Template Format

### 5.1 Non-Secret Template (.env.template)

This template contains only non-secret configuration and serves as the bootstrap for developers:

```bash
# Web App Configuration Template
# Copy this to .env and fill in local values for development

# ==================== REQUIRED KEYS ====================
# These keys MUST be set before startup

# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=propellq_dev

# API Server
API_PORT=8000
API_HOST=0.0.0.0

# Environment Identifier
ENVIRONMENT=dev

# ==================== OPTIONAL KEYS ====================
# These keys have sensible defaults but can be overridden

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Performance Tuning
API_TIMEOUT_MS=30000
DATABASE_POOL_SIZE=10
CACHE_TTL_SECONDS=60

# Features
ENABLE_ANALYTICS=false
ENABLE_SMS_NOTIFICATIONS=false

# ==================== SECRETS ====================
# DO NOT fill these in .env.template
# Secrets are loaded from secret manager at runtime
# See SEC-1 for secret loading patterns

# DATABASE_PASSWORD=*** from secret manager
# AUTH_SECRET_KEY=*** from secret manager
# AWS_ACCESS_KEY_ID=*** from secret manager
# etc.
```

### 5.2 Local Development Bootstrap

```bash
#!/bin/bash
# bootstrap-dev.sh - Set up local development configuration

set -e

# Create .env from template
cp .env.template .env

# Prompt developer for environment-specific values
read -p "Database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}
sed -i "s/DATABASE_HOST=.*/DATABASE_HOST=$DB_HOST/" .env

read -p "API Port [8000]: " API_PORT
API_PORT=${API_PORT:-8000}
sed -i "s/API_PORT=.*/API_PORT=$API_PORT/" .env

# Load secrets from local secret manager for development
# (or generate test secrets if not available)
echo "Loading secrets from local development secret manager..."
source scripts/load-dev-secrets.sh

echo "✓ Development configuration ready"
echo "✓ Start server with: python app/server.py"
```

---

## 6. Configuration Validation During Schema Definition

### 6.1 Schema Validation Rules

Each configuration key must satisfy:

```yaml
Validation Checklist:
  - [ ] Type defined (string, integer, boolean, enum, secret)
  - [ ] Required flag specified (true/false)
  - [ ] Default value specified OR marked required
  - [ ] Validation rules defined (regex, range, enum, etc.)
  - [ ] For secrets: rotation frequency documented
  - [ ] For secrets: backup paths defined
  - [ ] Conflict detection: no overlapping env var names
  - [ ] Dependency detection: key X requires key Y documented
  - [ ] Access documented: which service/role reads this
```

### 6.2 Key Naming Convention

```
PATTERN: {SERVICE}_{CATEGORY}_{NAME}

Examples:
  DATABASE_HOST           (global service)
  BOOKING_SERVICE_TIMEOUT (service-specific)
  ENABLE_SMS_NOTIFICATIONS (feature flag)
  ELASTICSEARCH_PASSWORD   (credentials)
  
Prohibited:
  - UNDEFINED_KEY (must have documented schema)
  - temp_config (temp values not allowed)
  - CONFIG_* (reserved prefix for framework)
  - SECRET_* (use secret_path, not env var)
```

---

## 7. Schema Versioning and Change Management

### 7.1 Schema Version Tracking

```yaml
schema_version: "1.0"
last_updated: "2026-06-22"
compatibility_notes: |
  This is the initial schema version for all services.
  
  Breaking changes (major version bump):
    - Removing required key
    - Changing key data type
    - Renaming existing key
    
  Non-breaking changes (minor version bump):
    - Adding optional key
    - Expanding enum values
    - Relaxing validation constraints

changelog:
  - version: "1.0"
    date: "2026-06-22"
    changes:
      - "Initial schema definition"
      - "5 services documented"
      - "23 web_app keys, 18 booking keys, 16 search keys"
      - "Secrets guidance for all services"
```

### 7.2 Schema Change Approval Process

All schema changes require approval:

```yaml
Change Process:
  1. Propose change in PR with justification
  2. Update CFG-1 schema document
  3. Document backward compatibility
  4. Get approval from: Tech Lead + Product Lead
  5. Update version number
  6. Deploy schema version to all environments
  7. Monitor for configuration drift
```

---

## 8. Dependency Documentation

### 8.1 Configuration Dependencies

```yaml
Key Dependencies:
  - API_PORT depends on: API_HOST (must have same network scope)
  - DATABASE_POOL_SIZE depends on: DATABASE_HOST (pool size scales with distance)
  - LOG_LEVEL depends on: ENVIRONMENT (dev=DEBUG, prod=WARNING)
  - ENABLE_SMS_NOTIFICATIONS depends on: TWILIO_AUTH_TOKEN (secret exists)
  - CACHE_TTL_SECONDS depends on: CACHE_BACKEND (Redis/Memcached/None)

Conflict Prevention:
  - Cannot set both DATABASE_HOST and DATABASE_URL
  - Cannot set both LOG_LEVEL=DEBUG and PRODUCTION_MODE=true
  - Cannot set CACHE_TTL=0 with ENABLE_CACHING=true
```

---

## 9. Catalog Access and Discovery

### 9.1 Programmatic Access

Configuration schema is accessible to automation:

```python
# app/config/schema.py
CONFIG_SCHEMA = {
    "web_app": {
        "required_keys": ["DATABASE_HOST", "DATABASE_PORT", ...],
        "optional_keys": ["LOG_LEVEL", "LOG_FORMAT", ...],
        "secret_keys": ["DATABASE_PASSWORD", "AUTH_SECRET_KEY", ...],
        "validation_rules": { ... },
    },
    "booking_service": { ... },
    # ... other services
}

def get_required_keys(service_name):
    """Get all required config keys for service."""
    return CONFIG_SCHEMA[service_name]["required_keys"]

def get_all_secrets(service_name):
    """Get all secret keys for service."""
    return CONFIG_SCHEMA[service_name]["secret_keys"]
```

### 9.2 Documentation Discovery

Schema documentation is discoverable:

```bash
# CLI to discover configuration
$ propellq-cli config schema web_app
Loaded schema version 1.0

Required Keys (startup-blocking):
  - DATABASE_HOST: string (PostgreSQL host)
  - DATABASE_PORT: integer (default 5432)
  - DATABASE_NAME: string
  - API_PORT: integer
  - ENVIRONMENT: enum (dev|staging|prod)

Optional Keys:
  - LOG_LEVEL: enum (default INFO)
  - LOG_FORMAT: enum (default json)
  - ... (10 more)

Secret Keys:
  - DATABASE_PASSWORD (from secret_path: prod/database/master_password)
  - AUTH_SECRET_KEY (from secret_path: app/auth/secret_key)
  - ... (6 more)
```

---

## 10. Known Limitations

### 10.1 v1.0 Limitations

```
Current scope:
  ✓ Static schema definition (not auto-generated)
  ✓ Configuration discovery via CLI
  ✗ Dynamic schema updates (v1.1)
  ✗ Cross-service config validation (v1.1)
  ✗ Configuration recommendation engine (v1.2)

Planned enhancements:
  - v1.1: Auto-generate schema from code annotations
  - v1.1: Cross-service conflict detection
  - v1.2: AI-powered configuration recommendations
  - v1.2: Configuration drift detection
```

---

## References

- [CFG-2: Precedence and Resolution Rules](CFG-2-PRECEDENCE_AND_RESOLUTION_RULES.md)
- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [VALID-1: Startup Validation Gate](VALID-1-STARTUP_VALIDATION_GATE.md)
- [OPS-1: Configuration Runbook](OPS-1-CONFIGURATION_RUNBOOK.md)

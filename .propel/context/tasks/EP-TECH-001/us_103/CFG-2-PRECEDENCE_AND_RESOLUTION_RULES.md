# CFG-2: Precedence and Resolution Rules

**Author**: Architecture Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines the deterministic order in which configuration values are resolved from multiple sources. Precedence rules ensure that configuration behavior is predictable and auditable, eliminating ambiguity about which value will be used.

---

## 2. Configuration Source Hierarchy

### 2.1 Precedence Order (Highest to Lowest)

Configuration is resolved in this strict order. The first source with a defined value wins:

```
1. RUNTIME OVERRIDES (highest priority)
   ↓
2. ENVIRONMENT VARIABLES
   ↓
3. CONFIGURATION FILES (local .env, ./config/)
   ↓
4. SECRET MANAGER (for secret keys only)
   ↓
5. CODE DEFAULTS (hardcoded defaults in app/)
   ↓
6. SCHEMA DEFAULTS (from CFG-1)
   ↓
7. MISSING (lowest priority - triggers fail-fast)
```

### 2.2 Precedence Matrix by Source Type

| Priority | Source | Scope | Example | Used For |
|----------|--------|-------|---------|----------|
| 1 | Runtime override | CLI/process | `--api-port 9000` | One-off testing |
| 2 | Environment variable | Process environment | `API_PORT=8000` | Server config |
| 3 | Config file (.env) | File system | `.env: API_PORT=7000` | Local development |
| 4 | Config file (./config) | File system | `./config/app.yaml` | Structured config |
| 5 | Secret manager | Secure backend | `/prod/database/password` | Secrets only |
| 6 | Code defaults | Python/Go code | `db_timeout = os.getenv(..., 5000)` | Fallback |
| 7 | Schema defaults | CFG-1 document | `default: 5432` | Documentation |
| 8 | Missing | None | (not found) | Fail-fast error |

---

## 3. Detailed Resolution Rules by Source

### 3.1 Runtime Overrides (Priority 1)

**When used**: Testing, debugging, temporary workarounds  
**Set by**: CLI arguments, environment at startup  
**Override capability**: Can override any source except required validation

```bash
# Example: Override config at startup
python app/server.py --api-port 9000 --log-level DEBUG --environment test

# Example: Override via environment variable before process start
API_PORT=9000 python app/server.py

# Implementation pattern
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--api-port', type=int, help='Override API_PORT')
parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING'])
args = parser.parse_args()

config = load_config_from_defaults()
if args.api_port:
    config['API_PORT'] = args.api_port  # Runtime override wins
```

**Limitations**:
- Runtime overrides are not persisted
- Cannot override required startup validation
- Cannot override secrets (must use secret manager)
- Logged in audit trail for compliance

---

### 3.2 Environment Variables (Priority 2)

**When used**: Container orchestration (Kubernetes, Docker), CI/CD  
**Set by**: Shell environment, deployment manifests  
**Persistence**: Depends on where environment is defined

```bash
# Example: Container environment variables
export DATABASE_HOST=db.prod.internal
export DATABASE_PORT=5432
export DATABASE_NAME=propellq
export LOG_LEVEL=INFO

# Implementation in code
import os

config = {
    'DATABASE_HOST': os.getenv('DATABASE_HOST'),
    'DATABASE_PORT': os.getenv('DATABASE_PORT', '5432'),  # Default if not set
    'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
}
```

**Container example** (docker-compose.yml):

```yaml
services:
  web_app:
    image: propellq/web_app:latest
    environment:
      DATABASE_HOST: ${DB_HOST}
      DATABASE_PORT: ${DB_PORT}
      ENVIRONMENT: production
      LOG_LEVEL: INFO
```

**Kubernetes example** (deployment.yaml):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        env:
        - name: DATABASE_HOST
          value: "db.prod.internal"
        - name: DATABASE_PORT
          value: "5432"
        - name: ENVIRONMENT
          value: "prod"
```

---

### 3.3 Configuration Files (Priority 3)

#### 3.3a .env Files (Development & Local)

**When used**: Local development, testing  
**Location**: `.env` (gitignored), `.env.staging`, `.env.prod` (gitignored)  
**Format**: KEY=VALUE (one per line, no complex nesting)

```bash
# .env (for local development)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=propellq_dev
API_PORT=8000
LOG_LEVEL=DEBUG
ENABLE_ANALYTICS=false
```

**Implementation**:

```python
from dotenv import load_dotenv
import os

# Load .env file (does not override existing env vars)
load_dotenv('.env', override=False)

config = {
    'DATABASE_HOST': os.getenv('DATABASE_HOST', 'localhost'),
    'DATABASE_PORT': int(os.getenv('DATABASE_PORT', '5432')),
}
```

**Important**: Never commit `.env` to source control

```bash
# .gitignore
.env
.env.*.local
config/secrets.yaml
```

#### 3.3b YAML Configuration Files (Structured)

**When used**: Complex configuration, multiple environments  
**Location**: `./config/app.yaml`, `./config/app.prod.yaml`  
**Format**: YAML with hierarchical structure

```yaml
# ./config/app.yaml (development defaults)
app:
  name: "web_app"
  port: 8000
  host: "0.0.0.0"

database:
  host: "localhost"
  port: 5432
  name: "propellq_dev"
  pool:
    size: 10
    timeout: 30

logging:
  level: "DEBUG"
  format: "text"

features:
  analytics: false
  sms_notifications: false
```

```yaml
# ./config/app.prod.yaml (production overrides)
app:
  port: 8080
  
database:
  host: "prod-db.rds.amazonaws.com"
  port: 5432
  pool:
    size: 50
    timeout: 15

logging:
  level: "WARNING"
  format: "json"

features:
  analytics: true
  sms_notifications: true
```

**Implementation**:

```python
import yaml
import os

def load_config():
    # Load base config
    with open('./config/app.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load environment-specific overrides
    env_file = f"./config/app.{os.getenv('ENVIRONMENT', 'dev')}.yaml"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f)
            config.update(env_config)
    
    # Environment variables override files
    if os.getenv('DATABASE_HOST'):
        config['database']['host'] = os.getenv('DATABASE_HOST')
    
    return config
```

---

### 3.4 Secret Manager (Priority 4)

**When used**: All secrets in any environment  
**Set by**: Deployment automation, secret manager  
**Access**: via service identities, role-based access

```python
# Implementation pattern for secret resolution
import boto3

def load_secret(secret_path):
    """Load secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    try:
        response = client.get_secret_value(SecretId=secret_path)
        return response['SecretString']
    except client.exceptions.ResourceNotFoundException:
        raise ConfigError(f"Secret not found: {secret_path}")
    except client.exceptions.AccessDeniedException:
        raise ConfigError(f"Access denied to secret: {secret_path}")

# Usage
config = {
    'DATABASE_PASSWORD': load_secret('prod/database/master_password'),
    'AUTH_SECRET_KEY': load_secret('app/auth/secret_key'),
}
```

**Important**: Secrets are NEVER stored in environment variables when avoidable. Load directly from secret manager.

---

### 3.5 Code Defaults (Priority 5)

**When used**: Fallback for optional values when other sources fail  
**Set by**: Hardcoded in application source  
**Usage**: Only for non-critical parameters

```python
# app/config/defaults.py

DEFAULT_CONFIG = {
    'LOG_LEVEL': 'INFO',                    # Fallback if not in environment
    'LOG_FORMAT': 'json',                   # Fallback if not in config file
    'API_TIMEOUT_MS': 30000,                # Fallback if not specified
    'DATABASE_POOL_SIZE': 10,               # Fallback if not specified
    'CACHE_TTL_SECONDS': 3600,              # Fallback if not specified
    'MAX_RETRY_ATTEMPTS': 3,                # Fallback if not specified
}

# app/config/loader.py
import os
from app.config.defaults import DEFAULT_CONFIG

def get_config_value(key, source_priority=None):
    """Get config value with precedence checking."""
    
    # 1. Check runtime overrides (if available in context)
    if hasattr(context, 'runtime_overrides') and key in context.runtime_overrides:
        return context.runtime_overrides[key]
    
    # 2. Check environment variables
    if key in os.environ:
        return os.environ[key]
    
    # 3. Check config files
    if key in loaded_yaml_config:
        return loaded_yaml_config[key]
    
    # 4. Check secret manager (for secrets only)
    # (handled separately in load_secrets())
    
    # 5. Check code defaults
    if key in DEFAULT_CONFIG:
        return DEFAULT_CONFIG[key]
    
    # 6. Return None or raise error for required keys
    return None
```

---

### 3.6 Schema Defaults (Priority 7)

**When used**: Documentation and validation only  
**Set by**: CFG-1 schema document  
**Usage**: Defines what default SHOULD be if not elsewhere

```yaml
# From CFG-1
DATABASE_PORT:
  type: integer
  required: true
  default: 5432  # This is the schema default
  
LOG_LEVEL:
  type: enum
  required: false
  default: "INFO"  # This is the schema default
```

---

## 4. Conflict Resolution Procedure

### 4.1 Detecting Conflicts

Conflicts occur when multiple sources define conflicting values:

```
Scenario 1: Environment Variable vs. Config File
  ENV var:  API_PORT=9000
  .env:     API_PORT=8000
  Result:   USE 9000 (env var wins, priority 2 > priority 3)

Scenario 2: Runtime Override vs. Environment Variable
  Runtime:  --api-port 7000
  ENV var:  API_PORT=8000
  Result:   USE 7000 (runtime wins, priority 1 > priority 2)

Scenario 3: Config File vs. Secret Manager (for secrets)
  .env:     DATABASE_PASSWORD=secret123  ← PROHIBITED
  Secret:   prod/database/password=***
  Result:   ERROR - Secrets cannot be in .env files
```

### 4.2 Conflict Detection Code

```python
def validate_no_conflicts(loaded_sources):
    """Detect and report configuration conflicts."""
    conflicts = []
    
    # Check for secrets in files (always prohibited)
    if 'DATABASE_PASSWORD' in loaded_file_config:
        conflicts.append({
            'type': 'CRITICAL',
            'key': 'DATABASE_PASSWORD',
            'issue': 'Secret found in configuration file (prohibited)',
            'fix': 'Remove from .env, load only from secret manager',
        })
    
    # Warn about multiple sources defining same key
    keys_by_source = {}
    for source, config in loaded_sources.items():
        for key in config:
            if key not in keys_by_source:
                keys_by_source[key] = []
            keys_by_source[key].append(source)
    
    for key, sources in keys_by_source.items():
        if len(sources) > 1:
            # This is OK - precedence rules apply
            logging.debug(f"Key {key} defined in {sources}, using {sources[0]}")
    
    return conflicts

# Usage
conflicts = validate_no_conflicts({
    'env_vars': env_config,
    'files': file_config,
    'secrets': secret_config,
})

if conflicts:
    for conflict in conflicts:
        if conflict['type'] == 'CRITICAL':
            raise ConfigError(conflict['issue'])
        else:
            logger.warning(f"Config warning: {conflict['issue']}")
```

---

## 5. Prohibited Configuration Patterns

### 5.1 Anti-Patterns That Will Be Rejected

```yaml
PROHIBITED:
  1. Secrets in .env or config files
     ✗ DATABASE_PASSWORD=secret123 in .env
     ✓ Load DATABASE_PASSWORD from secret manager only

  2. Environment variable with two different values
     ✗ API_PORT=8000 in .env AND API_PORT=9000 in ENV
     ✓ ENV var takes precedence (rules defined)

  3. Hardcoded credentials in code
     ✗ password = "hardcoded_secret"
     ✓ password = load_secret("prod/database/password")

  4. Configuration in comments/docs
     ✗ # database host is db.prod.internal
     ✓ DATABASE_HOST=db.prod.internal in config

  5. Unvalidated configuration values
     ✗ port = int(os.getenv('PORT'))  # Could fail
     ✓ port = validated_int(os.getenv('PORT'), min=1, max=65535)

  6. Conditional imports based on environment
     ✗ if ENVIRONMENT == 'prod': use_prod_db_config()
     ✓ ENVIRONMENT variable selects config file to load
```

---

## 6. Resolution Algorithm

### 6.1 Configuration Loading Sequence

```python
def load_configuration(environment='dev'):
    """
    Load configuration following strict precedence rules.
    
    Steps:
    1. Load schema defaults (CFG-1)
    2. Load code defaults
    3. Load config files (./config/app.yaml, ./config/app.{env}.yaml)
    4. Load environment variables
    5. Load secrets from secret manager
    6. Apply runtime overrides
    7. Validate all required keys present
    8. Validate all values match schema constraints
    """
    
    config = {}
    
    # Step 1: Schema defaults from CFG-1
    for key, schema in CONFIG_SCHEMA.items():
        if 'default' in schema:
            config[key] = schema['default']
    
    # Step 2: Code defaults
    config.update(DEFAULT_CONFIG)
    
    # Step 3: Config files
    base_config = load_yaml('./config/app.yaml')
    config.update(base_config)
    
    env_config_file = f'./config/app.{environment}.yaml'
    if os.path.exists(env_config_file):
        env_config = load_yaml(env_config_file)
        config.update(env_config)
    
    # Step 4: Environment variables (override files)
    for key in CONFIG_SCHEMA:
        if key in os.environ:
            config[key] = os.environ[key]
    
    # Step 5: Secrets from secret manager
    for key in CONFIG_SCHEMA:
        schema = CONFIG_SCHEMA[key]
        if schema.get('type') == 'secret':
            secret_path = schema.get('secret_path')
            if secret_path:
                config[key] = load_secret(secret_path)
    
    # Step 6: Runtime overrides (if available)
    if hasattr(context, 'runtime_overrides'):
        config.update(context.runtime_overrides)
    
    # Step 7: Validate required keys
    for key, schema in CONFIG_SCHEMA.items():
        if schema.get('required') and key not in config:
            raise ConfigError(f"Required key missing: {key}")
    
    # Step 8: Validate schema constraints
    for key, value in config.items():
        validate_config_value(key, value, CONFIG_SCHEMA[key])
    
    return config
```

---

## 7. Testing Precedence Rules

### 7.1 Unit Tests for Precedence

```python
# tests/test_config_precedence.py

def test_env_var_overrides_config_file():
    """Environment variables take precedence over config files."""
    os.environ['API_PORT'] = '9000'
    config = load_configuration()
    assert config['API_PORT'] == 9000  # From env, not file

def test_runtime_override_wins():
    """Runtime overrides have highest priority."""
    os.environ['API_PORT'] = '9000'
    config = load_configuration(runtime_overrides={'API_PORT': 7000})
    assert config['API_PORT'] == 7000

def test_secret_manager_used_for_secrets():
    """Secrets loaded from manager, not files."""
    config = load_configuration()
    # DATABASE_PASSWORD should come from secret manager
    assert config['DATABASE_PASSWORD'] == load_secret('prod/database/password')

def test_schema_default_as_fallback():
    """Schema defaults used when no other source has value."""
    config = load_configuration()
    # LOG_LEVEL defaults to INFO from schema
    assert config['LOG_LEVEL'] == 'INFO'

def test_prohibited_pattern_rejected():
    """Secrets in .env files are rejected."""
    with pytest.raises(ConfigError):
        # Try to load config with secret in .env
        config = load_configuration(allow_secrets_in_files=False)
```

---

## 8. Documentation and Communication

### 8.1 Precedence Quick Reference

```
Quick Reference:
  Highest Priority (wins)
  1. Runtime arguments: --api-port 9000
  2. Environment variables: export API_PORT=8000
  3. Config files: ./config/app.yaml
  4. Secret manager: aws secretsmanager get-secret-value
  5. Code defaults: DEFAULT_CONFIG = {...}
  6. Schema defaults: from CFG-1 document
  Lowest Priority (fails if missing)
```

### 8.2 Developer Guidance

```markdown
# Configuration Precedence for Developers

When a value is needed, the system checks in this order:

1. **Runtime overrides** - Use this for testing
   `python app/server.py --api-port 9000`

2. **Environment variables** - Use this in containers
   `export API_PORT=8000`

3. **Configuration files** - Use this for development
   `.env` or `./config/app.yaml`

4. **Secret manager** - ONLY for secrets
   Use AWS Secrets Manager or Vault

5. **Code defaults** - Last resort
   Hardcoded fallbacks in app/config/defaults.py

## Examples

### Local Development
Use .env file (lowest priority, easy to change):
```
DATABASE_HOST=localhost
API_PORT=8000
```

### Docker Container
Use environment variables (set in docker-compose):
```
API_PORT=9000
DATABASE_HOST=db.internal
```

### Production
Use secret manager (never in env vars or files):
```
# Load from AWS Secrets Manager
```
```

---

## 9. Known Limitations

### 9.1 v1.0 Limitations

```
Current scope:
  ✓ Precedence rules defined and enforced
  ✓ Configuration from multiple sources supported
  ✓ Conflict detection implemented
  ✗ Real-time config updates (v1.1)
  ✗ Configuration encryption at rest (v1.1)
  ✗ Configuration change notifications (v1.1)

Planned enhancements:
  - v1.1: Hot reload for non-critical config
  - v1.1: Configuration encryption in files
  - v1.1: Event notifications on config changes
```

---

## References

- [CFG-1: Configuration Schema and Catalog](CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md)
- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [VALID-1: Startup Validation Gate](VALID-1-STARTUP_VALIDATION_GATE.md)

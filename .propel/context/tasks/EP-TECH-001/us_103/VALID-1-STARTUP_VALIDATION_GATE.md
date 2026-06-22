# VALID-1: Startup Validation Gate

**Author**: Platform Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines fail-fast startup validation that ensures all required configuration and secrets are present before the service starts. Clear diagnostic messages guide troubleshooting.

---

## 2. Startup Validation Architecture

### 2.1 Validation Phases

```
                    Service Start
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  Phase 1: Load Configuration    │
        │  (env vars, files, secrets)     │
        └─────────────┬───────────────────┘
                      │
        ┌─────────────▼───────────────────┐
        │  Phase 2: Validate Required     │
        │  (all keys present)             │
        └─────────────┬───────────────────┘
                      │
        ┌─────────────▼───────────────────┐
        │  Phase 3: Validate Constraints  │
        │  (types, ranges, formats)       │
        └─────────────┬───────────────────┘
                      │
        ┌─────────────▼───────────────────┐
        │  Phase 4: Connectivity Tests    │
        │  (DB, Redis, services)          │
        └─────────────┬───────────────────┘
                      │
        ┌─────────────▼───────────────────┐
        │  Phase 5: Health Check          │
        │  (readiness probe succeeds)     │
        └─────────────┬───────────────────┘
                      │
                      ▼
              ✓ Service Ready
              Listening on port
```

---

## 3. Validation Rules by Phase

### 3.1 Phase 1: Load Configuration

```python
# app/config/loader.py

def load_configuration():
    """Load all configuration from all sources."""
    
    logger.info("=== PHASE 1: Loading Configuration ===")
    
    config = {}
    
    # Try each source in order
    sources_tried = []
    
    try:
        # 1. Load .env file
        logger.debug("Loading from .env file...")
        from dotenv import load_dotenv
        load_dotenv('.env', override=False)
        sources_tried.append('.env')
    except Exception as e:
        logger.warning(f"Could not load .env: {e}")
    
    try:
        # 2. Load YAML config
        logger.debug("Loading from config/app.yaml...")
        with open('config/app.yaml', 'r') as f:
            yaml_config = yaml.safe_load(f)
            config.update(yaml_config or {})
        sources_tried.append('config/app.yaml')
    except FileNotFoundError:
        logger.debug("config/app.yaml not found (optional)")
    except Exception as e:
        logger.error(f"Error loading config/app.yaml: {e}")
        raise
    
    try:
        # 3. Load environment variables
        logger.debug("Loading environment variables...")
        for key, value in os.environ.items():
            if key.isupper() and not key.startswith('_'):
                config[key] = value
        sources_tried.append('environment variables')
    except Exception as e:
        logger.error(f"Error loading environment variables: {e}")
        raise
    
    # 4. Load secrets from manager
    logger.debug("Loading secrets from manager...")
    try:
        secrets = load_secrets()
        config.update(secrets)
        sources_tried.append('secret manager')
    except Exception as e:
        logger.error(f"Error loading secrets: {e}")
        logger.error("Cannot start without secrets - secret manager unreachable?")
        raise
    
    logger.info(f"✓ Configuration loaded from: {', '.join(sources_tried)}")
    return config

def load_secrets():
    """Load secrets from AWS Secrets Manager."""
    
    logger.debug("Connecting to AWS Secrets Manager...")
    
    try:
        client = boto3.client('secretsmanager', region_name='us-east-1')
        
        secrets = {}
        secret_paths = {
            'DATABASE_PASSWORD': 'prod/database/master_password',
            'AUTH_SECRET_KEY': 'prod/auth/secret_key',
            # ... other secrets
        }
        
        for key, path in secret_paths.items():
            try:
                response = client.get_secret_value(SecretId=path)
                secrets[key] = response['SecretString']
                logger.debug(f"✓ Loaded secret: {key}")
            except client.exceptions.ResourceNotFoundException:
                logger.warning(f"Secret not found: {path}")
            except client.exceptions.AccessDeniedException:
                logger.error(f"Access denied to secret: {path}")
                logger.error("Service identity may lack permission - check IAM role")
                raise
        
        return secrets
    
    except Exception as e:
        logger.error(f"Failed to load secrets: {str(e)}")
        raise ConfigError("Cannot load secrets from manager")
```

---

### 3.2 Phase 2: Validate Required Keys

```python
# app/config/validators.py

def validate_required_keys(config):
    """Ensure all required configuration keys are present."""
    
    logger.info("=== PHASE 2: Validating Required Keys ===")
    
    required_keys = {
        'DATABASE_HOST': str,
        'DATABASE_PORT': int,
        'DATABASE_NAME': str,
        'API_PORT': int,
        'ENVIRONMENT': str,
        'AUTH_SECRET_KEY': str,
        'DATABASE_PASSWORD': str,
    }
    
    missing_keys = []
    invalid_type = []
    
    for key, expected_type in required_keys.items():
        if key not in config:
            missing_keys.append(key)
            logger.error(f"✗ MISSING: {key}")
        else:
            value = config[key]
            if not value or (isinstance(value, str) and not value.strip()):
                missing_keys.append(f"{key} (empty)")
                logger.error(f"✗ EMPTY: {key}")
            else:
                logger.debug(f"✓ Found: {key}")
    
    if missing_keys:
        error_msg = f"CRITICAL: Missing required configuration:\n"
        for key in missing_keys:
            error_msg += f"  - {key}\n"
        error_msg += "\nFix: Set these environment variables or in .env file\n"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    logger.info(f"✓ All {len(required_keys)} required keys present")

def validate_config_constraints(config):
    """Validate configuration values meet constraints."""
    
    logger.info("=== PHASE 3: Validating Config Constraints ===")
    
    constraints = {
        'DATABASE_PORT': {'type': int, 'min': 1, 'max': 65535},
        'API_PORT': {'type': int, 'min': 1, 'max': 65535},
        'ENVIRONMENT': {'type': str, 'enum': ['dev', 'staging', 'prod']},
        'LOG_LEVEL': {'type': str, 'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
    }
    
    validation_errors = []
    
    for key, rules in constraints.items():
        if key not in config:
            logger.debug(f"⊘ Optional: {key} (not set)")
            continue
        
        value = config[key]
        
        # Type validation
        if 'type' in rules:
            try:
                if rules['type'] == int:
                    value = int(value)
                elif rules['type'] == bool:
                    value = str(value).lower() in ('true', '1', 'yes')
                elif rules['type'] == str:
                    value = str(value)
            except (ValueError, TypeError):
                validation_errors.append(f"{key}: invalid type (expected {rules['type']})")
                logger.error(f"✗ {key}: invalid type")
                continue
        
        # Range validation
        if 'min' in rules and value < rules['min']:
            validation_errors.append(f"{key}: value {value} < minimum {rules['min']}")
            logger.error(f"✗ {key}: value out of range")
        
        if 'max' in rules and value > rules['max']:
            validation_errors.append(f"{key}: value {value} > maximum {rules['max']}")
            logger.error(f"✗ {key}: value out of range")
        
        # Enum validation
        if 'enum' in rules and value not in rules['enum']:
            validation_errors.append(f"{key}: value '{value}' not in {rules['enum']}")
            logger.error(f"✗ {key}: invalid enum value")
        
        if key not in validation_errors:
            logger.debug(f"✓ Valid: {key}={value}")
    
    if validation_errors:
        error_msg = "CRITICAL: Configuration constraints violated:\n"
        for error in validation_errors:
            error_msg += f"  - {error}\n"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    logger.info(f"✓ All config constraints satisfied")
```

---

### 3.3 Phase 4: Connectivity Tests

```python
# app/startup/connectivity.py

def test_connectivity(config):
    """Test connectivity to external services."""
    
    logger.info("=== PHASE 4: Testing Connectivity ===")
    
    connectivity_tests = {
        'database': test_database_connection,
        'redis': test_redis_connection,
        'elasticsearch': test_elasticsearch_connection,
    }
    
    failures = []
    
    for test_name, test_func in connectivity_tests.items():
        try:
            logger.info(f"Testing {test_name} connectivity...")
            test_func(config)
            logger.info(f"✓ {test_name}: OK")
        except Exception as e:
            logger.error(f"✗ {test_name}: FAILED - {str(e)}")
            failures.append((test_name, str(e)))
    
    if failures:
        error_msg = "CRITICAL: Service connectivity failed:\n"
        for service, error in failures:
            error_msg += f"  - {service}: {error}\n"
        error_msg += "\nDiagnosis checklist:\n"
        error_msg += "  1. Check service is running (docker ps, kubectl get pods)\n"
        error_msg += "  2. Check credentials (DATABASE_PASSWORD, etc.)\n"
        error_msg += "  3. Check network connectivity (ping, nc, curl)\n"
        error_msg += "  4. Check firewall rules\n"
        error_msg += "  5. Check service logs for errors\n"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    logger.info(f"✓ All connectivity tests passed")

def test_database_connection(config):
    """Test database connectivity and permissions."""
    
    try:
        db = psycopg2.connect(
            host=config['DATABASE_HOST'],
            port=config['DATABASE_PORT'],
            database=config['DATABASE_NAME'],
            user='master_user',
            password=config['DATABASE_PASSWORD'],
            connect_timeout=5
        )
        
        # Test read permission
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        if result[0] != 1:
            raise RuntimeError("Database returned unexpected result")
        
        db.close()
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Cannot connect to database: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Database test failed: {str(e)}")

def test_redis_connection(config):
    """Test Redis connectivity."""
    
    try:
        redis_client = redis.Redis(
            host=config.get('REDIS_HOST', 'localhost'),
            port=int(config.get('REDIS_PORT', 6379)),
            password=config.get('REDIS_PASSWORD'),
            socket_connect_timeout=5
        )
        
        redis_client.ping()
        redis_client.close()
    except redis.ConnectionError as e:
        raise RuntimeError(f"Cannot connect to Redis: {str(e)}")
```

---

### 3.4 Phase 5: Readiness Check

```python
# app/startup/health.py

@app.get("/health/ready")
async def readiness_check():
    """Readiness probe - all dependencies healthy."""
    
    logger.info("Running readiness check...")
    
    checks = {
        'database': check_database_healthy,
        'redis': check_redis_healthy,
        'memory': check_memory_available,
    }
    
    results = {}
    all_ready = True
    
    for check_name, check_func in checks.items():
        try:
            result = await check_func()
            results[check_name] = result
            if result.get('status') != 'healthy':
                all_ready = False
                logger.warning(f"⚠ {check_name}: {result.get('message')}")
            else:
                logger.debug(f"✓ {check_name}: healthy")
        except Exception as e:
            results[check_name] = {'status': 'unhealthy', 'error': str(e)}
            all_ready = False
            logger.error(f"✗ {check_name}: {str(e)}")
    
    if all_ready:
        return {'status': 'ready', 'checks': results}
    else:
        raise HTTPException(status_code=503, detail={'status': 'not_ready', 'checks': results})

async def check_database_healthy():
    """Check database is responsive."""
    try:
        db.execute("SELECT 1")
        return {'status': 'healthy', 'message': 'Database responding'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': f'Database error: {str(e)}'}
```

---

## 4. Diagnostic Output

### 4.1 Successful Startup

```
2026-06-22 10:00:00 INFO  === PHASE 1: Loading Configuration ===
2026-06-22 10:00:00 DEBUG Loading from .env file...
2026-06-22 10:00:00 DEBUG Loading from config/app.yaml...
2026-06-22 10:00:00 DEBUG Loading environment variables...
2026-06-22 10:00:00 DEBUG Loading secrets from manager...
2026-06-22 10:00:00 DEBUG ✓ Loaded secret: DATABASE_PASSWORD
2026-06-22 10:00:00 DEBUG ✓ Loaded secret: AUTH_SECRET_KEY
2026-06-22 10:00:00 INFO  ✓ Configuration loaded from: .env, config/app.yaml, environment variables, secret manager

2026-06-22 10:00:01 INFO  === PHASE 2: Validating Required Keys ===
2026-06-22 10:00:01 DEBUG ✓ Found: DATABASE_HOST
2026-06-22 10:00:01 DEBUG ✓ Found: DATABASE_PORT
2026-06-22 10:00:01 DEBUG ✓ Found: DATABASE_NAME
2026-06-22 10:00:01 DEBUG ✓ Found: API_PORT
2026-06-22 10:00:01 DEBUG ✓ Found: ENVIRONMENT
2026-06-22 10:00:01 DEBUG ✓ Found: AUTH_SECRET_KEY
2026-06-22 10:00:01 DEBUG ✓ Found: DATABASE_PASSWORD
2026-06-22 10:00:01 INFO  ✓ All 7 required keys present

2026-06-22 10:00:02 INFO  === PHASE 3: Validating Config Constraints ===
2026-06-22 10:00:02 DEBUG ✓ Valid: DATABASE_PORT=5432
2026-06-22 10:00:02 DEBUG ✓ Valid: API_PORT=8000
2026-06-22 10:00:02 DEBUG ✓ Valid: ENVIRONMENT=prod
2026-06-22 10:00:02 DEBUG ✓ Valid: LOG_LEVEL=INFO
2026-06-22 10:00:02 INFO  ✓ All config constraints satisfied

2026-06-22 10:00:03 INFO  === PHASE 4: Testing Connectivity ===
2026-06-22 10:00:03 INFO  Testing database connectivity...
2026-06-22 10:00:03 INFO  ✓ database: OK
2026-06-22 10:00:04 INFO  ✓ All connectivity tests passed

2026-06-22 10:00:05 INFO  === PHASE 5: Running Readiness Check ===
2026-06-22 10:00:05 INFO  ✓ database: healthy
2026-06-22 10:00:05 INFO  ✓ redis: healthy
2026-06-22 10:00:05 INFO  ✓ memory: 78% available
2026-06-22 10:00:05 INFO  ✓ Service ready

2026-06-22 10:00:06 INFO  Starting server on 0.0.0.0:8000
```

### 4.2 Failure Case: Missing Secret

```
2026-06-22 10:00:00 INFO  === PHASE 1: Loading Configuration ===
2026-06-22 10:00:00 DEBUG Loading secrets from manager...
2026-06-22 10:00:00 ERROR ✗ Access denied to secret: prod/database/master_password

CRITICAL ERROR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cannot load secrets from manager

DIAGNOSIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service identity may lack permission to access AWS Secrets Manager.

STEPS TO FIX:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Check IAM role attached to service:
   aws ec2 describe-instances --instance-ids i-xxx \
     --query 'Reservations[0].Instances[0].IamInstanceProfile'

2. Verify policy allows secret access:
   aws iam list-attached-role-policies --role-name web-app-prod

3. Get the policy document:
   aws iam get-role-policy --role-name web-app-prod \
     --policy-name web-app-secrets

4. Verify secret exists:
   aws secretsmanager describe-secret \
     --secret-id prod/database/master_password

5. If secret missing, create it:
   aws secretsmanager create-secret \
     --name prod/database/master_password \
     --secret-string "your-password-here"

For more help: See SEC-1-SECRET_MANAGER_INTEGRATION.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exiting with status 1
```

---

## 5. Known Limitations

### 5.1 v1.0 Limitations

```
Current scope:
  ✓ 5-phase startup validation
  ✓ Clear diagnostic messages
  ✓ Fail-fast on missing config
  ✗ Health probe metrics (v1.1)
  ✗ Configuration migration helpers (v1.1)
  ✗ Recovery suggestions (v1.1)

Planned enhancements:
  - v1.1: Prometheus health probe metrics
  - v1.1: Auto-migrate old config format
  - v1.1: AI-powered recovery suggestions
```

---

## References

- [CFG-1: Configuration Schema and Catalog](CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md)
- [CFG-2: Precedence and Resolution Rules](CFG-2-PRECEDENCE_AND_RESOLUTION_RULES.md)
- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [VALID-2: CI Configuration Safety Checks](VALID-2-CI_CONFIGURATION_SAFETY_CHECKS.md)

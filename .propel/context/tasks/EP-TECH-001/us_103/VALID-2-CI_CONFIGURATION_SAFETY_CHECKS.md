# VALID-2: CI Configuration Safety Checks

**Author**: Platform & DevOps Team  
**Date**: 2026-06-22  
**Status**: Active  
**Version**: 1.0  

---

## 1. Overview

This document defines CI/CD pipeline checks that validate configuration safety before deployment. Invalid, unsafe, or missing configuration blocks release, preventing bad configurations from reaching production.

---

## 2. CI Configuration Safety Checks

### 2.1 Check 1: No Secrets in Configuration Files

**Purpose**: Detect and block hardcoded secrets in .env, YAML, or JSON  
**Severity**: CRITICAL  
**Action**: BLOCK release  

```python
# scripts/ci_check_no_hardcoded_secrets.py

def check_no_hardcoded_secrets():
    """Detect hardcoded secrets in config files."""
    
    secret_patterns = [
        # Passwords
        r'password\s*[:=]\s*["\']?([a-zA-Z0-9]{6,})["\']?',
        r'pwd\s*[:=]\s*["\']?([a-zA-Z0-9]{6,})["\']?',
        
        # API keys
        r'api_key\s*[:=]\s*["\']?(sk-[a-zA-Z0-9]{20,})["\']?',
        r'secret_key\s*[:=]\s*["\']?([a-zA-Z0-9]{32,})["\']?',
        
        # AWS
        r'AKIA[0-9A-Z]{16}',  # AWS access key
        r'aws_secret_access_key\s*[:=]\s*["\']?([a-zA-Z0-9/+]{40})["\']?',
        
        # JWT tokens
        r'jwt_secret\s*[:=]\s*["\']?([a-zA-Z0-9._-]{20,})["\']?',
        
        # Database connection strings with password
        r'postgresql://[a-zA-Z0-9]+:([a-zA-Z0-9!@#$%^&*()_+-=]{6,})@',
    ]
    
    files_to_check = [
        '.env',
        '.env.prod',
        '.env.staging',
        'config/*.yaml',
        'config/*.yml',
        'config/*.json',
    ]
    
    violations = []
    
    for file_pattern in files_to_check:
        for file_path in glob.glob(file_pattern, recursive=True):
            if '.gitignore' in file_path or 'dist' in file_path:
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
                line_num = 0
                
                for line in content.split('\n'):
                    line_num += 1
                    
                    for pattern in secret_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'issue': 'Potential hardcoded secret detected',
                                'pattern': pattern,
                            })
    
    if violations:
        print("CRITICAL: Hardcoded secrets detected!")
        print("━" * 70)
        
        for violation in violations:
            print(f"\n{violation['file']}:{violation['line']}")
            print(f"  Issue: {violation['issue']}")
            print(f"  Pattern: {violation['pattern']}")
        
        print("\nFIX: Remove secrets from config files.")
        print("     Use secret manager instead (AWS Secrets Manager, Vault, etc)")
        print("     See SEC-1-SECRET_MANAGER_INTEGRATION.md")
        return False
    else:
        print("✓ No hardcoded secrets detected")
        return True

# CI integration
if __name__ == '__main__':
    success = check_no_hardcoded_secrets()
    sys.exit(0 if success else 1)
```

### 2.2 Check 2: All Required Keys Defined

**Purpose**: Ensure all required configuration keys exist  
**Severity**: CRITICAL  
**Action**: BLOCK release  

```python
# scripts/ci_check_required_keys.py

def check_required_keys_defined():
    """Verify all required config keys are defined."""
    
    required_keys = {
        'DATABASE_HOST': str,
        'DATABASE_PORT': int,
        'DATABASE_NAME': str,
        'API_PORT': int,
        'ENVIRONMENT': str,
        'LOG_LEVEL': str,
    }
    
    config = load_config_for_environment('prod')
    
    missing_keys = []
    
    for key, expected_type in required_keys.items():
        if key not in config:
            missing_keys.append(key)
        elif not config[key]:
            missing_keys.append(f"{key} (empty)")
    
    if missing_keys:
        print("CRITICAL: Missing required configuration keys!")
        print("━" * 70)
        print("\nMissing keys:")
        for key in missing_keys:
            print(f"  - {key}")
        
        print("\nRequired keys:")
        for key in required_keys:
            print(f"  - {key}: {required_keys[key].__name__}")
        
        print("\nFIX: Define these keys in .env or environment variables")
        print("     See CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md")
        return False
    else:
        print(f"✓ All {len(required_keys)} required keys defined")
        return True

# CI integration
if __name__ == '__main__':
    success = check_required_keys_defined()
    sys.exit(0 if success else 1)
```

### 2.3 Check 3: Configuration Types and Ranges

**Purpose**: Validate config values match schema types and constraints  
**Severity**: HIGH  
**Action**: BLOCK release  

```python
# scripts/ci_check_config_validation.py

def validate_config_types_and_ranges():
    """Validate config values match schema."""
    
    config_schema = {
        'DATABASE_PORT': {'type': int, 'min': 1, 'max': 65535},
        'API_PORT': {'type': int, 'min': 1, 'max': 65535},
        'ENVIRONMENT': {'type': str, 'enum': ['dev', 'staging', 'prod']},
        'LOG_LEVEL': {'type': str, 'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
        'DATABASE_POOL_SIZE': {'type': int, 'min': 2, 'max': 100},
        'API_TIMEOUT_MS': {'type': int, 'min': 100, 'max': 300000},
    }
    
    config = load_config_for_environment('prod')
    validation_errors = []
    
    for key, schema in config_schema.items():
        if key not in config:
            continue  # Already checked in Check 2
        
        value = config[key]
        
        # Type validation
        if schema['type'] == int:
            try:
                value = int(value)
            except (ValueError, TypeError):
                validation_errors.append(
                    f"{key}: Expected int, got {type(value).__name__}"
                )
                continue
        
        # Range validation
        if 'min' in schema and value < schema['min']:
            validation_errors.append(
                f"{key}: {value} < minimum {schema['min']}"
            )
        
        if 'max' in schema and value > schema['max']:
            validation_errors.append(
                f"{key}: {value} > maximum {schema['max']}"
            )
        
        # Enum validation
        if 'enum' in schema and value not in schema['enum']:
            validation_errors.append(
                f"{key}: '{value}' not in {schema['enum']}"
            )
    
    if validation_errors:
        print("HIGH: Configuration validation errors!")
        print("━" * 70)
        print("\nValidation errors:")
        for error in validation_errors:
            print(f"  - {error}")
        
        print("\nExpected schema:")
        for key, schema in config_schema.items():
            print(f"  - {key}: {schema}")
        
        return False
    else:
        print("✓ All configuration values valid")
        return True

# CI integration
if __name__ == '__main__':
    success = validate_config_types_and_ranges()
    sys.exit(0 if success else 1)
```

### 2.4 Check 4: No Wildcard Permissions in IAM

**Purpose**: Ensure IAM policies don't have overly broad permissions  
**Severity**: CRITICAL  
**Action**: BLOCK release  

```python
# scripts/ci_check_iam_policies.py

def check_no_wildcard_iam_policies():
    """Validate IAM policies have no wildcards."""
    
    iam_client = boto3.client('iam')
    
    service_roles = [
        'propellq-web-app-prod',
        'propellq-booking-service-prod',
        'propellq-search-service-prod',
    ]
    
    violations = []
    
    for role_name in service_roles:
        try:
            # Get inline policies
            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            
            for policy_name in inline_policies['PolicyNames']:
                policy_doc = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                
                # Check for wildcard resources in secret manager access
                for statement in policy_doc['RolePolicyDocument']['Statement']:
                    resources = statement.get('Resource', [])
                    if isinstance(resources, str):
                        resources = [resources]
                    
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    # Flag wildcard secret access
                    for action in actions:
                        if 'secretsmanager' in action.lower():
                            for resource in resources:
                                if '*' in resource and 'secret' in resource:
                                    violations.append({
                                        'role': role_name,
                                        'policy': policy_name,
                                        'resource': resource,
                                        'action': action,
                                    })
        
        except iam_client.exceptions.NoSuchEntityException:
            print(f"Warning: IAM role not found: {role_name}")
    
    if violations:
        print("CRITICAL: Overly broad IAM policy detected!")
        print("━" * 70)
        
        for violation in violations:
            print(f"\nRole: {violation['role']}")
            print(f"  Policy: {violation['policy']}")
            print(f"  Resource: {violation['resource']} ← Contains wildcard")
            print(f"  Action: {violation['action']}")
        
        print("\nFIX: Use specific resource ARNs instead of wildcards")
        print("     Example: arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:prod/database/*")
        print("     See SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md")
        return False
    else:
        print("✓ No wildcard IAM permissions detected")
        return True

# CI integration
if __name__ == '__main__':
    success = check_no_wildcard_iam_policies()
    sys.exit(0 if success else 1)
```

### 2.5 Check 5: No Plaintext Credentials in Docker Images

**Purpose**: Prevent credentials being baked into Docker images  
**Severity**: CRITICAL  
**Action**: BLOCK Docker build  

```bash
#!/bin/bash
# scripts/ci_check_docker_image_security.sh

# Scan Docker image for secrets

IMAGE_NAME="$1"

if [ -z "$IMAGE_NAME" ]; then
    echo "CRITICAL: Docker image name required"
    exit 1
fi

echo "Scanning Docker image for secrets: $IMAGE_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for common secret patterns in image layers
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  truffleHog/truffleHog \
  docker "$IMAGE_NAME" --json

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ No secrets detected in Docker image"
    exit 0
else
    echo "CRITICAL: Secrets detected in Docker image!"
    echo "Fix: Remove sensitive data from Dockerfile"
    echo "     Use multi-stage builds to exclude secrets from final image"
    echo "     Use --mount=type=secret in RUN command instead"
    exit 1
fi
```

### 2.6 Check 6: Configuration Schema Version Compatibility

**Purpose**: Ensure service version compatible with config schema  
**Severity**: MEDIUM  
**Action**: WARN (don't block, but notify)  

```python
# scripts/ci_check_schema_compatibility.py

def check_schema_compatibility():
    """Verify service is compatible with config schema."""
    
    # Get service version from package.json / setup.py / etc
    service_version = get_service_version()
    
    # Get schema version from CFG-1
    schema_version = get_config_schema_version()
    
    # Define compatibility matrix
    compatibility = {
        '1.0': {'min_schema': '1.0', 'max_schema': '1.0'},
        '1.1': {'min_schema': '1.0', 'max_schema': '1.1'},
        '2.0': {'min_schema': '2.0', 'max_schema': '2.0'},
    }
    
    if service_version not in compatibility:
        print(f"WARNING: Unknown service version {service_version}")
        return True
    
    compat = compatibility[service_version]
    
    if not (compat['min_schema'] <= schema_version <= compat['max_schema']):
        print(f"WARNING: Service {service_version} may not be compatible with schema {schema_version}")
        print(f"  Expected schema versions: {compat['min_schema']} to {compat['max_schema']}")
        print("\nNote: This is a warning, not a blocker")
        print("      Verify compatibility before deploying")
        return True
    else:
        print(f"✓ Service {service_version} compatible with schema {schema_version}")
        return True
```

---

## 3. CI Pipeline Integration

### 3.1 GitHub Actions Example

```yaml
# .github/workflows/config-validation.yml

name: Configuration Safety Checks

on: [push, pull_request]

jobs:
  config-checks:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Check for hardcoded secrets
      run: python scripts/ci_check_no_hardcoded_secrets.py
      if: always()
    
    - name: Check required keys
      run: python scripts/ci_check_required_keys.py
      if: always()
    
    - name: Validate config types
      run: python scripts/ci_check_config_validation.py
      if: always()
    
    - name: Check IAM policies
      run: python scripts/ci_check_iam_policies.py
      if: always()
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    
    - name: Scan Docker image
      run: bash scripts/ci_check_docker_image_security.sh propellq/web-app:latest
      if: always()
    
    - name: Comment results on PR
      if: github.event_name == 'pull_request' && always()
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const results = JSON.parse(fs.readFileSync('ci_results.json'));
          
          let comment = '## Configuration Safety Checks\n';
          for (const check of results) {
            const status = check.passed ? '✅' : '❌';
            comment += `\n${status} ${check.name}`;
            if (!check.passed) {
              comment += `\n  Error: ${check.error}`;
            }
          }
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

### 3.2 GitLab CI Example

```yaml
# .gitlab-ci.yml (excerpt)

config_safety_checks:
  stage: validate
  image: python:3.10
  script:
    - echo "Running configuration safety checks..."
    - python scripts/ci_check_no_hardcoded_secrets.py
    - python scripts/ci_check_required_keys.py
    - python scripts/ci_check_config_validation.py
  only:
    - merge_requests
    - main
  allow_failure: false  # Block merge if checks fail
```

---

## 4. Pre-Release Gate

### 4.1 Pre-Production Validation Checklist

```bash
#!/bin/bash
# scripts/pre_release_validation.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Pre-Release Configuration Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CHECKS_PASSED=0
CHECKS_FAILED=0

# Run all checks
for check_script in scripts/ci_check_*.py; do
    echo ""
    echo "Running: $(basename $check_script)"
    if python "$check_script"; then
        ((CHECKS_PASSED++))
    else
        ((CHECKS_FAILED++))
        echo "✗ FAILED"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Results: $CHECKS_PASSED passed, $CHECKS_FAILED failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $CHECKS_FAILED -gt 0 ]; then
    echo "❌ Pre-release validation FAILED"
    echo "   Cannot deploy with configuration issues"
    exit 1
else
    echo "✅ Pre-release validation PASSED"
    echo "   Safe to deploy"
    exit 0
fi
```

---

## 5. Known Limitations

### 5.1 v1.0 Limitations

```
Current scope:
  ✓ 6 critical safety checks
  ✓ CI/CD pipeline integration
  ✓ Pre-release validation gate
  ✗ Dynamic policy scanning (v1.1)
  ✗ Configuration drift detection (v1.1)
  ✗ Compliance rule engine (v1.2)

Planned enhancements:
  - v1.1: Scan current AWS policies
  - v1.1: Detect config divergence from schema
  - v1.2: Custom compliance rules
  - v1.2: Configuration audit reports
```

---

## References

- [CFG-1: Configuration Schema and Catalog](CFG-1-CONFIGURATION_SCHEMA_AND_CATALOG.md)
- [SEC-1: Secret Manager Integration](SEC-1-SECRET_MANAGER_INTEGRATION.md)
- [SEC-2: Least-Privilege Access Controls](SEC-2-LEAST_PRIVILEGE_ACCESS_CONTROLS.md)
- [VALID-1: Startup Validation Gate](VALID-1-STARTUP_VALIDATION_GATE.md)

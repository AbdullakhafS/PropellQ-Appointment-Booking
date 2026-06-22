# CFG-2: Precedence and Resolution Rules

**Status:** Published | **Version:** 1.0 | **Date:** 2026-06-22

---

## 1. Configuration Precedence

Configuration is resolved in this order (first match wins):

```
1. Runtime Overrides (highest priority)
   ↓
2. Secret Manager (secure values)
   ↓
3. Environment Variables
   ↓
4. Configuration Files (.env)
   ↓
5. Defaults (lowest priority)
```

---

## 2. Precedence Examples

### Example 1: Database Password

```
DB_PASSWORD resolution:
  1. Check for runtime override (if supported)
    → Not set
  2. Check Secret Manager
    → Found: "prod-db-pass-12345"
    → **USE THIS**
  3. Not checked (already resolved)

Result: "prod-db-pass-12345" from Secret Manager
```

### Example 2: Log Level

```
LOG_LEVEL resolution:
  1. Check for runtime override
    → Not set
  2. Check Secret Manager
    → Not appropriate for this key
  3. Check Environment Variable
    → Found: "DEBUG"
    → **USE THIS**
  4. Not checked (already resolved)

Result: "DEBUG" from Environment Variable
```

### Example 3: Cache TTL

```
CACHE_TTL resolution:
  1. Check for runtime override
    → Not set
  2. Check Secret Manager
    → Not appropriate
  3. Check Environment Variable
    → Not set
  4. Check .env file
    → Not set
  5. Use Default
    → 3600 (seconds)
    → **USE THIS**

Result: 3600 from Default
```

---

## 3. Prohibited Patterns

### ❌ Don't Do This

```
# Silent fallback (no error if missing)
var password = config["DB_PASSWORD"] ?? "";  // BAD

# Empty string accepted as valid
if (config["DB_HOST"] == "")  // BAD: should fail

# Null checks without validation
var port = int.Parse(config["DB_PORT"] ?? "0");  // BAD: 0 is invalid

# Environment specific fallbacks
if (env == "prod")
  password = secretManager.Get(...)
else
  password = config["PASSWORD"]  // BAD: inconsistent
```

### ✅ Do This Instead

```
// Explicit validation on both
var password = config["DB_PASSWORD"];
if (string.IsNullOrEmpty(password))
  throw new ConfigurationException("DB_PASSWORD is required");

// Consistent approach regardless of environment
var password = secretManager.Get("db-password")
  ?? throw new ConfigurationException("Secret not found");

// Type-safe with range validation
var port = int.Parse(config["DB_PORT"]
  ?? throw new ConfigurationException("DB_PORT required"));
if (port < 1024 || port > 65535)
  throw new ConfigurationException("DB_PORT out of range");
```

---

## 4. Override Capability Matrix

| Configuration | Can Override at Runtime | Reason |
|---|---|---|
| LOG_LEVEL | ✅ Yes | Useful for debugging in prod |
| DB_PASSWORD | ❌ No | Too risky, requires rotation instead |
| CACHE_TTL | ✅ Yes | Can tune performance on the fly |
| SERVICE_NAME | ❌ No | Immutable identity |
| TRACE_ENABLED | ✅ Yes | Enable/disable observability |
| DB_HOST | ❌ No | Cannot change at runtime safely |

---

## 5. Environment Variable Convention

All configuration as environment variables uses UPPER_SNAKE_CASE:

```
✅ Correct:
  SERVICE_NAME
  DB_HOST
  DB_POOL_SIZE
  LOG_LEVEL
  TRACE_ENABLED
  OAUTH_CLIENT_ID

❌ Incorrect:
  ServiceName
  db.host
  DBPoolSize
  log-level
  trace_enabled
  oauthClientId
```

---

## 6. Resolution Testing

```csharp
[TestClass]
public class ConfigurationPrecedenceTests
{
    [TestMethod]
    public void Precedence_SecretManagerOverEnvVar()
    {
        // Setup
        Environment.SetEnvironmentVariable("DB_PASSWORD", "env-value");
        var secretManager = new Mock<ISecretManager>();
        secretManager.Setup(x => x.GetSecret("db-password"))
            .Returns("secret-manager-value");
        
        var resolver = new ConfigurationResolver(
            secretManager.Object,
            new[] { ("DB_PASSWORD", "env-value") }
        );
        
        // Act
        var value = resolver.Resolve("DB_PASSWORD");
        
        // Assert
        Assert.AreEqual("secret-manager-value", value);
    }
    
    [TestMethod]
    public void Precedence_EnvVarOverDefault()
    {
        var resolver = new ConfigurationResolver(
            new NoSecretManager(),
            new[] { ("LOG_LEVEL", "INFO") }
        );
        
        var value = resolver.Resolve("LOG_LEVEL");  // Default is DEBUG
        Assert.AreEqual("INFO", value);  // Env var wins
    }
}
```

---

## 7. Documentation

Every environment should document its precedence chain:

```
Production Configuration Precedence
===================================

1. Runtime Overrides
   - Emergency timeout override via admin API
   - Usually empty (not used)

2. Secret Manager (AWS Secrets Manager)
   - DB_PASSWORD: prod-db-pass-xyz
   - OAUTH_CLIENT_SECRET: prod-oauth-xyz

3. Environment Variables (set in deployment manifest)
   - LOG_LEVEL: WARN
   - TRACE_ENABLED: false
   - DB_HOST: postgres.prod.internal

4. .env files
   - Not used in production (security)

5. Defaults (from code)
   - CACHE_TTL: 3600
   - DB_POOL_SIZE: 10

Result: Production config is mix of (SM → Env → Defaults)
```

---

## References

- https://12factor.net/config

**Next:** [VALID-2: CI Configuration Safety Checks](valid-ci-checks.md)

# VALID-1: Startup Validation Gate

**Status:** Published | **Version:** 1.0 | **Date:** 2026-06-22

---

## 1. Overview

Implement fail-fast checks for missing required config and secrets on service startup with clear, actionable diagnostic messages.

---

## 2. Validation Checklist

```
On Service Startup:
  ✓ Required keys present? (all must exist)
  ✓ Type validation? (string matches pattern, int in range)
  ✓ Dependency validation? (if A set, B required)
  ✓ Environment-specific rules? (prod has strict requirements)
  ✓ All validations pass?
    → YES: Log "Configuration valid" + Continue startup
    → NO: Log diagnostics + Exit with code 1
```

---

## 3. Fail-Fast Implementation

### 3.1 C#

```csharp
public class StartupValidator
{
    private readonly IConfiguration _config;
    private readonly ConfigurationSchema _schema;
    private readonly ILogger _logger;
    
    public void ValidateOnStartup()
    {
        var errors = new List<string>();
        
        // Check required keys
        foreach (var key in _schema.RequiredKeys)
        {
            if (string.IsNullOrEmpty(_config[key]))
            {
                errors.Add($"Missing required configuration: {key}");
            }
        }
        
        // Type validation
        if (_config["DB_POOL_SIZE"] is not null)
        {
            if (!int.TryParse(_config["DB_POOL_SIZE"], out var poolSize))
            {
                errors.Add($"DB_POOL_SIZE must be integer, got: {_config["DB_POOL_SIZE"]}");
            }
            else if (poolSize < 1 || poolSize > 100)
            {
                errors.Add($"DB_POOL_SIZE must be 1-100, got: {poolSize}");
            }
        }
        
        // Dependency validation
        if (!string.IsNullOrEmpty(_config["OAUTH_CLIENT_ID"]))
        {
            if (string.IsNullOrEmpty(_config["OAUTH_CLIENT_SECRET"]))
            {
                errors.Add("OAUTH_CLIENT_ID set but OAUTH_CLIENT_SECRET missing");
            }
        }
        
        if (errors.Any())
        {
            var diagnostic = GenerateDiagnostic(errors);
            _logger.LogError("Configuration validation failed:\n{Diagnostic}", diagnostic);
            Environment.Exit(1);
        }
        
        _logger.LogInformation("Configuration validation passed");
    }
    
    private string GenerateDiagnostic(List<string> errors)
    {
        var sb = new StringBuilder();
        sb.AppendLine("❌ Configuration Validation Failed");
        sb.AppendLine($"\nErrors ({errors.Count}):");
        
        foreach (var error in errors)
        {
            sb.AppendLine($"  • {error}");
        }
        
        sb.AppendLine("\nHow to fix:");
        sb.AppendLine("  1. Check .env.example for required keys");
        sb.AppendLine("  2. Set missing values in .env.local or secret manager");
        sb.AppendLine("  3. Verify types and ranges");
        
        return sb.ToString();
    }
}
```

### 3.2 TypeScript

```typescript
import { z } from 'zod';

const configSchema = z.object({
  SERVICE_NAME: z.string().min(1),
  DB_HOST: z.string().min(1),
  DB_NAME: z.string().regex(/^[a-z]/),
  DB_PASSWORD: z.string().min(12),
  DB_POOL_SIZE: z.coerce.number().int().min(1).max(100).default(10),
}).strict();  // Fail on extra keys

export function validateStartup(config: Record<string, any>): void {
  const result = configSchema.safeParse(config);
  
  if (!result.success) {
    const errors = result.error.errors;
    
    console.error('❌ Configuration Validation Failed\n');
    console.error(`Errors (${errors.length}):`);
    
    errors.forEach(error => {
      const path = error.path.join('.');
      console.error(`  • ${path}: ${error.message}`);
    });
    
    console.error('\nHow to fix:');
    console.error('  1. Check .env.example for required keys');
    console.error('  2. Set missing values in .env.local');
    console.error('  3. Verify types and ranges\n');
    
    process.exit(1);
  }
  
  console.log('✓ Configuration validation passed');
}
```

---

## 4. Error Message Examples

```
❌ Configuration Validation Failed

Errors (3):
  • Missing required configuration: DB_PASSWORD
  • DB_POOL_SIZE must be 1-100, got: 200
  • OAUTH_CLIENT_ID set but OAUTH_CLIENT_SECRET missing

How to fix:
  1. Check .env.example for required keys
  2. Set missing values in .env.local or secret manager
  3. Verify types and ranges

See: https://wiki/config/booking-service for full schema
```

---

## 5. Health Check Endpoint

```csharp
[ApiController]
[Route("api/health")]
public class HealthController : ControllerBase
{
    private readonly ConfigurationValidator _validator;
    
    [HttpGet]
    public IActionResult Health()
    {
        var (isHealthy, diagnostics) = _validator.ValidateHealth();
        
        return isHealthy 
            ? Ok(new { status = "healthy", diagnostics })
            : StatusCode(503, new { status = "degraded", diagnostics });
    }
}
```

---

## 6. Testing Validation

```csharp
[TestClass]
public class StartupValidationTests
{
    [TestMethod]
    public void ValidateOnStartup_MissingRequired_Fails()
    {
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string>
            {
                { "SERVICE_NAME", "test" }
                // Missing DB_HOST, DB_NAME, etc
            })
            .Build();
        
        var validator = new StartupValidator(config);
        
        Assert.ThrowsException<ApplicationException>(
            () => validator.ValidateOnStartup()
        );
    }
}
```

---

## 7. Startup Timing

- Configuration validation: < 100ms
- Service ready to serve: < 1 second
- Total startup: < 5 seconds

---

## References

- https://12factor.net/config

**Next:** [VALID-2: CI Configuration Safety Checks](valid-ci-checks.md)

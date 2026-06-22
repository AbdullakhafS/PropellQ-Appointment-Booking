# LOG-1: Structured Log Schema Standard

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** Backend engineers, DevOps, platform teams

---

## 1. Overview

This document defines the standard JSON schema for all structured logs across the PropellQ platform. All services MUST emit logs conforming to this schema to enable:
- Centralized log aggregation and searchability
- End-to-end correlation tracing
- Automated incident detection and response
- Compliance auditing and retention enforcement

**Scope:**
- Application logs (Info, Warning, Error, Debug)
- Audit logs (security events, data access)
- Infrastructure logs (deployment, system health)

---

## 2. Core Log Schema

### 2.1 Required Fields (All Logs)

Every log event MUST include these fields:

```json
{
  "timestamp": "2026-06-22T14:30:00.123Z",
  "level": "INFO",
  "logger": "AppointmentService.Controllers.AppointmentsController",
  "message": "Appointment created successfully",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "traceId": "0af7651916cd43dd8448eb211c80319c",
  "spanId": "b7ad6b7169203331",
  "environment": "production",
  "service": "appointment-service",
  "version": "1.2.0",
  "hostname": "pod-appointment-001",
  "process": {
    "pid": 12345,
    "name": "dotnet"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO8601 | Yes | UTC timestamp when log was created (YYYY-MM-DDTHH:mm:ss.SSSZ) |
| `level` | Enum | Yes | Log severity level (see § 2.2) |
| `logger` | String | Yes | Source logger name (fully qualified class name) |
| `message` | String | Yes | Human-readable log message |
| `correlationId` | UUID | Yes | End-to-end request/operation correlation ID |
| `traceId` | String | Yes | OpenTelemetry trace ID (hex string, 32 chars) |
| `spanId` | String | Yes | OpenTelemetry span ID (hex string, 16 chars) |
| `environment` | Enum | Yes | Deployment environment (development, staging, production) |
| `service` | String | Yes | Service name (kebab-case, e.g., appointment-service) |
| `version` | SemVer | Yes | Service version (MAJOR.MINOR.PATCH) |
| `hostname` | String | Yes | Pod/instance hostname or node name |
| `process` | Object | Yes | Process metadata (pid, name, thread) |

### 2.2 Log Level Hierarchy

| Level | Severity | Use Case |
|-------|----------|----------|
| **DEBUG** | 10 | Detailed diagnostic information for developers during troubleshooting |
| **INFO** | 20 | General informational messages about application flow (default for prod) |
| **WARN** | 30 | Warning conditions that don't prevent operation (deprecated APIs, slow queries) |
| **ERROR** | 40 | Error conditions that prevent successful operation completion |
| **CRITICAL** | 50 | System-level failures requiring immediate attention (security breach, data corruption) |

**Guidelines:**
- Production: INFO level minimum (DEBUG disabled by default)
- Staging: DEBUG level recommended for troubleshooting
- Development: DEBUG level enabled
- Never use CRITICAL for recoverable errors (use ERROR)
- Use WARN for degraded but operational states

### 2.3 Context Fields (Conditional)

Include these fields when applicable:

```json
{
  "context": {
    "actor": {
      "userId": "user-123",
      "tenantId": "tenant-456",
      "roles": ["CLINICIAN", "ADMIN"],
      "email": "dr.smith@propellq.local"
    },
    "request": {
      "method": "POST",
      "path": "/api/v1/appointments",
      "statusCode": 201,
      "duration_ms": 145,
      "queryParams": {
        "filter_status": "PENDING"
      }
    },
    "error": {
      "type": "ValidationException",
      "code": "VALIDATION_ERROR",
      "message": "Patient ID is required",
      "stackTrace": "at AppointmentService.Validators.ValidateAsync() ..."
    },
    "performance": {
      "dbQueryDuration_ms": 45,
      "cacheHit": true,
      "memoryUsage_mb": 256,
      "cpuPercent": 22.5
    },
    "business": {
      "appointmentId": "apt-001",
      "patientId": "pat-123",
      "operation": "CREATE_APPOINTMENT",
      "outcome": "SUCCESS"
    }
  }
}
```

#### 2.3.1 Actor Context

Include when log relates to a user action:

```json
"actor": {
  "userId": "user-123",
  "tenantId": "tenant-456",
  "roles": ["CLINICIAN"],
  "email": "dr.smith@propellq.local",
  "ipAddress": "192.168.1.100"
}
```

**Mandatory for:** User logins, data access, permission changes, audit events

#### 2.3.2 Request Context

Include for HTTP request-related logs:

```json
"request": {
  "method": "POST",
  "path": "/api/v1/appointments",
  "statusCode": 201,
  "duration_ms": 145,
  "queryParams": {
    "page_number": "1",
    "page_size": "20"
  },
  "headers": {
    "user-agent": "AppointmentClient/1.0",
    "content-type": "application/json"
  }
}
```

**Mandatory for:** Request/response pairs, HTTP errors, performance logs

#### 2.3.3 Error Context

Include when log describes an error condition:

```json
"error": {
  "type": "ValidationException",
  "code": "VALIDATION_ERROR",
  "message": "Patient ID is required",
  "stackTrace": "at AppointmentService.Validators.ValidateAsync() line 45\n at ...",
  "innerError": {
    "type": "NullReferenceException",
    "message": "Object reference not set to an instance of an object"
  }
}
```

**Mandatory for:** ERROR and CRITICAL level logs

#### 2.3.4 Performance Context

Include for performance-sensitive operations:

```json
"performance": {
  "dbQueryDuration_ms": 45,
  "externalApiDuration_ms": 120,
  "cacheHit": true,
  "cacheHitRate": 0.85,
  "memoryUsage_mb": 256,
  "cpuPercent": 22.5,
  "gc_collections": 2
}
```

**Mandatory for:** Database queries > 100ms, external API calls, operations exceeding thresholds

#### 2.3.5 Business Context

Include for business-critical events:

```json
"business": {
  "appointmentId": "apt-001",
  "patientId": "pat-123",
  "clinicianId": "clin-456",
  "operation": "CREATE_APPOINTMENT",
  "outcome": "SUCCESS",
  "value_usd": 150.00,
  "workflowStep": "CONFIRMATION"
}
```

**Mandatory for:** Appointment creation/update/cancellation, payment processing, critical state changes

---

## 3. Severity-Based Schema Variations

### 3.1 Info Log (Typical)

```json
{
  "timestamp": "2026-06-22T14:30:00.123Z",
  "level": "INFO",
  "logger": "AppointmentService.Controllers.AppointmentsController",
  "message": "Appointment created successfully",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "traceId": "0af7651916cd43dd8448eb211c80319c",
  "spanId": "b7ad6b7169203331",
  "environment": "production",
  "service": "appointment-service",
  "version": "1.2.0",
  "hostname": "pod-appointment-001",
  "process": { "pid": 12345, "name": "dotnet" },
  "context": {
    "actor": {
      "userId": "user-123",
      "tenantId": "tenant-456",
      "roles": ["CLINICIAN"]
    },
    "request": {
      "method": "POST",
      "path": "/api/v1/appointments",
      "statusCode": 201,
      "duration_ms": 145
    },
    "business": {
      "appointmentId": "apt-001",
      "operation": "CREATE_APPOINTMENT",
      "outcome": "SUCCESS"
    }
  }
}
```

### 3.2 Warning Log

```json
{
  "timestamp": "2026-06-22T14:31:00.456Z",
  "level": "WARN",
  "logger": "AppointmentService.Services.ClinicalDataService",
  "message": "Query performance degradation detected",
  "correlationId": "550e8400-e29b-41d4-a716-446655440001",
  "traceId": "1af7651916cd43dd8448eb211c80319d",
  "spanId": "c7ad6b7169203332",
  "environment": "production",
  "service": "appointment-service",
  "version": "1.2.0",
  "hostname": "pod-appointment-001",
  "process": { "pid": 12345, "name": "dotnet" },
  "context": {
    "request": {
      "method": "GET",
      "path": "/api/v1/appointments",
      "duration_ms": 2500
    },
    "performance": {
      "dbQueryDuration_ms": 2400,
      "threshold_ms": 1000,
      "cacheHit": false
    }
  }
}
```

### 3.3 Error Log

```json
{
  "timestamp": "2026-06-22T14:32:00.789Z",
  "level": "ERROR",
  "logger": "AppointmentService.Controllers.AppointmentsController",
  "message": "Failed to create appointment: validation error",
  "correlationId": "550e8400-e29b-41d4-a716-446655440002",
  "traceId": "2af7651916cd43dd8448eb211c80319e",
  "spanId": "d7ad6b7169203333",
  "environment": "production",
  "service": "appointment-service",
  "version": "1.2.0",
  "hostname": "pod-appointment-001",
  "process": { "pid": 12345, "name": "dotnet" },
  "context": {
    "actor": {
      "userId": "user-123",
      "tenantId": "tenant-456"
    },
    "request": {
      "method": "POST",
      "path": "/api/v1/appointments",
      "statusCode": 400
    },
    "error": {
      "type": "ValidationException",
      "code": "VALIDATION_ERROR",
      "message": "Patient ID is required",
      "stackTrace": "at AppointmentService.Validators.CreateAppointmentValidator.ValidateAsync() line 45\n at AppointmentService.Controllers.AppointmentsController.CreateAppointment() line 120"
    }
  }
}
```

### 3.4 Audit Log (Security Event)

```json
{
  "timestamp": "2026-06-22T14:33:00.012Z",
  "level": "INFO",
  "logger": "AuditService",
  "message": "User accessed sensitive patient data",
  "correlationId": "550e8400-e29b-41d4-a716-446655440003",
  "traceId": "3af7651916cd43dd8448eb211c80319f",
  "spanId": "e7ad6b7169203334",
  "environment": "production",
  "service": "audit-service",
  "version": "1.0.0",
  "hostname": "pod-audit-001",
  "process": { "pid": 54321, "name": "dotnet" },
  "context": {
    "actor": {
      "userId": "user-123",
      "tenantId": "tenant-456",
      "roles": ["CLINICIAN"],
      "email": "dr.smith@propellq.local",
      "ipAddress": "192.168.1.100"
    },
    "business": {
      "auditEventType": "DATA_ACCESS",
      "resourceType": "PatientRecord",
      "resourceId": "pat-123",
      "action": "READ",
      "outcome": "SUCCESS",
      "timestamp": "2026-06-22T14:33:00Z"
    }
  }
}
```

---

## 4. Field Naming Conventions

| Category | Pattern | Example |
|----------|---------|---------|
| Time durations | `{metric}_ms` or `{metric}_s` | `duration_ms`, `cacheHit_ms` |
| Counts | `{metric}_count` or just plural | `errorCount`, `records` |
| Rates/Percentages | `{metric}_percent` or `{metric}Rate` | `cpuPercent`, `hitRate` |
| IDs | `{entity}Id` | `userId`, `appointmentId`, `tenantId` |
| Flags/Booleans | Plain name or `is{Property}` | `cacheHit`, `isRetry` |
| Timestamps | `{event}At` or explicit `_timestamp` | `createdAt`, `error_timestamp` |

---

## 5. Redaction and Masking Rules

### 5.1 Fields That MUST Be Redacted

These fields contain sensitive data and MUST be masked in all logs:

| Field Pattern | Content Type | Masking Rule |
|---------------|--------------|--------------|
| `*password*` | Credentials | Remove entirely |
| `*token*`, `*secret*` | Credentials | Remove entirely |
| `*apiKey*` | Credentials | Remove entirely |
| `*ssn*`, `*socialSecurityNumber*` | PII | Mask all but last 4: `XXX-XX-1234` |
| `*creditCard*`, `*cardNumber*` | PII | Mask all but last 4: `****-****-****-1234` |
| `*email*` | PII | Hash domain, keep first letter: `a****@example.com` |
| `*phone*`, `*phoneNumber*` | PII | Mask all but last 4: `(XXX) XXX-1234` |
| `*ipAddress*` | PII | Last octet only: `192.168.1.***` |
| `*medicalRecord*`, `*diagnosis*` | PHI | Full mask: `[REDACTED_PHI]` |
| `*medication*` | PHI | Full mask: `[REDACTED_MEDICATION]` |
| `*labResult*` | PHI | Full mask: `[REDACTED_LAB_RESULT]` |

### 5.2 Redaction Examples

**Before Redaction:**
```json
{
  "context": {
    "actor": {
      "email": "dr.smith@hospital.com",
      "ssn": "123-45-6789"
    },
    "error": {
      "message": "Database connection failed: password=secret123"
    }
  }
}
```

**After Redaction:**
```json
{
  "context": {
    "actor": {
      "email": "d****@hospital.com",
      "ssn": "XXX-XX-6789"
    },
    "error": {
      "message": "Database connection failed: password=[REDACTED_CREDENTIAL]"
    }
  }
}
```

---

## 6. Implementation Patterns

### 6.1 C# Structured Logging Example

```csharp
using Serilog;
using Serilog.Context;

public class AppointmentService
{
    private readonly ILogger<AppointmentService> _logger;

    public AppointmentService(ILogger<AppointmentService> logger)
    {
        _logger = logger;
    }

    public async Task<AppointmentDto> CreateAppointmentAsync(
        string correlationId,
        CreateAppointmentRequest request,
        string userId)
    {
        using (LogContext.PushProperty("correlationId", correlationId))
        using (LogContext.PushProperty("userId", userId))
        using (LogContext.PushProperty("tenantId", request.TenantId))
        {
            var stopwatch = Stopwatch.StartNew();

            try
            {
                _logger.LogInformation(
                    "Creating appointment for patient {PatientId}",
                    request.PatientId);

                // Appointment creation logic
                var appointment = await CreateAsync(request);

                stopwatch.Stop();

                _logger.LogInformation(
                    "Appointment created successfully. " +
                    "AppointmentId: {AppointmentId}, Duration: {Duration}ms",
                    appointment.Id,
                    stopwatch.ElapsedMilliseconds);

                return appointment;
            }
            catch (ValidationException ex)
            {
                _logger.LogError(ex,
                    "Appointment creation validation failed. " +
                    "Errors: {@ValidationErrors}",
                    ex.ValidationErrors);
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Unexpected error creating appointment");
                throw;
            }
        }
    }
}
```

### 6.2 Serilog Configuration (appsettings.json)

```json
{
  "Serilog": {
    "MinimumLevel": "Information",
    "Enrich": [
      "FromLogContext",
      "WithMachineName",
      "WithThreadId",
      "WithProperty"
    ],
    "WriteTo": [
      {
        "Name": "Console",
        "Args": {
          "outputTemplate": "{Timestamp:yyyy-MM-dd HH:mm:ss.fff zzz} [{Level:u3}] {Message:lj}{NewLine}{Exception}"
        }
      },
      {
        "Name": "File",
        "Args": {
          "path": "logs/app.json",
          "formatter": "Serilog.Formatting.Json.JsonFormatter"
        }
      }
    ],
    "Properties": {
      "Service": "appointment-service",
      "Environment": "production",
      "Version": "1.2.0"
    }
  }
}
```

### 6.3 TypeScript Structured Logging Example

```typescript
import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DDTHH:mm:ss.SSSZ' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'appointment-service',
    version: '1.2.0',
    environment: process.env.NODE_ENV || 'development'
  },
  transports: [
    new winston.transports.File({ filename: 'logs/error.json', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.json' })
  ]
});

// Log with context
function logWithContext(correlationId: string, userId: string) {
  logger.info('Appointment created', {
    correlationId,
    context: {
      actor: { userId },
      business: {
        appointmentId: 'apt-001',
        operation: 'CREATE_APPOINTMENT',
        outcome: 'SUCCESS'
      }
    }
  });
}
```

---

## 7. Validation Rules

All logs MUST satisfy these rules:

- ✅ Contains all required fields (§ 2.1)
- ✅ Level is one of: DEBUG, INFO, WARN, ERROR, CRITICAL
- ✅ Timestamp is valid ISO8601 UTC
- ✅ correlationId is valid UUID v4
- ✅ traceId and spanId match OpenTelemetry format
- ✅ No sensitive fields left unmasked (§ 5)
- ✅ Message is concise and actionable (<500 chars)
- ✅ All numbers are not null/undefined
- ✅ No circular references in nested objects

---

## 8. Best Practices

### 8.1 What to Log

✅ **DO log:**
- Application state transitions (service started, configuration loaded)
- User-initiated actions and outcomes
- Performance metrics and thresholds exceeded
- Error conditions with context
- Security events (login, permission changes, data access)
- Business milestones (appointment created, payment processed)

### 8.2 What NOT to Log

❌ **DON'T log:**
- Passwords, API keys, tokens, secrets
- Personally identifiable information (PII) unless masked
- Protected health information (PHI) unless justified
- Raw request/response bodies (log headers/summaries only)
- Stack traces for expected exceptions
- Debug variables in production logs

### 8.3 Log Message Guidelines

| Pattern | Example |
|---------|---------|
| **Action completed** | "Appointment created successfully" |
| **Error with context** | "Failed to create appointment: patient not found (pat-123)" |
| **Performance threshold** | "Slow database query: 2500ms (threshold: 1000ms)" |
| **State transition** | "Service status changed: RUNNING → DEGRADED" |

---

## 9. Checklist for Services

When implementing structured logging:

- [ ] All logs conform to schema (§ 2)
- [ ] Correlation ID included in every log
- [ ] Sensitive fields masked (§ 5)
- [ ] Performance logs included for slow operations
- [ ] Error logs include stack traces and context
- [ ] Audit logs capture security events
- [ ] Log level appropriate to message severity
- [ ] Message is concise and actionable
- [ ] Tests validate log output format
- [ ] CI/CD validates logs for security compliance

---

## 10. References

- Structured Logging Best Practices: https://propellq.local/docs/logging
- OpenTelemetry Specification: https://opentelemetry.io/docs/reference/specification/
- Correlation ID Propagation: `LOG-2`
- Redaction Validation: `SEC-1`
- Log Pipeline: `PIPE-1`

---

**Next:** [LOG-2: Correlation Propagation Pattern](correlation-propagation-pattern.md)

# MID-1: Shared Error/Exception Middleware Contract

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes the middleware contract for error handling and exception processing. All services MUST implement shared middleware that catches validation errors, authentication failures, and unhandled exceptions, then emits responses in the standard error envelope format defined in STD-1.

The error middleware is a cross-cutting concern that ensures consistent error handling across all services, eliminating duplicate error handling logic.

---

## 2. Middleware Contract Interface

### 2.1 Middleware Signature (C#/.NET)

```csharp
public interface IErrorHandlingMiddleware
{
    /// <summary>
    /// Asynchronously processes HTTP request and catches all exceptions.
    /// </summary>
    /// <param name="context">HTTP context containing request and response</param>
    /// <param name="next">Next middleware in the pipeline</param>
    Task InvokeAsync(HttpContext context, RequestDelegate next);
}

public interface IExceptionHandler
{
    /// <summary>
    /// Determines if this handler can process the exception.
    /// </summary>
    bool CanHandle(Exception ex);

    /// <summary>
    /// Converts exception to standard error response envelope.
    /// </summary>
    /// <param name="ex">The exception to handle</param>
    /// <param name="context">HTTP context for additional context</param>
    ErrorResponse Handle(Exception ex, HttpContext context);
}
```

### 2.2 Middleware Signature (TypeScript/Node)

```typescript
export interface ErrorHandlingMiddleware {
  (
    err: Error,
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void>;
}

export interface ExceptionHandler {
  canHandle(err: Error): boolean;
  handle(err: Error, context: RequestContext): ErrorResponse;
}
```

---

## 3. Error Classification and Handling

### 3.1 Exception Categories

The middleware MUST classify exceptions into these categories:

| Category | Examples | HTTP Status | Error Code |
|----------|----------|-------------|-----------|
| **Validation Errors** | Schema validation, format validation, business rules | 400 | VALIDATION_ERROR |
| **Authentication Errors** | Missing token, invalid token, expired token | 401 | UNAUTHORIZED |
| **Authorization Errors** | Insufficient permissions, resource access denied | 403 | FORBIDDEN |
| **Not Found** | Resource doesn't exist, path not found | 404 | NOT_FOUND |
| **Conflict Errors** | Duplicate key, concurrent modification, state conflict | 409 | RESOURCE_CONFLICT |
| **Rate Limiting** | Rate limit exceeded, quota exhausted | 429 | RATE_LIMITED |
| **Unprocessable Entity** | Request semantically invalid, business logic violation | 422 | UNPROCESSABLE_ENTITY |
| **Internal Server Error** | Database failure, timeout, unexpected exception | 500 | INTERNAL_SERVER_ERROR |
| **External Service Error** | Third-party API failure, dependency unavailable | 502/503 | INVALID_GATEWAY / SERVICE_UNAVAILABLE |

### 3.2 Exception Handler Registration

Services MUST register exception handlers in priority order:

```csharp
// C# Example
services.AddScoped<IExceptionHandler, ValidationExceptionHandler>();
services.AddScoped<IExceptionHandler, AuthenticationExceptionHandler>();
services.AddScoped<IExceptionHandler, AuthorizationExceptionHandler>();
services.AddScoped<IExceptionHandler, NotFoundExceptionHandler>();
services.AddScoped<IExceptionHandler, ConflictExceptionHandler>();
services.AddScoped<IExceptionHandler, RateLimitExceptionHandler>();
services.AddScoped<IExceptionHandler, UnprocessableEntityExceptionHandler>();
services.AddScoped<IExceptionHandler, InternalServerErrorHandler>();
```

---

## 4. Validation Error Handling

### 4.1 Validation Exception Handler

All validation frameworks (FluentValidation, DataAnnotations, etc.) MUST be caught and converted:

**Input (Validation Failure):**
```csharp
var validator = new AppointmentValidator();
var result = await validator.ValidateAsync(appointment);
if (!result.IsValid)
{
    throw new ValidationException(result.Errors);
}
```

**Output (Standard Error Envelope):**
```json
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "scheduledTime",
        "issue": "Must be in the future",
        "code": "ScheduledTimeInPast",
        "value": "2026-05-01T10:00:00Z"
      },
      {
        "field": "appointmentType",
        "issue": "Invalid appointment type",
        "code": "InvalidEnumValue",
        "value": "INVALID_TYPE"
      }
    ]
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "requestId": "987f6543-e89b-12d3-a456-426614174111",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

### 4.2 Validation Error Detail Rules

Each validation error detail MUST include:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `field` | Yes | string | JSON path or field name |
| `issue` | Yes | string | Human-readable error message |
| `code` | No | string | Machine-readable error code (e.g., Required, InvalidFormat) |
| `value` | No | any | The problematic value (redact PII/secrets) |

### 4.3 Validation Middleware Implementation Guidance

```csharp
public class ValidationExceptionHandler : IExceptionHandler
{
    public bool CanHandle(Exception ex) =>
        ex is ValidationException || ex is FluentValidation.ValidationException;

    public ErrorResponse Handle(Exception ex, HttpContext context)
    {
        var errors = new List<ErrorDetail>();
        
        if (ex is FluentValidation.ValidationException fvEx)
        {
            errors = fvEx.Errors
                .Select(f => new ErrorDetail
                {
                    Field = f.PropertyName,
                    Issue = f.ErrorMessage,
                    Code = f.ErrorCode,
                    Value = f.AttemptedValue
                })
                .ToList();
        }

        return new ErrorResponse
        {
            StatusCode = 400,
            Success = false,
            Error = new Error
            {
                Code = "VALIDATION_ERROR",
                Message = "Request validation failed",
                Details = errors
            },
            CorrelationId = context.GetCorrelationId(),
            RequestId = context.GetRequestId(),
            Timestamp = DateTime.UtcNow
        };
    }
}
```

---

## 5. Authentication Error Handling

### 5.1 Authentication Exception Handler

Invalid or missing tokens MUST return 401 UNAUTHORIZED:

**Input (Missing Token):**
```
GET /api/v1/appointments
(No Authorization header)
```

**Output:**
```json
{
  "statusCode": 401,
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid authentication token"
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

**Input (Expired Token):**
```
GET /api/v1/appointments
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
(token expired 1 hour ago)
```

**Output:**
```json
{
  "statusCode": 401,
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication token has expired",
    "details": [
      {
        "field": "Authorization",
        "issue": "Token expired at 2026-06-22T13:30:00Z"
      }
    ]
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

### 5.2 Authentication Error Detail Rules

For authentication errors, include:
- **Field:** "Authorization"
- **Issue:** Reason for authentication failure (expired, invalid signature, malformed, etc.)
- **Value:** NEVER include the actual token

### 5.3 Authentication Middleware Implementation

```csharp
public class AuthenticationExceptionHandler : IExceptionHandler
{
    public bool CanHandle(Exception ex) =>
        ex is UnauthorizedAccessException ||
        ex is SecurityTokenException ||
        ex.InnerException is SecurityTokenException;

    public ErrorResponse Handle(Exception ex, HttpContext context)
    {
        string message = ex switch
        {
            SecurityTokenExpiredException stEx =>
                $"Authentication token has expired",
            SecurityTokenInvalidSignatureException =>
                "Authentication token has invalid signature",
            SecurityTokenNotYetValidException =>
                "Authentication token is not yet valid",
            _ => "Missing or invalid authentication token"
        };

        var details = new List<ErrorDetail>
        {
            new ErrorDetail
            {
                Field = "Authorization",
                Issue = message
            }
        };

        return new ErrorResponse
        {
            StatusCode = 401,
            Success = false,
            Error = new Error
            {
                Code = "UNAUTHORIZED",
                Message = message,
                Details = details
            },
            CorrelationId = context.GetCorrelationId(),
            Timestamp = DateTime.UtcNow
        };
    }
}
```

---

## 6. Authorization Error Handling

### 6.1 Authorization Exception Handler

Insufficient permissions MUST return 403 FORBIDDEN:

**Input (Insufficient Permission):**
```
GET /api/v1/admin/settings
Authorization: Bearer {clinician_token}
(clinician_token has CLINICIAN role, endpoint requires ADMIN role)
```

**Output:**
```json
{
  "statusCode": 403,
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions to access this resource",
    "details": [
      {
        "field": "Authorization",
        "issue": "User role CLINICIAN is not authorized for this operation",
        "requiredRoles": ["ADMIN"]
      }
    ]
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

### 6.2 Authorization Middleware Implementation

```csharp
public class AuthorizationExceptionHandler : IExceptionHandler
{
    public bool CanHandle(Exception ex) =>
        ex is ForbiddenAccessException ||
        ex is UnauthorizedAccessException && ex.Message.Contains("Permission");

    public ErrorResponse Handle(Exception ex, HttpContext context)
    {
        var userClaims = context.User.Claims;
        var userRole = userClaims.FirstOrDefault(c => c.Type == "role")?.Value;

        return new ErrorResponse
        {
            StatusCode = 403,
            Success = false,
            Error = new Error
            {
                Code = "FORBIDDEN",
                Message = "Insufficient permissions to access this resource",
                Details = new List<ErrorDetail>
                {
                    new ErrorDetail
                    {
                        Field = "Authorization",
                        Issue = $"User role {userRole} is not authorized for this operation"
                    }
                }
            },
            CorrelationId = context.GetCorrelationId(),
            Timestamp = DateTime.UtcNow
        };
    }
}
```

---

## 7. Unhandled Exception Handling

### 7.1 Generic Exception Handler

Unexpected exceptions MUST be logged and converted to safe error response:

**Input (Database Exception):**
```
NullReferenceException in repository layer
at RepositoryImpl.GetAppointment(string id)
```

**Output (Client sees generic message, details logged):**
```json
{
  "statusCode": 500,
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred. Contact support with your request ID."
  },
  "correlationId": "123e4567-e89b-12d3-a456-426614174000",
  "requestId": "987f6543-e89b-12d3-a456-426614174111",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

**Server Log (Detailed trace):**
```
[ERROR] CorrelationId: 123e4567-e89b-12d3-a456-426614174000
RequestId: 987f6543-e89b-12d3-a456-426614174111
UserId: user-123
Endpoint: GET /api/v1/appointments/apt-001
Exception: System.NullReferenceException: Object reference not set to an instance of an object.
   at RepositoryImpl.GetAppointment(String id) in /src/Repository.cs:line 42
   at AppointmentService.GetAsync(String id)
Stack trace...
```

### 7.2 Generic Exception Handler Implementation

```csharp
public class InternalServerErrorHandler : IExceptionHandler
{
    private readonly ILogger<InternalServerErrorHandler> _logger;

    public InternalServerErrorHandler(ILogger<InternalServerErrorHandler> logger)
    {
        _logger = logger;
    }

    public bool CanHandle(Exception ex) => true; // Catches all

    public ErrorResponse Handle(Exception ex, HttpContext context)
    {
        var correlationId = context.GetCorrelationId();
        var requestId = context.GetRequestId();

        _logger.LogError(ex,
            "Unhandled exception. CorrelationId: {CorrelationId}, RequestId: {RequestId}, UserId: {UserId}, Endpoint: {Endpoint}",
            correlationId,
            requestId,
            context.User?.FindFirst("sub")?.Value,
            $"{context.Request.Method} {context.Request.Path}");

        return new ErrorResponse
        {
            StatusCode = 500,
            Success = false,
            Error = new Error
            {
                Code = "INTERNAL_SERVER_ERROR",
                Message = "An unexpected error occurred. Contact support with your request ID."
            },
            CorrelationId = correlationId,
            RequestId = requestId,
            Timestamp = DateTime.UtcNow
        };
    }
}
```

---

## 8. Middleware Integration Pattern

### 8.1 Middleware Registration (C#)

```csharp
// In Program.cs or Startup.cs
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    // Error handling middleware MUST be first in pipeline
    app.UseMiddleware<ErrorHandlingMiddleware>();
    
    // Other middleware
    app.UseAuthentication();
    app.UseAuthorization();
    app.UseRouting();
    
    app.UseEndpoints(endpoints => endpoints.MapControllers());
}
```

### 8.2 Middleware Implementation (C#)

```csharp
public class ErrorHandlingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ErrorHandlingMiddleware> _logger;
    private readonly IEnumerable<IExceptionHandler> _handlers;

    public ErrorHandlingMiddleware(
        RequestDelegate next,
        ILogger<ErrorHandlingMiddleware> logger,
        IEnumerable<IExceptionHandler> handlers)
    {
        _next = next;
        _logger = logger;
        _handlers = handlers.OrderByPriority(); // Custom method
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            // Find first handler that can process this exception
            var handler = _handlers.FirstOrDefault(h => h.CanHandle(ex));
            
            if (handler == null)
            {
                throw; // Re-throw if no handler found
            }

            var errorResponse = handler.Handle(ex, context);
            
            context.Response.StatusCode = errorResponse.StatusCode;
            context.Response.ContentType = "application/json";

            await context.Response.WriteAsJsonAsync(errorResponse);
        }
    }
}
```

---

## 9. Correlation ID Propagation

### 9.1 Correlation ID Extraction

Middleware MUST extract or generate correlation ID:

```csharp
public static class CorrelationIdExtensions
{
    public static string GetCorrelationId(this HttpContext context)
    {
        const string headerName = "X-Correlation-ID";
        
        if (context.Request.Headers.TryGetValue(headerName, out var correlationId))
        {
            return correlationId.ToString();
        }

        // Generate new if not provided
        return context.Items["CorrelationId"] as string ?? Guid.NewGuid().ToString();
    }

    public static string GetRequestId(this HttpContext context)
    {
        const string headerName = "X-Request-ID";
        
        if (context.Request.Headers.TryGetValue(headerName, out var requestId))
        {
            return requestId.ToString();
        }

        // Generate new if not provided
        return context.Items["RequestId"] as string ?? Guid.NewGuid().ToString();
    }
}
```

### 9.2 Correlation ID Propagation

Middleware MUST ensure correlation IDs are available in logs:

```csharp
public class CorrelationIdMiddleware
{
    private readonly RequestDelegate _next;

    public CorrelationIdMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context)
    {
        var correlationId = context.GetCorrelationId();
        var requestId = context.GetRequestId();

        // Store in context items for later retrieval
        context.Items["CorrelationId"] = correlationId;
        context.Items["RequestId"] = requestId;

        // Add to response headers
        context.Response.Headers.Add("X-Correlation-ID", correlationId);
        context.Response.Headers.Add("X-Request-ID", requestId);

        // Log start of request
        _logger.LogInformation(
            "Request started. CorrelationId: {CorrelationId}, RequestId: {RequestId}, " +
            "Method: {Method}, Path: {Path}, RemoteIP: {RemoteIP}",
            correlationId, requestId, context.Request.Method, context.Request.Path,
            context.Connection.RemoteIpAddress);

        await _next(context);
    }
}
```

---

## 10. Testing Error Middleware

### 10.1 Unit Test Examples

```csharp
[Fact]
public async Task ValidationException_Returns400WithErrorDetails()
{
    // Arrange
    var handler = new ValidationExceptionHandler();
    var exception = new FluentValidation.ValidationException(new[]
    {
        new ValidationFailure("email", "Invalid email format")
    });
    var context = CreateHttpContext();

    // Act
    var result = handler.Handle(exception, context);

    // Assert
    Assert.Equal(400, result.StatusCode);
    Assert.Equal("VALIDATION_ERROR", result.Error.Code);
    Assert.Single(result.Error.Details);
    Assert.Equal("email", result.Error.Details[0].Field);
}

[Fact]
public async Task UnauthorizedException_Returns401()
{
    // Arrange
    var handler = new AuthenticationExceptionHandler();
    var exception = new UnauthorizedAccessException("Invalid token");
    var context = CreateHttpContext();

    // Act
    var result = handler.Handle(exception, context);

    // Assert
    Assert.Equal(401, result.StatusCode);
    Assert.Equal("UNAUTHORIZED", result.Error.Code);
}
```

---

## 11. Implementation Checklist

Services MUST verify:

- [ ] Error middleware is registered as first middleware in pipeline
- [ ] All validation exceptions return 400 with VALIDATION_ERROR code
- [ ] All authentication exceptions return 401 with UNAUTHORIZED code
- [ ] All authorization exceptions return 403 with FORBIDDEN code
- [ ] All unhandled exceptions return 500 with generic message
- [ ] Error responses follow standard error envelope structure
- [ ] Correlation IDs are extracted or generated and included in response
- [ ] Error details include field, issue, and code fields
- [ ] Sensitive data (tokens, passwords) is redacted from responses
- [ ] Unhandled exceptions are logged with full stack trace
- [ ] All error handlers follow IExceptionHandler interface
- [ ] Error handlers are registered in priority order
- [ ] Integration tests validate error responses

---

## 12. Questions and Feedback

For questions about error middleware:
- Open issue in: `.propel/context/standards/issues/`
- Middleware team: middleware-team@propellq.local
- Next review date: Q3 2026

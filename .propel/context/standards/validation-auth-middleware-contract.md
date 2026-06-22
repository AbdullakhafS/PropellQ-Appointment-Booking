# MID-2: Validation and Auth Hook Contract

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes the contract for request validation middleware and authentication/authorization hook integration points. It defines:
- Validation middleware interface and integration patterns
- Authentication hook contract and claim extraction
- Authorization middleware contract and role/permission evaluation
- Request enrichment patterns with user/tenant context
- Standardized rejection behavior and error propagation

---

## 2. Request Validation Middleware Contract

### 2.1 Validation Middleware Interface

All services MUST implement validation as middleware that:
1. Intercepts incoming requests before reaching controllers/handlers
2. Validates request structure, format, and business rules
3. Enriches context with validation metadata
4. Returns standardized error response if validation fails

**C# Interface:**
```csharp
public interface IRequestValidationMiddleware
{
    /// <summary>
    /// Validates incoming request and short-circuits with 400 if invalid.
    /// </summary>
    Task InvokeAsync(HttpContext context, RequestDelegate next);
}

public interface IRequestValidator<TRequest>
{
    /// <summary>
    /// Validates request payload against schema and business rules.
    /// Returns validation result with error details if invalid.
    /// </summary>
    Task<ValidationResult> ValidateAsync(TRequest request, RequestContext context);
}

public class ValidationResult
{
    public bool IsValid { get; set; }
    public List<ValidationFailure> Errors { get; set; }
}

public class ValidationFailure
{
    public string PropertyName { get; set; }
    public string ErrorMessage { get; set; }
    public string ErrorCode { get; set; }
    public object AttemptedValue { get; set; }
}
```

**TypeScript Interface:**
```typescript
export interface RequestValidationMiddleware {
  (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void>;
}

export interface RequestValidator<T> {
  validate(
    request: T,
    context: RequestContext
  ): Promise<ValidationResult>;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationFailure[];
}

export interface ValidationFailure {
  propertyName: string;
  errorMessage: string;
  errorCode?: string;
  attemptedValue?: any;
}
```

### 2.2 Validation Execution Phases

Request validation MUST execute in this order:

1. **Schema Validation** (automatic)
   - JSON structure, field types, required fields
   - Handled by framework (ASP.NET ModelState, Express middleware, etc.)

2. **Format Validation** (middleware)
   - Email, UUID, ISO-8601 dates, enum values
   - Reusable validators for common formats

3. **Business Logic Validation** (service/controller)
   - Domain-specific rules (e.g., appointment date > now, slot availability)
   - Depends on business context

### 2.3 Validation Middleware Implementation (C#)

```csharp
public class RequestValidationMiddleware : IRequestValidationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<RequestValidationMiddleware> _logger;

    public RequestValidationMiddleware(RequestDelegate next, 
        IServiceProvider serviceProvider,
        ILogger<RequestValidationMiddleware> logger)
    {
        _next = next;
        _serviceProvider = serviceProvider;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        // Skip GET requests (no body validation needed)
        if (context.Request.Method == "GET" || 
            context.Request.Method == "DELETE" ||
            context.Request.Method == "HEAD")
        {
            await _next(context);
            return;
        }

        // Read request body for validation
        var body = await ReadRequestBodyAsync(context.Request);

        if (string.IsNullOrEmpty(body))
        {
            _logger.LogWarning("Empty request body for {Method} {Path}",
                context.Request.Method, context.Request.Path);
            
            context.Response.StatusCode = 400;
            context.Response.ContentType = "application/json";
            await context.Response.WriteAsJsonAsync(new
            {
                statusCode = 400,
                success = false,
                error = new
                {
                    code = "INVALID_REQUEST",
                    message = "Request body cannot be empty"
                }
            });
            return;
        }

        // Parse and validate request
        try
        {
            var requestObject = JsonSerializer.Deserialize<dynamic>(body);
            var validationResult = await ValidateRequestAsync(requestObject, context);

            if (!validationResult.IsValid)
            {
                context.Response.StatusCode = 400;
                context.Response.ContentType = "application/json";
                await context.Response.WriteAsJsonAsync(CreateErrorResponse(
                    validationResult, context));
                return;
            }

            // Store validated request in context
            context.Items["ValidatedRequest"] = requestObject;
        }
        catch (JsonException ex)
        {
            _logger.LogWarning(ex, "JSON parsing error");
            
            context.Response.StatusCode = 400;
            context.Response.ContentType = "application/json";
            await context.Response.WriteAsJsonAsync(new
            {
                statusCode = 400,
                success = false,
                error = new
                {
                    code = "INVALID_REQUEST",
                    message = "Request body is not valid JSON",
                    details = new[] { new { field = "body", issue = ex.Message } }
                }
            });
            return;
        }

        // Continue to next middleware
        await _next(context);
    }

    private async Task<string> ReadRequestBodyAsync(HttpRequest request)
    {
        request.EnableBuffering();
        var reader = new StreamReader(request.Body);
        var body = await reader.ReadToEndAsync();
        request.Body.Position = 0; // Reset position for controller
        return body;
    }

    private async Task<ValidationResult> ValidateRequestAsync(dynamic request, HttpContext context)
    {
        // Determine request type from route/controller
        var validatorType = DetermineValidatorType(context.Request.Path);
        
        if (validatorType == null)
        {
            return new ValidationResult { IsValid = true, Errors = new() };
        }

        // Get validator instance
        var validator = _serviceProvider.GetService(validatorType) as dynamic;
        
        if (validator == null)
        {
            return new ValidationResult { IsValid = true, Errors = new() };
        }

        // Execute validation
        return await validator.ValidateAsync(request, new RequestContext(context));
    }

    private Type DetermineValidatorType(PathString path)
    {
        // Map route paths to validator types
        // Example: /api/v1/appointments -> CreateAppointmentValidator
        return null;
    }

    private dynamic CreateErrorResponse(ValidationResult result, HttpContext context)
    {
        return new
        {
            statusCode = 400,
            success = false,
            error = new
            {
                code = "VALIDATION_ERROR",
                message = "Request validation failed",
                details = result.Errors.Select(e => new
                {
                    field = e.PropertyName,
                    issue = e.ErrorMessage,
                    code = e.ErrorCode,
                    value = e.AttemptedValue
                }).ToList()
            },
            correlationId = context.GetCorrelationId(),
            requestId = context.GetRequestId(),
            timestamp = DateTime.UtcNow
        };
    }
}
```

### 2.4 Common Validators

All services MUST use these reusable validators:

```csharp
public static class CommonValidators
{
    public static IRuleBuilder<T, string> MustBeValidEmail<T>(
        this IRuleBuilder<T, string> ruleBuilder)
    {
        return ruleBuilder
            .EmailAddress()
            .WithErrorCode("InvalidEmailFormat")
            .WithMessage("Must be a valid email address");
    }

    public static IRuleBuilder<T, string> MustBeValidUuid<T>(
        this IRuleBuilder<T, string> ruleBuilder)
    {
        return ruleBuilder
            .Must(id => Guid.TryParse(id, out _))
            .WithErrorCode("InvalidUuidFormat")
            .WithMessage("Must be a valid UUID");
    }

    public static IRuleBuilder<T, DateTime> MustBeInFuture<T>(
        this IRuleBuilder<T, DateTime> ruleBuilder)
    {
        return ruleBuilder
            .GreaterThan(DateTime.UtcNow)
            .WithErrorCode("DateInPast")
            .WithMessage("Must be in the future");
    }

    public static IRuleBuilder<T, string> MustBeValidEnumValue<T, TEnum>(
        this IRuleBuilder<T, string> ruleBuilder) where TEnum : struct, Enum
    {
        return ruleBuilder
            .Must(value => Enum.TryParse<TEnum>(value, true, out _))
            .WithErrorCode("InvalidEnumValue")
            .WithMessage($"Must be a valid {typeof(TEnum).Name} value");
    }
}
```

### 2.5 Validator Usage Example

```csharp
public class CreateAppointmentValidator : AbstractValidator<CreateAppointmentRequest>
{
    public CreateAppointmentValidator()
    {
        RuleFor(x => x.PatientId)
            .NotEmpty()
            .MustBeValidUuid()
            .WithErrorCode("PatientIdRequired");

        RuleFor(x => x.ClinicianId)
            .NotEmpty()
            .MustBeValidUuid()
            .WithErrorCode("ClinicianIdRequired");

        RuleFor(x => x.AppointmentType)
            .NotEmpty()
            .MustBeValidEnumValue<CreateAppointmentRequest, AppointmentType>()
            .WithErrorCode("InvalidAppointmentType");

        RuleFor(x => x.ScheduledTime)
            .NotEmpty()
            .MustBeInFuture()
            .WithErrorCode("ScheduledTimeInvalid");

        RuleFor(x => x.Duration)
            .GreaterThan(0)
            .LessThanOrEqualTo(480)
            .WithErrorCode("InvalidDuration")
            .WithMessage("Duration must be between 1 and 480 minutes");
    }
}
```

---

## 3. Authentication Hook Contract

### 3.1 Authentication Middleware Interface

All services MUST implement authentication middleware that:
1. Extracts and validates authentication tokens
2. Decodes tokens and extracts claims
3. Attaches user context to request
4. Supports multiple auth schemes (Bearer, API Key, etc.)

**C# Interface:**
```csharp
public interface IAuthenticationMiddleware
{
    Task InvokeAsync(HttpContext context, RequestDelegate next);
}

public interface ITokenValidator
{
    Task<TokenValidationResult> ValidateAsync(string token);
}

public class TokenValidationResult
{
    public bool IsValid { get; set; }
    public ClaimsPrincipal Principal { get; set; }
    public string Error { get; set; }
}

public class AuthContext
{
    public string UserId { get; set; }
    public string TenantId { get; set; }
    public List<string> Roles { get; set; }
    public List<string> Permissions { get; set; }
    public Dictionary<string, object> CustomClaims { get; set; }
}
```

### 3.2 Token Extraction and Validation

Authentication middleware MUST:
1. Extract Bearer token from Authorization header
2. Validate JWT signature and expiration
3. Extract claims and build AuthContext
4. Attach to request context

```csharp
public class BearerTokenAuthenticationMiddleware : IAuthenticationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ITokenValidator _tokenValidator;
    private readonly ILogger<BearerTokenAuthenticationMiddleware> _logger;

    public BearerTokenAuthenticationMiddleware(RequestDelegate next,
        ITokenValidator tokenValidator,
        ILogger<BearerTokenAuthenticationMiddleware> logger)
    {
        _next = next;
        _tokenValidator = tokenValidator;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        // Extract token from Authorization header
        var authHeader = context.Request.Headers["Authorization"].ToString();
        
        if (string.IsNullOrEmpty(authHeader))
        {
            // Allow public endpoints to proceed without auth
            await _next(context);
            return;
        }

        try
        {
            // Must be "Bearer {token}"
            if (!authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
            {
                _logger.LogWarning("Invalid Authorization header format");
                throw new UnauthorizedAccessException("Invalid Authorization header format");
            }

            var token = authHeader.Substring("Bearer ".Length).Trim();

            // Validate token
            var validationResult = await _tokenValidator.ValidateAsync(token);

            if (!validationResult.IsValid)
            {
                _logger.LogWarning("Token validation failed: {Error}", validationResult.Error);
                throw new UnauthorizedAccessException(validationResult.Error);
            }

            // Extract claims and build auth context
            var authContext = ExtractAuthContext(validationResult.Principal);
            
            // Attach to request context
            context.Items["AuthContext"] = authContext;
            context.User = validationResult.Principal;

            _logger.LogInformation("User authenticated. UserId: {UserId}, TenantId: {TenantId}",
                authContext.UserId, authContext.TenantId);
        }
        catch (UnauthorizedAccessException ex)
        {
            _logger.LogWarning(ex, "Authentication failed");
            throw;
        }

        await _next(context);
    }

    private AuthContext ExtractAuthContext(ClaimsPrincipal principal)
    {
        return new AuthContext
        {
            UserId = principal.FindFirst("sub")?.Value,
            TenantId = principal.FindFirst("tenant_id")?.Value,
            Roles = principal.FindAll("role")?.Select(c => c.Value).ToList() ?? new(),
            Permissions = principal.FindAll("permission")?.Select(c => c.Value).ToList() ?? new(),
            CustomClaims = principal.Claims
                .Where(c => !c.Type.In("sub", "tenant_id", "role", "permission", "iat", "exp"))
                .ToDictionary(c => c.Type, c => (object)c.Value)
        };
    }
}
```

### 3.3 JWT Token Claims Standard

All JWT tokens MUST include these standard claims:

```json
{
  "sub": "user-123",                    // Subject (user ID)
  "tenant_id": "tenant-456",            // Tenant ID
  "role": ["CLINICIAN", "ADMIN"],       // Array of roles
  "permission": ["read:appointments"],  // Array of permissions
  "iat": 1687461000,                    // Issued at
  "exp": 1687464600,                    // Expiration (1 hour)
  "iss": "https://auth.propellq.local", // Issuer
  "aud": "propellq-api",                // Audience
  "email": "clinician@hospital.com",    // User email
  "name": "Dr. Jane Smith",             // User name
  "jti": "unique-token-id"              // JWT ID (for revocation tracking)
}
```

### 3.4 Authentication Error Handling

Authentication errors MUST propagate to error middleware (MID-1):

```csharp
// Authentication failure throws exception caught by MID-1
throw new SecurityTokenException("Token signature validation failed");

// Error middleware converts to:
{
  "statusCode": 401,
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication token validation failed"
  }
}
```

---

## 4. Authorization Middleware Contract

### 4.1 Authorization Middleware Interface

All services MUST implement authorization middleware that:
1. Evaluates role and permission requirements
2. Enforces resource ownership checks
3. Returns 403 if unauthorized

**C# Interface:**
```csharp
public interface IAuthorizationMiddleware
{
    Task InvokeAsync(HttpContext context, RequestDelegate next);
}

public interface IAuthorizationPolicy
{
    Task<bool> EvaluateAsync(AuthContext authContext, ResourceContext resource);
}
```

### 4.2 Authorization Attributes/Decorators

Controllers MUST use authorization attributes:

```csharp
[ApiController]
[Route("/api/v1/appointments")]
public class AppointmentsController : ControllerBase
{
    [HttpGet("{id}")]
    [Authorize]
    [RequirePermission("read:appointments")]
    public async Task<IActionResult> GetAppointment(string id)
    {
        // Get appointment and verify user can access it
        var appointment = await _appointmentService.GetAsync(id);
        
        // Ownership check - clinician can only read their own appointments
        var authContext = HttpContext.Items["AuthContext"] as AuthContext;
        if (appointment.ClinicianId != authContext.UserId)
        {
            throw new ForbiddenAccessException();
        }

        return Ok(appointment);
    }

    [HttpPost]
    [Authorize]
    [RequirePermission("write:appointments")]
    [RequireRole("ADMIN", "CLINICIAN")]
    public async Task<IActionResult> CreateAppointment(CreateAppointmentRequest request)
    {
        var appointment = await _appointmentService.CreateAsync(request);
        return CreatedAtAction(nameof(GetAppointment), new { id = appointment.Id }, appointment);
    }

    [HttpDelete("{id}")]
    [Authorize]
    [RequirePermission("delete:appointments")]
    [RequireRole("ADMIN")]
    public async Task<IActionResult> DeleteAppointment(string id)
    {
        await _appointmentService.DeleteAsync(id);
        return NoContent();
    }
}
```

### 4.3 Authorization Policy Evaluation

```csharp
public class AuthorizationPolicyHandler : IAuthorizationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IAuthorizationPolicyEvaluator _policyEvaluator;

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        var authContext = context.Items["AuthContext"] as AuthContext;
        
        if (authContext == null)
        {
            // No auth context (public endpoint)
            await next(context);
            return;
        }

        // Get authorization requirements from controller action
        var endpoint = context.GetEndpoint();
        var authorizeAttributes = endpoint?.Metadata.GetOrderedMetadata<AuthorizeAttribute>();

        if (authorizeAttributes?.Count > 0)
        {
            // Evaluate each authorization requirement
            foreach (var attribute in authorizeAttributes)
            {
                var isAuthorized = await _policyEvaluator.EvaluateAsync(
                    attribute, authContext, context);

                if (!isAuthorized)
                {
                    throw new ForbiddenAccessException(
                        $"User does not have required {attribute.GetType().Name}");
                }
            }
        }

        await next(context);
    }
}

public class AuthorizationPolicyEvaluator : IAuthorizationPolicyEvaluator
{
    public Task<bool> EvaluateAsync(AuthorizeAttribute policy, 
        AuthContext authContext, HttpContext httpContext)
    {
        // Evaluate based on attribute type
        return policy switch
        {
            RequirePermissionAttribute p => EvaluatePermissionPolicy(p, authContext),
            RequireRoleAttribute r => EvaluateRolePolicy(r, authContext),
            _ => Task.FromResult(true)
        };
    }

    private Task<bool> EvaluatePermissionPolicy(RequirePermissionAttribute policy, 
        AuthContext authContext)
    {
        // User must have ALL required permissions
        var hasAllPermissions = policy.RequiredPermissions
            .All(perm => authContext.Permissions.Contains(perm));

        return Task.FromResult(hasAllPermissions);
    }

    private Task<bool> EvaluateRolePolicy(RequireRoleAttribute policy, 
        AuthContext authContext)
    {
        // User must have AT LEAST ONE required role
        var hasRole = authContext.Roles
            .Any(role => policy.AllowedRoles.Contains(role));

        return Task.FromResult(hasRole);
    }
}
```

---

## 5. Request Context Enrichment

### 5.1 RequestContext Object

All middleware MUST enrich context with standardized properties:

```csharp
public class RequestContext
{
    public string CorrelationId { get; set; }
    public string RequestId { get; set; }
    public AuthContext AuthContext { get; set; }
    public Dictionary<string, object> ValidationMetadata { get; set; }
    public DateTime RequestStartTime { get; set; }
    public string TenantId { get; set; }
    public string UserId { get; set; }
}
```

### 5.2 Middleware Enrichment Order

Middleware MUST execute in this order:

1. **Correlation ID Middleware** - Extract/generate correlation IDs
2. **Logging Middleware** - Log request start
3. **Validation Middleware** - Validate request structure
4. **Authentication Middleware** - Validate token
5. **Authorization Middleware** - Check permissions
6. **Request Enrichment Middleware** - Add context data

```csharp
// Program.cs
public void Configure(IApplicationBuilder app)
{
    app.UseMiddleware<CorrelationIdMiddleware>();
    app.UseMiddleware<LoggingMiddleware>();
    app.UseMiddleware<RequestValidationMiddleware>();
    app.UseMiddleware<BearerTokenAuthenticationMiddleware>();
    app.UseMiddleware<AuthorizationPolicyHandler>();
    app.UseMiddleware<RequestEnrichmentMiddleware>();
    app.UseMiddleware<ErrorHandlingMiddleware>();
    
    app.UseRouting();
    app.UseEndpoints(endpoints => endpoints.MapControllers());
}
```

---

## 6. Validation and Auth Integration Testing

### 6.1 Validation Middleware Tests

```csharp
[Fact]
public async Task ValidationMiddleware_InvalidEmail_Returns400()
{
    // Arrange
    var request = new CreateAppointmentRequest
    {
        Email = "invalid-email",
        ScheduledTime = DateTime.UtcNow.AddDays(1)
    };

    // Act
    var response = await _client.PostAsJsonAsync("/api/v1/appointments", request);

    // Assert
    Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    var errorResponse = await response.Content.ReadAsAsync<ErrorResponse>();
    Assert.Equal("VALIDATION_ERROR", errorResponse.Error.Code);
    Assert.Contains(errorResponse.Error.Details, 
        d => d.Field == "email" && d.Code == "InvalidEmailFormat");
}

[Fact]
public async Task ValidationMiddleware_ScheduledTimeInPast_Returns400()
{
    // Arrange
    var request = new CreateAppointmentRequest
    {
        Email = "test@example.com",
        ScheduledTime = DateTime.UtcNow.AddDays(-1)
    };

    // Act
    var response = await _client.PostAsJsonAsync("/api/v1/appointments", request);

    // Assert
    Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    var errorResponse = await response.Content.ReadAsAsync<ErrorResponse>();
    Assert.Contains(errorResponse.Error.Details,
        d => d.Field == "scheduledTime" && d.Code == "DateInPast");
}
```

### 6.2 Authentication Middleware Tests

```csharp
[Fact]
public async Task AuthMiddleware_MissingToken_ContinuesForPublicEndpoint()
{
    // Act
    var response = await _client.GetAsync("/api/v1/public/health");

    // Assert
    Assert.Equal(HttpStatusCode.OK, response.StatusCode);
}

[Fact]
public async Task AuthMiddleware_InvalidToken_Returns401()
{
    // Arrange
    _client.DefaultRequestHeaders.Authorization = 
        new AuthenticationHeaderValue("Bearer", "invalid.token.here");

    // Act
    var response = await _client.GetAsync("/api/v1/appointments");

    // Assert
    Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    var errorResponse = await response.Content.ReadAsAsync<ErrorResponse>();
    Assert.Equal("UNAUTHORIZED", errorResponse.Error.Code);
}

[Fact]
public async Task AuthMiddleware_ValidToken_AttachesUserContext()
{
    // Arrange
    var token = GenerateValidJwt("user-123", roles: new[] { "CLINICIAN" });
    _client.DefaultRequestHeaders.Authorization = 
        new AuthenticationHeaderValue("Bearer", token);

    // Act
    var response = await _client.GetAsync("/api/v1/appointments");

    // Assert
    Assert.NotEqual(HttpStatusCode.Unauthorized, response.StatusCode);
}
```

### 6.3 Authorization Middleware Tests

```csharp
[Fact]
public async Task AuthorizationMiddleware_InsufficientPermission_Returns403()
{
    // Arrange
    var token = GenerateValidJwt("user-123", 
        roles: new[] { "CLINICIAN" },
        permissions: new[] { "read:appointments" });
    _client.DefaultRequestHeaders.Authorization = 
        new AuthenticationHeaderValue("Bearer", token);

    var request = new CreateAppointmentRequest { ... };

    // Act
    var response = await _client.PostAsJsonAsync("/api/v1/appointments", request);

    // Assert
    Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    var errorResponse = await response.Content.ReadAsAsync<ErrorResponse>();
    Assert.Equal("FORBIDDEN", errorResponse.Error.Code);
}

[Fact]
public async Task AuthorizationMiddleware_ValidPermission_AllowsRequest()
{
    // Arrange
    var token = GenerateValidJwt("user-123",
        roles: new[] { "CLINICIAN" },
        permissions: new[] { "write:appointments" });
    _client.DefaultRequestHeaders.Authorization = 
        new AuthenticationHeaderValue("Bearer", token);

    var request = new CreateAppointmentRequest { ... };

    // Act
    var response = await _client.PostAsJsonAsync("/api/v1/appointments", request);

    // Assert
    Assert.Equal(HttpStatusCode.Created, response.StatusCode);
}
```

---

## 7. Implementation Checklist

Services MUST verify:

- [ ] Request validation middleware intercepts all non-GET requests
- [ ] Validation errors return 400 with VALIDATION_ERROR code
- [ ] Common validators (email, UUID, date) are reusable
- [ ] Authentication middleware extracts Bearer tokens
- [ ] JWT tokens include standard claims (sub, tenant_id, role, permission)
- [ ] Token validation checks signature and expiration
- [ ] AuthContext is attached to request context
- [ ] Authorization policies evaluate roles and permissions
- [ ] Authorization failures return 403 with FORBIDDEN code
- [ ] Resource ownership checks prevent unauthorized access
- [ ] Middleware executes in correct order
- [ ] All validation/auth errors use standard error envelope
- [ ] Integration tests cover validation, auth, and authorization scenarios

---

## 8. Questions and Feedback

For questions about validation and auth contracts:
- Open issue in: `.propel/context/standards/issues/`
- Security team: security@propellq.local
- Next review date: Q3 2026

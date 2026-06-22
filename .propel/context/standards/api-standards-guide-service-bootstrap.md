# DOC-1: API Standards Guide and Service Bootstrap

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** API Developers, Service Owners, Platform Engineers

---

## 1. Overview

This guide provides comprehensive implementation examples and step-by-step instructions for building APIs that comply with PropellQ standards. It includes:

- Quick-start examples for common scenarios
- Service bootstrap starter package overview
- Integration patterns and best practices
- Troubleshooting common issues
- Reference implementations in multiple languages

**Use this guide to:**
- Develop new API endpoints
- Migrate existing endpoints to standards
- Train new team members
- Troubleshoot standards-related issues

---

## 2. Quick Reference

### 2.1 API Standards at a Glance

```
Request Pattern:
POST /api/v1/{resource}
X-Idempotency-Key: {uuid}
X-Correlation-ID: {uuid}
Authorization: Bearer {token}

{
  "field1": "value",
  "field2": 123
}

Response Pattern (Success):
{
  "statusCode": 201,
  "success": true,
  "correlationId": "{uuid}",
  "timestamp": "2026-06-22T14:30:00Z",
  "data": {
    "id": "resource-001",
    "field1": "value"
  }
}

Response Pattern (Error):
{
  "statusCode": 400,
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "field1",
        "issue": "Invalid format",
        "code": "InvalidFormat"
      }
    ]
  },
  "correlationId": "{uuid}"
}
```

### 2.2 Key Principles

1. **Consistency:** All APIs follow same envelope, naming, error formats
2. **Predictability:** Clients know what to expect across all endpoints
3. **Debuggability:** Correlation IDs and detailed errors aid troubleshooting
4. **Reliability:** Idempotency prevents duplicates on retries
5. **Discoverability:** OpenAPI docs and clear naming

---

## 3. Service Bootstrap Package

### 3.1 Bootstrap Package Contents

When creating a new service, clone the service bootstrap package:

```bash
git clone https://github.com/propellq/api-service-bootstrap.git \
  my-new-service

cd my-new-service

# Install dependencies
npm install
# or
dotnet restore
```

**Package structure:**
```
api-service-bootstrap/
├── src/
│   ├── Controllers/                    # HTTP endpoints
│   ├── Services/                       # Business logic
│   ├── Models/                         # DTOs and domain models
│   ├── Middleware/                     # Error, auth, validation
│   ├── Validators/                     # Request validators
│   └── Exceptions/                     # Custom exceptions
├── tests/
│   ├── Unit/                           # Unit tests
│   └── Integration/                    # API integration tests
├── docs/
│   ├── api-spec.openapi.json          # OpenAPI spec
│   └── migration-guide.md             # Deprecation guide template
├── .github/workflows/
│   ├── api-lint.yml                    # API conformance checking
│   ├── unit-tests.yml                  # Test CI/CD
│   └── deploy.yml                      # Deployment
├── docker-compose.yml                  # Local development environment
└── Program.cs / main.py / server.js   # Application entry point
```

### 3.2 Quick Setup (5 minutes)

**Step 1: Create service from bootstrap**
```bash
git clone https://github.com/propellq/api-service-bootstrap.git \
  propellq-appointment-service
cd propellq-appointment-service
```

**Step 2: Update identifiers**
```bash
# Replace all BOOTSTRAP_SERVICE with your service name
find . -type f -exec sed -i 's/BOOTSTRAP_SERVICE/AppointmentService/g' {} \;
find . -type f -exec sed -i 's/bootstrap-service/appointment-service/g' {} \;
```

**Step 3: Add first endpoint**
```csharp
// src/Controllers/AppointmentsController.cs
[ApiController]
[Route("api/v1/[controller]")]
public class AppointmentsController : ControllerBase
{
    [HttpPost]
    [Authorize]
    [RequirePermission("write:appointments")]
    public async Task<IActionResult> CreateAppointment(
        [FromBody] CreateAppointmentRequest request)
    {
        var appointment = await _service.CreateAsync(request);
        return CreatedAtAction(nameof(GetAppointment), 
            new { id = appointment.Id }, appointment);
    }

    [HttpGet("{id}")]
    [Authorize]
    [RequirePermission("read:appointments")]
    public async Task<IActionResult> GetAppointment(string id)
    {
        var appointment = await _service.GetAsync(id);
        if (appointment == null)
            return NotFound();
        return Ok(appointment);
    }
}
```

**Step 4: Run locally**
```bash
docker-compose up

# In another terminal
dotnet run

# Test endpoint
curl -H "Authorization: Bearer {token}" \
  http://localhost:5000/api/v1/appointments
```

---

## 4. Implementation Examples

### 4.1 Complete POST Endpoint Example (C#)

```csharp
using System;
using System.Threading.Tasks;
using FluentValidation;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;

namespace AppointmentService.Controllers
{
    [ApiController]
    [Route("api/v1/appointments")]
    public class AppointmentsController : ControllerBase
    {
        private readonly IAppointmentService _appointmentService;
        private readonly IAppointmentValidator _validator;
        private readonly ILogger<AppointmentsController> _logger;

        public AppointmentsController(
            IAppointmentService appointmentService,
            IAppointmentValidator validator,
            ILogger<AppointmentsController> logger)
        {
            _appointmentService = appointmentService;
            _validator = validator;
            _logger = logger;
        }

        /// <summary>
        /// Create a new appointment
        /// </summary>
        /// <param name="request">Appointment details</param>
        /// <returns>Created appointment with ID</returns>
        [HttpPost]
        [Authorize]
        [RequirePermission("write:appointments")]
        public async Task<ActionResult<AppointmentResponse>> CreateAppointment(
            [FromBody] CreateAppointmentRequest request,
            [FromHeader(Name = "X-Idempotency-Key")] string idempotencyKey)
        {
            var correlationId = HttpContext.GetCorrelationId();
            
            _logger.LogInformation(
                "Creating appointment. CorrelationId: {CorrelationId}, " +
                "IdempotencyKey: {IdempotencyKey}, PatientId: {PatientId}",
                correlationId, idempotencyKey, request.PatientId);

            try
            {
                // Validate request
                var validationResult = await _validator.ValidateAsync(request);
                if (!validationResult.IsValid)
                {
                    _logger.LogWarning(
                        "Validation failed. CorrelationId: {CorrelationId}, " +
                        "Errors: {ErrorCount}",
                        correlationId, validationResult.Errors.Count);

                    throw new ValidationException(validationResult.Errors);
                }

                // Create appointment
                var appointment = await _appointmentService.CreateAsync(
                    request, HttpContext.GetUserId());

                _logger.LogInformation(
                    "Appointment created. CorrelationId: {CorrelationId}, " +
                    "AppointmentId: {AppointmentId}",
                    correlationId, appointment.Id);

                return CreatedAtAction(
                    nameof(GetAppointment),
                    new { id = appointment.Id },
                    new AppointmentResponse
                    {
                        StatusCode = 201,
                        Success = true,
                        Data = appointment,
                        CorrelationId = correlationId,
                        Timestamp = DateTime.UtcNow
                    });
            }
            catch (ValidationException ex)
            {
                _logger.LogWarning(ex,
                    "Validation error. CorrelationId: {CorrelationId}",
                    correlationId);
                throw; // Will be caught by error middleware
            }
            catch (Exception ex)
            {
                _logger.LogError(ex,
                    "Unexpected error creating appointment. CorrelationId: {CorrelationId}",
                    correlationId);
                throw;
            }
        }

        /// <summary>
        /// Get appointment by ID
        /// </summary>
        [HttpGet("{id}")]
        [Authorize]
        [RequirePermission("read:appointments")]
        public async Task<ActionResult<AppointmentResponse>> GetAppointment(string id)
        {
            var correlationId = HttpContext.GetCorrelationId();
            var appointment = await _appointmentService.GetAsync(id);

            if (appointment == null)
            {
                _logger.LogWarning(
                    "Appointment not found. CorrelationId: {CorrelationId}, " +
                    "AppointmentId: {AppointmentId}",
                    correlationId, id);

                return NotFound(new AppointmentResponse
                {
                    StatusCode = 404,
                    Success = false,
                    Error = new ErrorResponse
                    {
                        Code = "NOT_FOUND",
                        Message = $"Appointment '{id}' not found"
                    },
                    CorrelationId = correlationId,
                    Timestamp = DateTime.UtcNow
                });
            }

            return Ok(new AppointmentResponse
            {
                StatusCode = 200,
                Success = true,
                Data = appointment,
                CorrelationId = correlationId,
                Timestamp = DateTime.UtcNow
            });
        }
    }
}
```

### 4.2 Complete Validator Example (C#)

```csharp
using FluentValidation;
using System;

namespace AppointmentService.Validators
{
    public class CreateAppointmentValidator : AbstractValidator<CreateAppointmentRequest>
    {
        public CreateAppointmentValidator()
        {
            // Patient ID validation
            RuleFor(x => x.PatientId)
                .NotEmpty()
                    .WithErrorCode("PatientIdRequired")
                    .WithMessage("Patient ID is required")
                .MustBeValidUuid()
                    .WithErrorCode("PatientIdInvalidFormat")
                    .WithMessage("Patient ID must be a valid UUID");

            // Clinician ID validation
            RuleFor(x => x.ClinicianId)
                .NotEmpty()
                    .WithErrorCode("ClinicianIdRequired")
                    .WithMessage("Clinician ID is required")
                .MustBeValidUuid()
                    .WithErrorCode("ClinicianIdInvalidFormat");

            // Appointment type validation
            RuleFor(x => x.AppointmentType)
                .NotEmpty()
                    .WithErrorCode("AppointmentTypeRequired")
                .MustBeValidEnumValue<CreateAppointmentRequest, AppointmentType>()
                    .WithErrorCode("InvalidAppointmentType")
                    .WithMessage("Invalid appointment type");

            // Scheduled time validation
            RuleFor(x => x.ScheduledTime)
                .NotEmpty()
                    .WithErrorCode("ScheduledTimeRequired")
                .MustBeInFuture()
                    .WithErrorCode("ScheduledTimeInPast")
                    .WithMessage("Appointment must be scheduled in the future");

            // Duration validation
            RuleFor(x => x.Duration)
                .GreaterThan(0)
                    .WithErrorCode("DurationTooShort")
                    .WithMessage("Duration must be greater than 0")
                .LessThanOrEqualTo(480)
                    .WithErrorCode("DurationTooLong")
                    .WithMessage("Duration cannot exceed 480 minutes");

            // Notes validation (optional)
            RuleFor(x => x.Notes)
                .MaximumLength(500)
                    .WithErrorCode("NotesTooLong")
                    .WithMessage("Notes cannot exceed 500 characters")
                .When(x => !string.IsNullOrEmpty(x.Notes));
        }
    }
}
```

### 4.3 Request/Response Models Example

```csharp
using System;

namespace AppointmentService.Models
{
    // Request DTO
    public class CreateAppointmentRequest
    {
        public string PatientId { get; set; }
        public string ClinicianId { get; set; }
        public AppointmentType AppointmentType { get; set; }
        public DateTime ScheduledTime { get; set; }
        public int Duration { get; set; } // minutes
        public string Notes { get; set; }
    }

    // Response DTOs
    public class AppointmentResponse<T> where T : class
    {
        public int StatusCode { get; set; }
        public bool Success { get; set; }
        public T Data { get; set; }
        public ErrorResponse Error { get; set; }
        public string CorrelationId { get; set; }
        public DateTime Timestamp { get; set; }
    }

    public class AppointmentDto
    {
        public string Id { get; set; }
        public string PatientId { get; set; }
        public string ClinicianId { get; set; }
        public AppointmentType AppointmentType { get; set; }
        public DateTime ScheduledTime { get; set; }
        public int Duration { get; set; }
        public string Notes { get; set; }
        public AppointmentStatus Status { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
    }

    public class ErrorResponse
    {
        public string Code { get; set; }
        public string Message { get; set; }
        public List<ErrorDetail> Details { get; set; }
    }

    public class ErrorDetail
    {
        public string Field { get; set; }
        public string Issue { get; set; }
        public string Code { get; set; }
        public object Value { get; set; }
    }

    // Enums
    public enum AppointmentType
    {
        CONSULTATION,
        FOLLOW_UP,
        PROCEDURE,
        SCREENING
    }

    public enum AppointmentStatus
    {
        PENDING,
        CONFIRMED,
        IN_PROGRESS,
        COMPLETED,
        CANCELLED
    }
}
```

### 4.4 Error Handling Integration Example

```csharp
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

namespace AppointmentService.Configuration
{
    public static class ServiceConfiguration
    {
        public static IServiceCollection AddApiStandards(
            this IServiceCollection services)
        {
            // Add middleware components
            services.AddScoped<IErrorHandlingMiddleware, ErrorHandlingMiddleware>();
            services.AddScoped<IIdempotencyMiddleware, IdempotencyMiddleware>();
            services.AddScoped<IRequestValidationMiddleware, RequestValidationMiddleware>();
            
            // Add exception handlers
            services.AddScoped<IExceptionHandler, ValidationExceptionHandler>();
            services.AddScoped<IExceptionHandler, AuthenticationExceptionHandler>();
            services.AddScoped<IExceptionHandler, AuthorizationExceptionHandler>();
            services.AddScoped<IExceptionHandler, InternalServerErrorHandler>();

            // Add idempotency store (Redis in production)
            if (Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") == "Production")
            {
                services.AddSingleton<IIdempotencyStore>(
                    new RedisIdempotencyStore(connectionString));
            }
            else
            {
                services.AddSingleton<IIdempotencyStore, InMemoryIdempotencyStore>();
            }

            return services;
        }

        public static IApplicationBuilder UseApiStandards(
            this IApplicationBuilder app)
        {
            // Middleware order matters!
            // Error handling MUST be first
            app.UseMiddleware<ErrorHandlingMiddleware>();
            app.UseMiddleware<CorrelationIdMiddleware>();
            app.UseMiddleware<LoggingMiddleware>();
            app.UseMiddleware<RequestValidationMiddleware>();
            app.UseMiddleware<BearerTokenAuthenticationMiddleware>();
            app.UseMiddleware<AuthorizationPolicyHandler>();
            app.UseMiddleware<IdempotencyMiddleware>();
            
            return app;
        }
    }
}
```

### 4.5 Startup Configuration Example (C#)

```csharp
// Program.cs
using AppointmentService.Configuration;
using FluentValidation;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

// Add services
builder.Services
    .AddControllers()
    .AddNewtonsoftJson();

builder.Services.AddApiStandards();

// Add validators
builder.Services.AddValidatorsFromAssemblyContaining(typeof(Program));

// Add authentication
builder.Services.AddAuthentication("Bearer")
    .AddJwtBearer(options =>
    {
        options.Authority = "https://auth.propellq.local";
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateAudience = false,
            ValidateIssuer = true,
            ValidIssuer = "https://auth.propellq.local"
        };
    });

builder.Services.AddAuthorization();

// Add logging
builder.Services.AddLogging();

// Add API documentation
builder.Services.AddSwaggerGen();

// Add health checks
builder.Services.AddHealthChecks();

var app = builder.Build();

// Configure middleware
app.UseApiStandards();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();
app.MapHealthChecks("/health");

// Enable Swagger
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.Run();
```

---

## 5. Common Patterns

### 5.1 List with Pagination

```csharp
[HttpGet]
[Authorize]
[RequirePermission("read:appointments")]
public async Task<IActionResult> ListAppointments(
    [FromQuery] int pageNumber = 1,
    [FromQuery] int pageSize = 20,
    [FromQuery] string sortBy = "-createdAt",
    [FromQuery] string filterStatus = null)
{
    var correlationId = HttpContext.GetCorrelationId();
    
    var result = await _appointmentService.ListAsync(
        pageNumber, pageSize, sortBy, filterStatus);

    return Ok(new ListResponse<AppointmentDto>
    {
        StatusCode = 200,
        Success = true,
        Data = result.Items,
        Pagination = new PaginationMetadata
        {
            PageNumber = pageNumber,
            PageSize = pageSize,
            TotalItems = result.Total,
            TotalPages = (result.Total + pageSize - 1) / pageSize,
            HasNextPage = pageNumber * pageSize < result.Total,
            HasPreviousPage = pageNumber > 1
        },
        CorrelationId = correlationId,
        Timestamp = DateTime.UtcNow
    });
}
```

### 5.2 Update with Idempotency

```csharp
[HttpPut("{id}")]
[Authorize]
[RequirePermission("write:appointments")]
public async Task<IActionResult> UpdateAppointment(
    string id,
    [FromBody] UpdateAppointmentRequest request,
    [FromHeader(Name = "X-Idempotency-Key")] string idempotencyKey)
{
    var correlationId = HttpContext.GetCorrelationId();
    
    // Idempotency middleware handles duplicate detection
    var appointment = await _appointmentService.UpdateAsync(id, request);

    return Ok(new AppointmentResponse
    {
        StatusCode = 200,
        Success = true,
        Data = appointment,
        CorrelationId = correlationId,
        Timestamp = DateTime.UtcNow
    });
}
```

### 5.3 Async Operation (Polling)

```csharp
[HttpPost("batch-import")]
[Authorize]
[RequirePermission("write:appointments")]
public async Task<IActionResult> ImportAppointments(
    [FromForm] IFormFile file)
{
    var correlationId = HttpContext.GetCorrelationId();
    
    // Start async operation
    var operationId = await _appointmentService.StartImportAsync(file);

    return Accepted(new AsyncOperationResponse
    {
        StatusCode = 202,
        Success = true,
        Data = new
        {
            operationId = operationId,
            status = "IN_PROGRESS",
            statusUrl = $"/api/v1/appointments/batch-import/{operationId}/status"
        },
        CorrelationId = correlationId,
        Timestamp = DateTime.UtcNow
    });
}

[HttpGet("batch-import/{operationId}/status")]
[Authorize]
public async Task<IActionResult> GetImportStatus(string operationId)
{
    var correlationId = HttpContext.GetCorrelationId();
    
    var status = await _appointmentService.GetImportStatusAsync(operationId);

    return Ok(new AsyncOperationResponse
    {
        StatusCode = 200,
        Success = true,
        Data = status,
        CorrelationId = correlationId,
        Timestamp = DateTime.UtcNow
    });
}
```

---

## 6. Testing Examples

### 6.1 Unit Test Example

```csharp
using Xunit;
using Moq;
using FluentAssertions;

namespace AppointmentService.Tests
{
    public class AppointmentsControllerTests
    {
        private readonly Mock<IAppointmentService> _mockService;
        private readonly Mock<IAppointmentValidator> _mockValidator;
        private readonly AppointmentsController _controller;

        public AppointmentsControllerTests()
        {
            _mockService = new Mock<IAppointmentService>();
            _mockValidator = new Mock<IAppointmentValidator>();
            _controller = new AppointmentsController(
                _mockService.Object,
                _mockValidator.Object,
                new MockLogger());
        }

        [Fact]
        public async Task CreateAppointment_WithValidRequest_Returns201()
        {
            // Arrange
            var request = new CreateAppointmentRequest
            {
                PatientId = "pat-123",
                ClinicianId = "clin-456",
                AppointmentType = AppointmentType.CONSULTATION,
                ScheduledTime = DateTime.UtcNow.AddDays(7),
                Duration = 30
            };

            var expectedAppointment = new AppointmentDto
            {
                Id = "apt-001",
                PatientId = request.PatientId,
                Status = AppointmentStatus.PENDING
            };

            _mockValidator.Setup(v => v.ValidateAsync(request))
                .ReturnsAsync(new ValidationResult { IsValid = true });

            _mockService.Setup(s => s.CreateAsync(request, It.IsAny<string>()))
                .ReturnsAsync(expectedAppointment);

            // Act
            var result = await _controller.CreateAppointment(request, "key-123");

            // Assert
            var createdResult = result.Result as CreatedAtActionResult;
            createdResult.Should().NotBeNull();
            createdResult.StatusCode.Should().Be(201);
            
            var response = createdResult.Value as AppointmentResponse;
            response.Data.Id.Should().Be("apt-001");
        }

        [Fact]
        public async Task CreateAppointment_WithInvalidRequest_Returns400()
        {
            // Arrange
            var request = new CreateAppointmentRequest
            {
                PatientId = "invalid-id",
                ClinicianId = "clin-456",
                AppointmentType = AppointmentType.CONSULTATION,
                ScheduledTime = DateTime.UtcNow.AddDays(-1), // Past date
                Duration = 30
            };

            var validationFailures = new[]
            {
                new ValidationFailure("patientId", "Invalid UUID format"),
                new ValidationFailure("scheduledTime", "Must be in future")
            };

            _mockValidator.Setup(v => v.ValidateAsync(request))
                .ReturnsAsync(new ValidationResult(validationFailures));

            // Act & Assert
            await Assert.ThrowsAsync<ValidationException>(
                () => _controller.CreateAppointment(request, "key-123"));
        }
    }
}
```

### 6.2 Integration Test Example

```csharp
using System.Net;
using System.Net.Http.Json;
using Xunit;

namespace AppointmentService.Tests.Integration
{
    public class AppointmentsIntegrationTests : IAsyncLifetime
    {
        private readonly WebApplicationFactory<Program> _factory;
        private HttpClient _client;

        public AppointmentsIntegrationTests()
        {
            _factory = new WebApplicationFactory<Program>();
            _client = _factory.CreateClient();
        }

        [Fact]
        public async Task CreateAppointment_EndToEnd_Success()
        {
            // Arrange
            var token = GenerateValidJwt();
            _client.DefaultRequestHeaders.Authorization = 
                new AuthenticationHeaderValue("Bearer", token);

            var request = new CreateAppointmentRequest
            {
                PatientId = "pat-123",
                ClinicianId = "clin-456",
                AppointmentType = AppointmentType.CONSULTATION,
                ScheduledTime = DateTime.UtcNow.AddDays(7),
                Duration = 30
            };

            // Act
            var response = await _client.PostAsJsonAsync(
                "/api/v1/appointments", request);

            // Assert
            response.StatusCode.Should().Be(HttpStatusCode.Created);
            
            var content = await response.Content.ReadAsAsync<AppointmentResponse>();
            content.Success.Should().BeTrue();
            content.Data.Id.Should().NotBeNullOrEmpty();
        }

        [Fact]
        public async Task CreateAppointment_WithoutToken_Returns401()
        {
            // Arrange
            var request = new CreateAppointmentRequest { ... };
            _client.DefaultRequestHeaders.Clear();

            // Act
            var response = await _client.PostAsJsonAsync(
                "/api/v1/appointments", request);

            // Assert
            response.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        }

        [Fact]
        public async Task CreateAppointment_Idempotent_ReplaysCachedResponse()
        {
            // Arrange
            var token = GenerateValidJwt();
            var key = "idempotency-key-123";
            var request = new CreateAppointmentRequest { ... };

            _client.DefaultRequestHeaders.Authorization = 
                new AuthenticationHeaderValue("Bearer", token);
            _client.DefaultRequestHeaders.Add("X-Idempotency-Key", key);

            // Act
            var response1 = await _client.PostAsJsonAsync("/api/v1/appointments", request);
            var content1 = await response1.Content.ReadAsAsync<AppointmentResponse>();
            var appointmentId1 = content1.Data.Id;

            // Act - Retry with same key
            var response2 = await _client.PostAsJsonAsync("/api/v1/appointments", request);
            var content2 = await response2.Content.ReadAsAsync<AppointmentResponse>();
            var appointmentId2 = content2.Data.Id;

            // Assert
            appointmentId1.Should().Be(appointmentId2); // Same appointment
            response2.Headers.GetValues("X-Idempotency-Replayed")
                .Should().Contain("true");
        }
    }
}
```

---

## 7. Troubleshooting

### 7.1 Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Missing correlationId | Logs have no correlation | Ensure CorrelationIdMiddleware runs first |
| Validation not working | Invalid requests succeed | Check if RequestValidationMiddleware is registered |
| Auth errors not caught | 500 instead of 401 | Ensure BearerTokenAuthenticationMiddleware runs before handlers |
| Idempotency not working | Duplicates on retry | Verify IdempotencyStore is configured and accessible |
| Wrong field names | camelCase sent, snake_case received | Check DTO field names match JSON field names |
| Pagination not included | Missing pagination metadata | Ensure response includes pagination object |

### 7.2 Common Questions

**Q: How do I add custom error codes?**  
A: Add to error code registry in STD-1 § 4.2, update error handlers, and communicate in release notes.

**Q: Can I skip idempotency for certain endpoints?**  
A: No, all write operations (POST/PUT/PATCH) MUST support idempotency.

**Q: What if response takes longer than TTL?**  
A: Idempotency cache TTL is 24-72 hours. Adjust as needed, but ensure long enough for typical retries.

**Q: How do I deprecate an endpoint?**  
A: Follow GOV-2 § 4. Announce 6 months in advance with migration guide.

---

## 8. Learning Resources

- **Standards Documentation:** `.propel/context/standards/`
- **Code Examples:** `api-service-bootstrap/examples/`
- **OpenAPI Examples:** `api-service-bootstrap/examples/api-spec.openapi.json`
- **Video Tutorial:** `https://propellq.local/docs/api-standards-video`
- **Support:** api-support@propellq.local

---

## 9. Checklist for New Services

When building a new API service:

- [ ] Clone `api-service-bootstrap` as starting point
- [ ] Define DTOs following naming conventions (STD-1 § 2.3)
- [ ] Create controllers returning standard response envelopes (STD-1 § 3)
- [ ] Implement validators (MID-2) for all endpoints
- [ ] Register middleware in correct order (MID-1, MID-2, MID-3)
- [ ] Add idempotency support to write endpoints (MID-3)
- [ ] Configure error handlers (MID-1)
- [ ] Create OpenAPI spec file
- [ ] Write integration tests validating standards compliance
- [ ] Run API lint checks (GOV-1)
- [ ] Ensure all endpoints documented
- [ ] Set up CI/CD pipeline with checks
- [ ] Deploy to staging and validate
- [ ] Submit PR conformance review

---

## 10. Next Steps

1. Review the standards documentation in this directory
2. Clone the service bootstrap package
3. Follow quick-start example to create first endpoint
4. Run integration tests to verify standards compliance
5. Contact api-support@propellq.local with questions

**Welcome to the PropellQ API standards program!**

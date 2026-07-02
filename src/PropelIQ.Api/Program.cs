using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi.Models;
using PropelIQ.Api.Services;
using PropelIQ.Infrastructure;
using PropelIQ.Infrastructure.Data;

var builder = WebApplication.CreateBuilder(args);

var configuredApiKey = builder.Configuration.GetValue<string>("Auth:ApiKey");
PropelIQ.Api.Startup.StartupValidation.EnsureApiKeyConfigured(
    builder.Environment.EnvironmentName,
    configuredApiKey);

// In-memory session store for UI login
builder.Services.AddSingleton<SessionStore>();
builder.Services.AddSingleton<LegacyBookingStore>();

// Infrastructure (EF Core, OpenAI, repositories, chatbot + EP-004 queue/waitlist/notification services)
builder.Services.AddInfrastructure(builder.Configuration);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new() { Title = "PropelIQ API", Version = "v1" });
    options.EnableAnnotations();
    options.AddSecurityDefinition("ApiKey", new OpenApiSecurityScheme
    {
        Description = "API key required in X-API-Key header",
        Name = "X-API-Key",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.ApiKey
    });

    options.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "ApiKey"
                }
            },
            Array.Empty<string>()
        }
    });
});

builder.Services
    .AddAuthentication("ApiKey")
    .AddScheme<Microsoft.AspNetCore.Authentication.AuthenticationSchemeOptions, PropelIQ.Api.Authentication.ApiKeyAuthenticationHandler>("ApiKey", _ => { });

builder.Services.AddAuthorizationBuilder()
    .SetFallbackPolicy(new AuthorizationPolicyBuilder()
        .AddAuthenticationSchemes("ApiKey")
        .RequireAuthenticatedUser()
        .Build());

var allowedOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>() ?? Array.Empty<string>();
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        if (allowedOrigins.Length > 0)
        {
            policy.WithOrigins(allowedOrigins)
                .AllowAnyMethod()
                .AllowAnyHeader();
        }
    });
});

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    dbContext.Database.Migrate();
}

var configuredUrls = builder.Configuration["ASPNETCORE_URLS"] ?? string.Empty;
var hasHttpsBinding = configuredUrls
    .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
    .Any(url => url.StartsWith("https://", StringComparison.OrdinalIgnoreCase));

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
if (!app.Environment.IsDevelopment() || hasHttpsBinding)
{
    app.UseHttpsRedirection();
}

// Serve UI static files from this API project's wwwroot.
app.UseStaticFiles();

IResult RenderPortalPage(string fileName)
{
    var filePath = Path.Combine(builder.Environment.WebRootPath ?? string.Empty, fileName);
    return File.Exists(filePath)
        ? Results.File(filePath, "text/html; charset=utf-8")
        : Results.NotFound();
}

app.UseAuthentication();
app.UseAuthorization();

// Root: redirect to login page (UI)
app.MapGet("/", () => Results.Redirect("/propeliq/login")).AllowAnonymous();
app.MapGet("/propeliq", () => Results.Redirect("/propeliq/login")).AllowAnonymous();
app.MapGet("/propeliq/login", () => RenderPortalPage("login.html")).AllowAnonymous();
app.MapGet("/propeliq/patient", () => RenderPortalPage("patient.html")).AllowAnonymous();
app.MapGet("/propeliq/staff", () => RenderPortalPage("staff.html")).AllowAnonymous();
app.MapGet("/propeliq/admin", () => RenderPortalPage("admin.html")).AllowAnonymous();
// Health-check endpoint keeps original JSON response
app.MapGet("/health", () => Results.Json(new { status = "ok", service = "PropelIQ API" })).AllowAnonymous();

app.MapControllers();
app.Run();

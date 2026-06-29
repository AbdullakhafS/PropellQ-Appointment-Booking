using Microsoft.AspNetCore.Authorization;
using Microsoft.Extensions.FileProviders;
using Microsoft.OpenApi.Models;
using PropelIQ.Api.Services;
using PropelIQ.Infrastructure;

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

// Serve the UI static files from app/public (relative to the project root)
var publicPath = Path.GetFullPath(
    Path.Combine(builder.Environment.ContentRootPath, "..", "..", "app", "public"));
if (Directory.Exists(publicPath))
{
    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = new PhysicalFileProvider(publicPath),
        RequestPath  = "",
    });
}

app.UseAuthentication();
app.UseAuthorization();

// Root: redirect to login page (UI)
app.MapGet("/", () => Results.Redirect("/login.html")).AllowAnonymous();
// Health-check endpoint keeps original JSON response
app.MapGet("/health", () => Results.Json(new { status = "ok", service = "PropelIQ API" })).AllowAnonymous();

app.MapControllers();
app.Run();

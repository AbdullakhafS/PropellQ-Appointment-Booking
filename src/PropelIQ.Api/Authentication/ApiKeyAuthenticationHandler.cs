using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;
using PropelIQ.Api.Services;

namespace PropelIQ.Api.Authentication;

public sealed class ApiKeyAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    private const string ApiKeyHeaderName = "X-API-Key";

    public ApiKeyAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder)
        : base(options, logger, encoder)
    {
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        // 1. Accept session Bearer tokens issued by /api/auth/session
        var authHeader = Request.Headers.Authorization.ToString();
        if (authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            var bearerToken = authHeader["Bearer ".Length..].Trim();
            var sessionStore = Context.RequestServices.GetRequiredService<SessionStore>();
            var session = sessionStore.ValidateToken(bearerToken);
            if (session is not null)
            {
                var sessionClaims = new[]
                {
                    new Claim(ClaimTypes.Name,  session.UserId),
                    new Claim(ClaimTypes.Role,  session.Role),
                    new Claim(ClaimTypes.Email, session.Email),
                };
                var sessionIdentity  = new ClaimsIdentity(sessionClaims, Scheme.Name);
                var sessionPrincipal = new ClaimsPrincipal(sessionIdentity);
                return Task.FromResult(AuthenticateResult.Success(
                    new AuthenticationTicket(sessionPrincipal, Scheme.Name)));
            }
            return Task.FromResult(AuthenticateResult.Fail("Invalid or expired session token."));
        }

        // 2. Fall back to X-API-Key header (machine-to-machine / Swagger)
        if (!Request.Headers.TryGetValue(ApiKeyHeaderName, out var providedApiKey) || string.IsNullOrWhiteSpace(providedApiKey))
        {
            return Task.FromResult(AuthenticateResult.Fail("Missing credentials."));
        }

        var configuredApiKey = Context.RequestServices
            .GetRequiredService<IConfiguration>()
            .GetValue<string>("Auth:ApiKey");

        if (string.IsNullOrWhiteSpace(configuredApiKey))
        {
            return Task.FromResult(AuthenticateResult.Fail("Server API key is not configured."));
        }

        if (!FixedTimeEquals(providedApiKey.ToString(), configuredApiKey))
        {
            return Task.FromResult(AuthenticateResult.Fail("Invalid API key."));
        }

        var claims = new[] { new Claim(ClaimTypes.Name, "ApiKeyClient") };
        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }

    protected override Task HandleChallengeAsync(AuthenticationProperties properties)
    {
        Response.StatusCode = StatusCodes.Status401Unauthorized;
        Response.Headers.Append("WWW-Authenticate", "ApiKey");
        return Task.CompletedTask;
    }

    private static bool FixedTimeEquals(string left, string right)
    {
        var leftBytes = System.Text.Encoding.UTF8.GetBytes(left);
        var rightBytes = System.Text.Encoding.UTF8.GetBytes(right);
        return System.Security.Cryptography.CryptographicOperations.FixedTimeEquals(leftBytes, rightBytes);
    }
}

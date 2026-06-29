using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.Services;
using System.Text.Json.Serialization;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/auth")]
[AllowAnonymous]
public sealed class AuthController : ControllerBase
{
    private readonly SessionStore _sessions;

    public AuthController(SessionStore sessions) => _sessions = sessions;

    // POST /api/auth/session  — login
    [HttpPost("session")]
    public IActionResult Login([FromBody] LoginRequest req)
    {
        var userId = req.GetUserId();
        if (string.IsNullOrWhiteSpace(userId) || string.IsNullOrWhiteSpace(req.Password))
            return BadRequest(Error("User ID and password are required."));

        var (token, error) = _sessions.Login(userId.Trim(), req.Password);
        if (token is null)
            return Unauthorized(Error(error ?? "Invalid credentials."));

        var session = _sessions.ValidateToken(token)!;
        return Ok(new
        {
            data = new
            {
                token,
                user_id = session.UserId,
                role    = session.Role,
                email   = session.Email,
            }
        });
    }

    // POST /api/auth/register
    [HttpPost("register")]
    public IActionResult Register([FromBody] RegisterRequest req)
    {
        var userId = req.GetUserId();
        if (string.IsNullOrWhiteSpace(userId) || string.IsNullOrWhiteSpace(req.Email) || string.IsNullOrWhiteSpace(req.Password))
            return BadRequest(Error("User ID, email, and password are required."));

        var (success, error) = _sessions.Register(userId.Trim(), req.Email.Trim(), req.Password);
        if (!success)
            return Conflict(Error(error ?? "Registration failed."));

        return Ok(new { data = new { message = "Account created successfully." } });
    }

    // POST /api/auth/password-reset/request
    [HttpPost("password-reset/request")]
    public IActionResult PasswordResetRequest([FromBody] PasswordResetRequest req)
    {
        // Demo-only: always return success to avoid user enumeration
        return Ok(new { data = new { message = "If that user exists, a reset link has been sent." } });
    }

    // DELETE /api/auth/session  — logout
    [HttpDelete("session")]
    public IActionResult Logout()
    {
        return Ok(new { data = new { message = "Signed out." } });
    }

    private static object Error(string message) =>
        new { error = new { message } };
}

public sealed class LoginRequest
{
    public string? UserId { get; init; }

    [JsonPropertyName("user_id")]
    public string? UserIdSnake { get; init; }

    public string? Password { get; init; }

    public string? GetUserId() =>
        !string.IsNullOrWhiteSpace(UserId) ? UserId : UserIdSnake;
}

public sealed class RegisterRequest
{
    public string? UserId { get; init; }

    [JsonPropertyName("user_id")]
    public string? UserIdSnake { get; init; }

    public string? Email { get; init; }

    public string? Password { get; init; }

    public string? GetUserId() =>
        !string.IsNullOrWhiteSpace(UserId) ? UserId : UserIdSnake;
}

public sealed class PasswordResetRequest
{
    public string? UserId { get; init; }

    [JsonPropertyName("user_id")]
    public string? UserIdSnake { get; init; }

    public string? GetUserId() =>
        !string.IsNullOrWhiteSpace(UserId) ? UserId : UserIdSnake;
}

using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.Controllers;
using PropelIQ.Api.Services;

namespace PropelIQ.Tests.Controllers;

public sealed class AuthControllerTests
{
    private static AuthController CreateController() =>
        new(new SessionStore());

    [Fact]
    public void Register_WithSnakeCaseUserId_ReturnsOk()
    {
        var controller = CreateController();
        var req = new RegisterRequest
        {
            UserIdSnake = $"snake_{Guid.NewGuid():N}"[..14],
            Email = "snake.case@example.com",
            Password = "Password123!"
        };

        var result = controller.Register(req);

        result.Should().BeOfType<OkObjectResult>();
    }

    [Fact]
    public void Login_WithSnakeCaseUserId_ReturnsOk()
    {
        var controller = CreateController();
        var req = new LoginRequest
        {
            UserIdSnake = "patient1",
            Password = "Patient123!"
        };

        var result = controller.Login(req);

        result.Should().BeOfType<OkObjectResult>();
    }

    [Fact]
    public void Register_MissingUserIdAcrossBothFields_ReturnsBadRequest()
    {
        var controller = CreateController();
        var req = new RegisterRequest
        {
            Email = "missing.user@example.com",
            Password = "Password123!"
        };

        var result = controller.Register(req);

        result.Should().BeOfType<BadRequestObjectResult>();
    }
}

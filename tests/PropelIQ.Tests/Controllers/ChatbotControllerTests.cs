using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Moq;
using PropelIQ.Api.Controllers;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using Xunit;
using FluentAssertions;

namespace PropelIQ.Tests.Controllers;

public sealed class ChatbotControllerTests
{
    private readonly Mock<IChatbotService> _serviceMock = new();
    private readonly Mock<ILogger<ChatbotController>> _loggerMock = new();

    private ChatbotController CreateController() =>
        new(_serviceMock.Object, _loggerMock.Object);

    [Fact]
    public async Task StartChat_ValidRequest_Returns200WithConversationId()
    {
        _serviceMock
            .Setup(s => s.StartSessionAsync(It.IsAny<StartChatRequest>(), default))
            .ReturnsAsync(new StartChatResult(5, "Hello Jane! What brings you in today?", 1, 6));

        var controller = CreateController();
        var result = await controller.StartChat(
            new StartChatRequestDto(1, 100, "Jane Doe"),
            CancellationToken.None);

        var ok = result.Should().BeOfType<OkObjectResult>().Subject;
        ok.StatusCode.Should().Be(200);
    }

    [Fact]
    public async Task GetHistory_NotFound_Returns404()
    {
        _serviceMock
            .Setup(s => s.GetHistoryAsync(999, default))
            .ThrowsAsync(new InvalidOperationException("not found"));

        var controller = CreateController();
        var result = await controller.GetHistory(999, CancellationToken.None);

        result.Should().BeOfType<NotFoundResult>();
    }
}

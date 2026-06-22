using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Moq;
using PropelIQ.Api.Controllers;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Domain.Entities;
using Xunit;
using FluentAssertions;

namespace PropelIQ.Tests.Controllers;

public sealed class ChatbotFallbackControllerTests
{
    private readonly Mock<IIntakeConversationRepository> _repoMock = new();
    private readonly Mock<ILogger<ChatbotFallbackController>> _loggerMock = new();

    private ChatbotFallbackController CreateController() =>
        new(_repoMock.Object, _loggerMock.Object);

    [Fact]
    public async Task SwitchToManual_ExistingConversation_Returns204AndPersists()
    {
        var conversation = IntakeConversation.Start(1, 100);
        _repoMock.Setup(r => r.GetByIdAsync(1, default)).ReturnsAsync(conversation);

        var controller = CreateController();
        var result = await controller.SwitchToManual(1, CancellationToken.None);

        result.Should().BeOfType<NoContentResult>();
        conversation.SwitchedToManualAt.Should().NotBeNull();
        _repoMock.Verify(r => r.UpdateAsync(conversation, default), Times.Once);
    }

    [Fact]
    public async Task SwitchToManual_NotFound_Returns404()
    {
        _repoMock.Setup(r => r.GetByIdAsync(999, default)).ReturnsAsync((IntakeConversation?)null);

        var controller = CreateController();
        var result = await controller.SwitchToManual(999, CancellationToken.None);

        result.Should().BeOfType<NotFoundResult>();
    }
}

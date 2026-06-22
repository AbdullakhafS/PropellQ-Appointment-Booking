using Moq;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Chatbot;
using Xunit;
using FluentAssertions;

namespace PropelIQ.Tests.Services;

public sealed class ChatbotServiceTests
{
    private readonly Mock<IIntakeConversationRepository> _conversationRepoMock = new();
    private readonly Mock<IChatbotPromptRepository> _promptRepoMock = new();
    private readonly Mock<ILogger<ChatbotService>> _loggerMock = new();

    private ChatbotService CreateService(ChatbotOptions? options = null)
    {
        var opts = Options.Create(options ?? new ChatbotOptions
        {
            ApiKey = "test-key",
            DeploymentName = "gpt-4o",
            TimeoutSeconds = 5,
            MaxRetryAttempts = 1,
            MaxContextTokens = 3000
        });
        return new ChatbotService(_conversationRepoMock.Object, _promptRepoMock.Object, opts, _loggerMock.Object);
    }

    [Fact]
    public async Task StartSessionAsync_CreatesConversationAndReturnsWelcome()
    {
        _promptRepoMock.Setup(r => r.GetActivePromptAsync(default)).ReturnsAsync((ChatbotPrompt?)null);
        _conversationRepoMock
            .Setup(r => r.CreateAsync(It.IsAny<IntakeConversation>(), default))
            .ReturnsAsync(42);

        var service = CreateService();
        var result = await service.StartSessionAsync(new StartChatRequest(1, 100, "Jane Doe"));

        result.ConversationId.Should().Be(42);
        result.WelcomeMessage.Should().Contain("Jane");
        result.WelcomeMessage.Should().Contain("brings you in");

        _conversationRepoMock.Verify(r => r.CreateAsync(It.IsAny<IntakeConversation>(), default), Times.Once);
    }

    [Fact]
    public async Task GetHistoryAsync_NonExistentConversation_ThrowsInvalidOperationException()
    {
        _conversationRepoMock.Setup(r => r.GetByIdAsync(999, default)).ReturnsAsync((IntakeConversation?)null);

        var service = CreateService();
        await Assert.ThrowsAsync<InvalidOperationException>(() => service.GetHistoryAsync(999));
    }
}

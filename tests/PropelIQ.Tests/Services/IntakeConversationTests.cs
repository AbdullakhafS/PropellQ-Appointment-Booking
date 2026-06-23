using PropelIQ.Domain.Entities;
using PropelIQ.Domain.Enums;
using PropelIQ.Domain.ValueObjects;
using Xunit;
using FluentAssertions;

namespace PropelIQ.Tests.Services;

public sealed class IntakeConversationTests
{
    [Fact]
    public void Start_CreatesConversationWithAiModeAndTimestamp()
    {
        var before = DateTimeOffset.UtcNow;
        var conv = IntakeConversation.Start(5, 99);

        conv.AppointmentId.Should().Be(5);
        conv.PatientId.Should().Be(99);
        conv.Mode.Should().Be(IntakeMode.Ai);
        conv.CreatedAt.Should().BeOnOrAfter(before);
        conv.Transcript.Should().BeEmpty();
        conv.MisunderstandingCount.Should().Be(0);
    }

    [Fact]
    public void IncrementMisunderstanding_IncrementsCounter()
    {
        var conv = IntakeConversation.Start(1, 1);
        conv.IncrementMisunderstanding();
        conv.IncrementMisunderstanding();
        conv.MisunderstandingCount.Should().Be(2);
    }

    [Fact]
    public void SwitchToManual_SetsModeAndTimestamp()
    {
        var conv = IntakeConversation.Start(1, 1);
        conv.SwitchToManual();

        conv.Mode.Should().Be(IntakeMode.Manual);
        conv.SwitchedToManualAt.Should().NotBeNull();
    }

    [Fact]
    public void MarkCompleted_SetsCompletedAt()
    {
        var conv = IntakeConversation.Start(1, 1);
        conv.MarkCompleted();
        conv.CompletedAt.Should().NotBeNull();
    }

    [Fact]
    public void GetTruncatedHistory_ReturnsSystemAndRecentMessages_WhenOverBudget()
    {
        var conv = IntakeConversation.Start(1, 1);
        conv.AppendMessage(ConversationMessage.System("System prompt here"));

        // Add 100 large messages to exceed token budget
        for (int i = 0; i < 100; i++)
            conv.AppendMessage(i % 2 == 0
                ? ConversationMessage.User(new string('a', 200))
                : ConversationMessage.Assistant(new string('b', 200)));

        var history = conv.GetTruncatedHistory(maxTokens: 500);

        history.Should().NotBeEmpty();
        history[0].Role.Should().Be("system", "system message should always be preserved");
        history.Count.Should().BeLessThan(conv.Transcript.Count);
    }

    [Fact]
    public void UpdateExtractedData_StoresDataAndScores()
    {
        var conv = IntakeConversation.Start(1, 1);
        var data = new ExtractedIntakeData("headache", ["asthma"], [], [], null);
        var scores = new ConfidenceScores(0.9, 0.8, 0.0, 0.0, 0.0);

        conv.UpdateExtractedData(data, scores);

        conv.ExtractedData.ChiefComplaint.Should().Be("headache");
        conv.ConfidenceScores.ChiefComplaint.Should().Be(0.9);
    }
}

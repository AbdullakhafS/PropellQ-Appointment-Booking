using PropelIQ.Domain.Enums;
using PropelIQ.Domain.ValueObjects;

namespace PropelIQ.Domain.Entities;

public sealed class IntakeConversation
{
    public int Id { get; private set; }
    public int AppointmentId { get; private set; }
    public int PatientId { get; private set; }
    public IntakeMode Mode { get; private set; }
    public IList<ConversationMessage> Transcript { get; private set; } = [];
    public ExtractedIntakeData ExtractedData { get; private set; } = ExtractedIntakeData.Empty();
    public ConfidenceScores ConfidenceScores { get; private set; } = ConfidenceScores.Zero();
    public DateTimeOffset? CompletedAt { get; private set; }
    public DateTimeOffset? SwitchedToManualAt { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }
    public int MisunderstandingCount { get; private set; }
    public ConversationStage CurrentStage { get; private set; } = ConversationStage.Greeting;

    private IntakeConversation() { }

    public static IntakeConversation Start(int appointmentId, int patientId)
        => new()
        {
            AppointmentId = appointmentId,
            PatientId = patientId,
            Mode = IntakeMode.Ai,
            CreatedAt = DateTimeOffset.UtcNow
        };

    public static IntakeConversation StartManual(int appointmentId, int patientId)
        => new()
        {
            AppointmentId = appointmentId,
            PatientId = patientId,
            Mode = IntakeMode.Manual,
            CreatedAt = DateTimeOffset.UtcNow
        };

    public void AppendMessage(ConversationMessage message)
        => Transcript.Add(message);

    public void UpdateExtractedData(ExtractedIntakeData data, ConfidenceScores scores)
    {
        ExtractedData = data;
        ConfidenceScores = scores;
    }

    public void IncrementMisunderstanding() => MisunderstandingCount++;

    public void AdvanceStage(ConversationStage stage)
    {
        if (stage > CurrentStage)
            CurrentStage = stage;
    }

    public void MarkCompleted()
        => CompletedAt = DateTimeOffset.UtcNow;

    public void SwitchToManual()
    {
        Mode = IntakeMode.Manual;
        SwitchedToManualAt = DateTimeOffset.UtcNow;
    }

    public IReadOnlyList<ConversationMessage> GetTruncatedHistory(int maxTokens = 3000)
    {
        var messages = Transcript.ToList();
        // Keep system message (index 0) and trim oldest user/assistant turns first
        if (messages.Count <= 2)
            return messages.AsReadOnly();

        var systemMessages = messages.Where(m => m.Role == "system").ToList();
        var conversationMessages = messages.Where(m => m.Role != "system").ToList();

        // Approximate token count: 1 token ≈ 4 characters
        var budget = maxTokens;
        var retained = new List<ConversationMessage>();

        for (int i = conversationMessages.Count - 1; i >= 0; i--)
        {
            var cost = conversationMessages[i].Content.Length / 4;
            if (budget - cost < 500) break; // reserve 500 tokens for response
            budget -= cost;
            retained.Insert(0, conversationMessages[i]);
        }

        return [.. systemMessages, .. retained];
    }
}

namespace PropelIQ.Domain.Entities;

public sealed class ChatbotPrompt
{
    public int Id { get; private set; }
    public string PromptVersion { get; private set; } = string.Empty;
    public string PromptText { get; private set; } = string.Empty;
    public DateTimeOffset EffectiveDate { get; private set; }
    public DateTimeOffset? DeprecatedAt { get; private set; }

    private ChatbotPrompt() { }

    public static ChatbotPrompt Create(string version, string promptText)
        => new()
        {
            PromptVersion = version,
            PromptText = promptText,
            EffectiveDate = DateTimeOffset.UtcNow
        };

    public bool IsActive => DeprecatedAt is null;

    public void Deprecate() => DeprecatedAt = DateTimeOffset.UtcNow;
}

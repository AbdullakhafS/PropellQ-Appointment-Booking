namespace PropelIQ.Domain.ValueObjects;

public sealed record ConversationMessage(
    string Role,
    string Content,
    DateTimeOffset Timestamp
)
{
    public static ConversationMessage User(string content) =>
        new("user", content, DateTimeOffset.UtcNow);

    public static ConversationMessage Assistant(string content) =>
        new("assistant", content, DateTimeOffset.UtcNow);

    public static ConversationMessage System(string content) =>
        new("system", content, DateTimeOffset.UtcNow);
}

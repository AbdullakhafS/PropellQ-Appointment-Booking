namespace PropelIQ.Infrastructure.Chatbot;

public sealed class ChatbotOptions
{
    public const string SectionName = "Chatbot";

    /// <summary>Azure OpenAI endpoint or OpenAI base URL.</summary>
    public string Endpoint { get; init; } = string.Empty;

    /// <summary>API key – loaded from environment/secrets, never from appsettings.json.</summary>
    public string ApiKey { get; init; } = string.Empty;

    /// <summary>Deployment name (Azure OpenAI) or model name (OpenAI).</summary>
    public string DeploymentName { get; init; } = "gpt-4o";

    /// <summary>Max tokens for the completion response.</summary>
    public int MaxResponseTokens { get; init; } = 512;

    /// <summary>Timeout in seconds for each LLM call.</summary>
    public int TimeoutSeconds { get; init; } = 10;

    /// <summary>Max retry attempts on transient failures.</summary>
    public int MaxRetryAttempts { get; init; } = 3;

    /// <summary>Approximate max context tokens to send per turn.</summary>
    public int MaxContextTokens { get; init; } = 3000;
}

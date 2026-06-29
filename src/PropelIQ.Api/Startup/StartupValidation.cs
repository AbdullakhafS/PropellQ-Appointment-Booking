namespace PropelIQ.Api.Startup;

public static class StartupValidation
{
    public static void EnsureApiKeyConfigured(string environmentName, string? apiKey)
    {
        if (!string.Equals(environmentName, "Development", StringComparison.OrdinalIgnoreCase)
            && string.IsNullOrWhiteSpace(apiKey))
        {
            throw new InvalidOperationException("Configuration Auth:ApiKey is required outside Development.");
        }
    }
}

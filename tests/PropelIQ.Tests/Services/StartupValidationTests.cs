using PropelIQ.Api.Startup;

namespace PropelIQ.Tests.Services;

public sealed class StartupValidationTests
{
    [Fact]
    public void EnsureApiKeyConfigured_Development_AllowsEmptyApiKey()
    {
        var exception = Record.Exception(() =>
            StartupValidation.EnsureApiKeyConfigured("Development", string.Empty));

        Assert.Null(exception);
    }

    [Fact]
    public void EnsureApiKeyConfigured_Production_ThrowsWhenApiKeyMissing()
    {
        Assert.Throws<InvalidOperationException>(() =>
            StartupValidation.EnsureApiKeyConfigured("Production", string.Empty));
    }

    [Fact]
    public void EnsureApiKeyConfigured_Production_AllowsConfiguredApiKey()
    {
        var exception = Record.Exception(() =>
            StartupValidation.EnsureApiKeyConfigured("Production", "super-secret-key"));

        Assert.Null(exception);
    }
}

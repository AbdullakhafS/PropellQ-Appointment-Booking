using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Tests.TestInfrastructure;

internal static class TestServiceFactory
{
    public static IServiceScopeFactory CreateScopeFactory(string? databaseName = null)
    {
        var services = new ServiceCollection();
        var dbName = databaseName ?? $"propeliq-tests-{Guid.NewGuid():N}";

        services.AddDbContext<AppDbContext>(options =>
            options.UseInMemoryDatabase(dbName));

        var provider = services.BuildServiceProvider();
        return provider.GetRequiredService<IServiceScopeFactory>();
    }

    public static AppDbContext CreateDbContext(string? databaseName = null)
    {
        var dbName = databaseName ?? $"propeliq-tests-{Guid.NewGuid():N}";
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options;

        return new AppDbContext(options);
    }
}
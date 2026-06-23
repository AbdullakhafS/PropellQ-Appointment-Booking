using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Infrastructure.Chatbot;
using PropelIQ.Infrastructure.Data;
using PropelIQ.Infrastructure.Repositories;
using PropelIQ.Infrastructure.Security;

namespace PropelIQ.Infrastructure;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddInfrastructure(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        // Encryption (transcript PII - HIPAA)
        services.Configure<TranscriptEncryptionOptions>(
            configuration.GetSection(TranscriptEncryptionOptions.SectionName));
        services.AddSingleton<TranscriptEncryption>();

        services.AddDbContext<AppDbContext>(options =>
            options.UseSqlServer(
                configuration.GetConnectionString("DefaultConnection"),
                sql => sql.MigrationsAssembly(typeof(AppDbContext).Assembly.FullName)));

        services.Configure<ChatbotOptions>(configuration.GetSection(ChatbotOptions.SectionName));

        services.AddScoped<IIntakeConversationRepository, IntakeConversationRepository>();
        services.AddScoped<IChatbotPromptRepository, ChatbotPromptRepository>();
        services.AddScoped<IChatbotService, ChatbotService>();

        return services;
    }
}

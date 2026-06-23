using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Infrastructure.Chatbot;
using PropelIQ.Infrastructure.Data;
using PropelIQ.Infrastructure.Draft;
using PropelIQ.Infrastructure.Insurance;
using PropelIQ.Infrastructure.ManualIntake;
using PropelIQ.Infrastructure.Repositories;
using PropelIQ.Infrastructure.Security;
using PropelIQ.Infrastructure.Storage;

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
        services.AddScoped<IIntakeDraftRepository, IntakeDraftRepository>();
        services.AddScoped<IChatbotService, ChatbotService>();
        services.AddScoped<IManualIntakeService, ManualIntakeService>();
        services.AddScoped<IIntakeDraftService, IntakeDraftService>();
        services.AddScoped<IInsurancePreCheckService, InsurancePreCheckService>();
        services.AddScoped<IInsuranceReviewService, InsuranceReviewService>();
        services.AddScoped<IIntakeStorageService, IntakeStorageService>();

        return services;
    }
}

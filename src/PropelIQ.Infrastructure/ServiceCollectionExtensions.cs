using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Infrastructure.Appointments;
using PropelIQ.Infrastructure.Chatbot;
using PropelIQ.Infrastructure.Data;
using PropelIQ.Infrastructure.Draft;
using PropelIQ.Infrastructure.Insurance;
using PropelIQ.Infrastructure.ManualIntake;
using PropelIQ.Infrastructure.Notifications;
using PropelIQ.Infrastructure.Queue;
using PropelIQ.Infrastructure.Repositories;
using PropelIQ.Infrastructure.Security;
using PropelIQ.Infrastructure.Slots;
using PropelIQ.Infrastructure.Storage;
using PropelIQ.Infrastructure.Waitlist;
using PropelIQ.Infrastructure.WalkIn;

namespace PropelIQ.Infrastructure;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddInfrastructure(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        // EP-002 / EP-003: Encryption, EF Core, Chatbot, Intake, Insurance, Storage
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

        // EP-004: Queue, Waitlist, Notifications
        services.AddSingleton<IQueueEventBroadcaster, QueueEventBroadcaster>();
        services.AddSingleton<ISlotAvailabilityService, SlotAvailabilityService>();
        services.AddScoped<IAppointmentDetailService, AppointmentDetailService>();
        services.AddSingleton<IWaitlistService, WaitlistService>();
        services.AddSingleton<IAutoOfferOrchestrator, AutoOfferOrchestrator>();
        services.AddSingleton<INotificationService, NotificationService>();

        services.AddScoped<IWalkInBookingService, WalkInBookingService>();
        services.AddScoped<IQueueService, QueueService>();
        services.AddScoped<IQueueStatsService, QueueStatsService>();

        return services;
    }
}

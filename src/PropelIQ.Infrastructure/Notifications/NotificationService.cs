using Microsoft.Extensions.Logging;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Infrastructure.Notifications;

/// <summary>
/// In-memory notification service.
/// Records every delivery attempt in an audit log.
/// In production, replace the delivery body with real channel adapters
/// (email, SMS, push) while keeping the same logging contract.
/// Singleton so the delivery log persists across request scopes.
/// </summary>
public sealed class NotificationService : INotificationService
{
    private static readonly List<NotificationDeliveryRecord> _log = [];
    private static readonly List<WaitlistOfferDeliveryRecord> _offerLog = [];
    private static readonly object _lock = new();

    private readonly ILogger<NotificationService> _logger;

    public NotificationService(ILogger<NotificationService> logger)
        => _logger = logger;

    public Task NotifyCancellationAsync(
        AppointmentChangeNotification notification,
        CancellationToken ct = default)
    {
        Dispatch(notification, "patient");
        Dispatch(notification, "provider");
        return Task.CompletedTask;
    }

    public Task NotifyRescheduleAsync(
        AppointmentChangeNotification notification,
        CancellationToken ct = default)
    {
        Dispatch(notification, "patient");
        Dispatch(notification, "provider");
        return Task.CompletedTask;
    }

    /// <summary>
    /// Dispatches an offer notification to the waitlisted patient (US-042 task_042_003).
    /// </summary>
    public Task NotifyWaitlistOfferAsync(
        WaitlistOfferNotification notification,
        CancellationToken ct = default)
    {
        bool delivered = true;
        string? failureReason = null;

        var record = new WaitlistOfferDeliveryRecord(
            Id: Guid.NewGuid(),
            OfferId: notification.OfferId,
            PatientId: notification.PatientId,
            PatientFullName: notification.PatientFullName,
            Delivered: delivered,
            FailureReason: failureReason,
            DispatchedAt: DateTimeOffset.UtcNow);

        lock (_lock)
            _offerLog.Add(record);

        _logger.LogInformation(
            "Waitlist offer notification dispatched: offer={OfferId} patient={PatientName} " +
            "provider={Provider} slot={SlotTime:HH:mm} expires={ExpiresAt:HH:mm} delivered={Delivered}",
            notification.OfferId, notification.PatientFullName,
            notification.ProviderName, notification.SlotStartTime,
            notification.ExpiresAt, delivered);

        return Task.CompletedTask;
    }

    public IReadOnlyList<NotificationDeliveryRecord> GetDeliveryLog(Guid appointmentId)
    {
        lock (_lock)
            return _log.Where(r => r.AppointmentId == appointmentId)
                       .OrderByDescending(r => r.DispatchedAt)
                       .ToList();
    }

    public IReadOnlyList<NotificationDeliveryRecord> GetAllDeliveryLogs()
    {
        lock (_lock)
            return _log.OrderByDescending(r => r.DispatchedAt).ToList();
    }

    public IReadOnlyList<WaitlistOfferDeliveryRecord> GetOfferDeliveryLog(Guid offerId)
    {
        lock (_lock)
            return _offerLog.Where(r => r.OfferId == offerId)
                            .OrderByDescending(r => r.DispatchedAt)
                            .ToList();
    }

    // ---------------------------------------------------------------------------

    private void Dispatch(AppointmentChangeNotification notification, string recipientType)
    {
        string recipientName = recipientType == "patient"
            ? notification.PatientFullName
            : notification.ProviderName;

        bool delivered = true;
        string? failureReason = null;

        var record = new NotificationDeliveryRecord(
            Id: Guid.NewGuid(),
            AppointmentId: notification.AppointmentId,
            RecipientType: recipientType,
            RecipientName: recipientName,
            ChangeType: notification.ChangeType,
            Delivered: delivered,
            FailureReason: failureReason,
            DispatchedAt: DateTimeOffset.UtcNow);

        lock (_lock)
            _log.Add(record);

        _logger.LogInformation(
            "Notification dispatched: type={Type} recipient={RecipientType}/{Name} appointment={ApptId} delivered={Delivered}",
            notification.ChangeType, recipientType, recipientName,
            notification.AppointmentId, delivered);
    }
}

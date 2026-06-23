using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

/// <summary>
/// Sends and records appointment change notifications (cancellation / reschedule)
/// and waitlist offer notifications.
/// Implementations should be non-throwing: failed delivery is recorded, not raised.
/// </summary>
public interface INotificationService
{
    /// <summary>
    /// Dispatches a cancellation notification to the patient and provider.
    /// </summary>
    Task NotifyCancellationAsync(
        AppointmentChangeNotification notification,
        CancellationToken ct = default);

    /// <summary>
    /// Dispatches a reschedule notification to the patient and provider.
    /// </summary>
    Task NotifyRescheduleAsync(
        AppointmentChangeNotification notification,
        CancellationToken ct = default);

    /// <summary>
    /// Dispatches an offer notification to the waitlisted patient.
    /// Called automatically by AutoOfferOrchestrator when a new offer is issued (US-042 task_042_003).
    /// </summary>
    Task NotifyWaitlistOfferAsync(
        WaitlistOfferNotification notification,
        CancellationToken ct = default);

    /// <summary>Returns appointment-change delivery records for a given appointment.</summary>
    IReadOnlyList<NotificationDeliveryRecord> GetDeliveryLog(Guid appointmentId);

    /// <summary>Returns all appointment-change delivery records (most recent first).</summary>
    IReadOnlyList<NotificationDeliveryRecord> GetAllDeliveryLogs();

    /// <summary>Returns waitlist offer delivery records for a given offer.</summary>
    IReadOnlyList<WaitlistOfferDeliveryRecord> GetOfferDeliveryLog(Guid offerId);
}

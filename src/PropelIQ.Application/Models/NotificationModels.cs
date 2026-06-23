namespace PropelIQ.Application.Models;

/// <summary>Identifies the type of schedule change that triggered a notification.</summary>
public enum AppointmentChangeType
{
    Cancelled,
    Rescheduled
}

/// <summary>
/// Data payload for an appointment change notification sent to patient and/or provider.
/// </summary>
public sealed record AppointmentChangeNotification(
    Guid AppointmentId,
    string PatientFullName,
    string ProviderName,
    AppointmentChangeType ChangeType,
    DateTimeOffset? OldAppointmentTime,
    DateTimeOffset? NewAppointmentTime,
    string? Reason
);

/// <summary>
/// Records a single notification delivery attempt — used for audit and observability.
/// </summary>
public sealed record NotificationDeliveryRecord(
    Guid Id,
    Guid AppointmentId,
    string RecipientType,       // "patient" | "provider"
    string RecipientName,
    AppointmentChangeType ChangeType,
    bool Delivered,
    string? FailureReason,
    DateTimeOffset DispatchedAt
);

// ---------------------------------------------------------------------------
// Waitlist offer notifications (US-042)
// ---------------------------------------------------------------------------

/// <summary>
/// Notification payload dispatched to a waitlisted patient when a slot offer is created.
/// </summary>
public sealed record WaitlistOfferNotification(
    Guid OfferId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    DateTimeOffset SlotStartTime,
    DateTimeOffset ExpiresAt
);

/// <summary>
/// Audit record for a waitlist offer notification delivery attempt.
/// </summary>
public sealed record WaitlistOfferDeliveryRecord(
    Guid Id,
    Guid OfferId,
    Guid PatientId,
    string PatientFullName,
    bool Delivered,
    string? FailureReason,
    DateTimeOffset DispatchedAt
);

namespace PropelIQ.Application.Models;

/// <summary>
/// Raised when an appointment slot is freed (cancelled or rescheduled)
/// and the auto-offer pipeline should run for the affected provider.
/// </summary>
public record SlotReleasedEvent(
    /// <summary>Provider identifier used to match waitlist entries.</summary>
    string ProviderId,
    /// <summary>Slot identifier; null for unslotted appointments.</summary>
    Guid? SlotId,
    /// <summary>Display name of the provider to embed in the offer notification.</summary>
    string ProviderName,
    /// <summary>Original start time of the freed slot.</summary>
    DateTimeOffset SlotTime,
    /// <summary>"cancelled" | "rescheduled"</summary>
    string ReleaseReason
);

/// <summary>
/// Result of a single auto-offer pipeline invocation.
/// </summary>
public record AutoOfferTriggerResult(
    bool OfferIssued,
    Guid? OfferId,
    /// <summary>"issued" | "no_candidates" | "idempotent_skip"</summary>
    string Reason
);

/// <summary>Result returned when an appointment is cancelled via the queue API.</summary>
public record CancelAppointmentResult(Guid AppointmentId, string Status);

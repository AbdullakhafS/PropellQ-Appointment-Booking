namespace PropelIQ.Application.Models;

// --- Waitlist join ---

public sealed record JoinWaitlistRequest(
    Guid PatientId,
    string PatientFullName,
    string ProviderId,
    string ProviderName,
    string? ClinicId,
    string? PreferredTimeContext
);

public sealed record WaitlistEntryResult(
    Guid WaitlistEntryId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    string Status,
    int Priority,
    DateTimeOffset CreatedAt
);

// --- Waitlist offer ---

public sealed record WaitlistOfferResult(
    Guid OfferId,
    Guid WaitlistEntryId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    DateTimeOffset SlotStartTime,
    string Status,
    DateTimeOffset ExpiresAt,
    DateTimeOffset? RespondedAt,
    Guid? ConvertedAppointmentId
);

// --- Accept/Decline ---

public sealed record RespondToOfferRequest(
    Guid OfferId,
    bool IsAccept
);

public sealed record OfferConversionResult(
    Guid OfferId,
    string OfferStatus,
    Guid? AppointmentId
);

// --- List ---

public sealed record WaitlistListResult(
    IReadOnlyList<WaitlistEntryResult> Entries
);

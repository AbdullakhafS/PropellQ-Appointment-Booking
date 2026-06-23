using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Waitlist;

// --- Join ---

public sealed record JoinWaitlistRequestDto(
    [Required] Guid PatientId,
    [Required, MaxLength(200)] string PatientFullName,
    [Required, MaxLength(100)] string ProviderId,
    [Required, MaxLength(200)] string ProviderName,
    [MaxLength(100)] string? ClinicId,
    [MaxLength(100)] string? PreferredTimeContext
);

public sealed record WaitlistEntryDto(
    Guid WaitlistEntryId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    string Status,
    int Priority,
    DateTimeOffset CreatedAt
);

// --- Offer ---

public sealed record WaitlistOfferDto(
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

// --- Respond ---

public sealed record RespondToOfferRequestDto(
    [Required] bool IsAccept
);

public sealed record OfferConversionResultDto(
    Guid OfferId,
    string OfferStatus,
    Guid? AppointmentId
);

// --- Issue offer ---

public sealed record IssueOfferRequestDto(
    [Required, MaxLength(100)] string ProviderId,
    [Required, MaxLength(200)] string ProviderName,
    [Required] DateTimeOffset SlotStartTime,
    Guid? SlotId = null
);

// --- Common ---

public sealed record ApiResponse<T>(bool Success, T? Data, string? Error = null)
{
    public static ApiResponse<T> Ok(T data) => new(true, data);
    public static ApiResponse<T> Fail(string error) => new(false, default, error);
}

// --- Process slot (US-042 explicit trigger) ---

public sealed record ProcessSlotRequestDto(
    [System.ComponentModel.DataAnnotations.Required, System.ComponentModel.DataAnnotations.MaxLength(200)] string ProviderId,
    [System.ComponentModel.DataAnnotations.Required, System.ComponentModel.DataAnnotations.MaxLength(200)] string ProviderName,
    [System.ComponentModel.DataAnnotations.Required] DateTimeOffset SlotTime,
    Guid? SlotId = null,
    [System.ComponentModel.DataAnnotations.MaxLength(50)] string? ReleaseReason = null
);

public sealed record ProcessSlotResponseDto(
    bool OfferIssued,
    Guid? OfferId,
    string Reason
);

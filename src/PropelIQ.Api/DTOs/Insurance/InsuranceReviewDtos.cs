using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Insurance;

// --- Pending list ---

public sealed record PendingInsuranceRowDto(
    int Id,
    int AppointmentId,
    int PatientId,
    string? PatientName,
    string? InsuranceName,
    string? MemberId,
    int? MatchedPlanId,
    string? MatchedPlanName,
    int ConfidenceScore,
    string VerificationStatus,
    DateTimeOffset? AppointmentDate,
    DateTimeOffset? LastVerifiedAt,
    DateTimeOffset CreatedAt
);

public sealed record PendingInsuranceResponseDto(
    IReadOnlyList<PendingInsuranceRowDto> Items,
    int TotalCount,
    int Page,
    int PageSize
);

// --- Verify ---

public sealed record VerifyInsuranceRequestDto(
    [Required] int StaffId,
    [Required, MaxLength(30)] string NewStatus,
    [Required, MaxLength(30)] string VerificationMethod,
    [MaxLength(1000)] string? Notes
);

public sealed record VerifyInsuranceResponseDto(
    int Id,
    string VerificationStatus,
    int VerifiedByStaffId,
    DateTimeOffset VerifiedAt
);

// --- Batch verify ---

public sealed record BatchVerifyRequestDto(
    [Required] IReadOnlyList<int> Ids,
    [Required] int StaffId,
    [Required, MaxLength(30)] string NewStatus,
    [Required, MaxLength(30)] string VerificationMethod,
    [MaxLength(1000)] string? Notes
);

public sealed record BatchVerifyResponseDto(
    IReadOnlyList<VerifyInsuranceResponseDto> Updated,
    int FailedCount
);

// --- Audit history ---

public sealed record AuditEntryDto(
    int Id,
    string PreviousStatus,
    string NewStatus,
    int VerifiedByStaffId,
    string VerificationMethod,
    string? Notes,
    DateTimeOffset VerifiedAt
);

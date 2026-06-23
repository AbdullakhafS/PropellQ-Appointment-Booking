namespace PropelIQ.Application.Models;

// --- Pending insurance list ---

public sealed record PendingInsuranceQuery(
    string? Status,
    string? InsuranceName,
    int? DateRangeDays,
    string SortBy,
    bool SortAscending,
    int Page,
    int PageSize
);

public sealed record PendingInsuranceRow(
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

public sealed record PendingInsuranceResult(
    IReadOnlyList<PendingInsuranceRow> Items,
    int TotalCount,
    int Page,
    int PageSize
);

// --- Verification update ---

public sealed record VerifyInsuranceRequest(
    int InsuranceVerificationId,
    int StaffId,
    string NewStatus,
    string VerificationMethod,
    string? Notes
);

public sealed record VerifyInsuranceResult(
    int Id,
    string VerificationStatus,
    int VerifiedByStaffId,
    DateTimeOffset VerifiedAt
);

// --- Audit history ---

public sealed record AuditEntry(
    int Id,
    string PreviousStatus,
    string NewStatus,
    int VerifiedByStaffId,
    string VerificationMethod,
    string? Notes,
    DateTimeOffset VerifiedAt
);

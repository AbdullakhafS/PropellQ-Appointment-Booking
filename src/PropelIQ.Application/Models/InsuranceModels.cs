namespace PropelIQ.Application.Models;

// --- Insurance pre-check ---

public sealed record InsurancePreCheckRequest(
    int AppointmentId,
    int PatientId,
    string? InsuranceName,
    string? MemberId,
    string? GroupNumber
);

public sealed record InsurancePreCheckResult(
    int? MatchedPlanId,
    string? MatchedPlanName,
    int ConfidenceScore,
    string VerificationStatus,
    string Reason
);

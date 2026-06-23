using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Intake;

public sealed record InsurancePreCheckRequestDto(
    [Required] int AppointmentId,
    [Required] int PatientId,
    [MaxLength(200)] string? InsuranceName,
    [MaxLength(100)] string? MemberId,
    [MaxLength(100)] string? GroupNumber
);

public sealed record InsurancePreCheckResponseDto(
    int? MatchedPlanId,
    string? MatchedPlanName,
    int ConfidenceScore,
    string VerificationStatus,
    string Reason,
    bool IsVerified
);

using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Intake;

// --- Store intake request ---

public sealed record StoreIntakeRequestDto(
    [Required] int AppointmentId,
    [Required] int PatientId,
    [Required, MaxLength(20)] string Mode,
    [MaxLength(4000)] string? ChiefComplaint,
    IReadOnlyList<IntakeHistoryDto>? MedicalHistory,
    IReadOnlyList<IntakeMedicationDto>? Medications,
    IReadOnlyList<IntakeAllergyDto>? Allergies,
    IntakeInsuranceDto? InsuranceInfo,
    [MaxLength(2000)] string? Notes
);

public sealed record IntakeHistoryDto(
    [Required, MaxLength(255)] string ConditionName,
    [MaxLength(10)] string? ConditionCode,
    int ConfidenceScore = 100
);

public sealed record IntakeMedicationDto(
    [Required, MaxLength(255)] string MedicationName,
    [MaxLength(100)] string? Dosage,
    [MaxLength(100)] string? Frequency,
    [MaxLength(50)] string? Route,
    int ConfidenceScore = 100
);

public sealed record IntakeAllergyDto(
    [Required, MaxLength(50)] string AllergenType,
    [Required, MaxLength(255)] string AllergenName,
    [Required, MaxLength(50)] string ReactionType,
    [MaxLength(500)] string? ReactionDescription,
    [MaxLength(20)] string? Severity,
    int ConfidenceScore = 100
);

public sealed record IntakeInsuranceDto(
    [MaxLength(200)] string? InsuranceName,
    [MaxLength(100)] string? MemberId,
    [MaxLength(100)] string? GroupNumber,
    [MaxLength(200)] string? PlanName
);

// --- Store intake response ---

public sealed record StoreIntakeResponseDto(
    int IntakeId,
    int AppointmentId,
    DateTimeOffset CompletedAt
);

// --- Get intake response ---

public sealed record GetIntakeResponseDto(
    int IntakeId,
    int AppointmentId,
    int PatientId,
    string Mode,
    string Status,
    string? ChiefComplaint,
    DateTimeOffset CompletedAt,
    DateTimeOffset CreatedAt,
    IReadOnlyList<IntakeHistoryDto> MedicalHistory,
    IReadOnlyList<IntakeMedicationDto> Medications,
    IReadOnlyList<IntakeAllergyDto> Allergies,
    IntakeInsuranceDto? InsuranceInfo
);

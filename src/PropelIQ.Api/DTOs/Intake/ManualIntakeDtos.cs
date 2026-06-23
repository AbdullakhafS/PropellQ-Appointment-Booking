using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Intake;

// --- Request DTOs ---

public sealed record SubmitManualIntakeRequestDto(
    [Required] int AppointmentId,
    [Required] int PatientId,
    [Required, MaxLength(2000)] string ChiefComplaint,
    IReadOnlyList<string>? MedicalHistory,
    [MaxLength(1000)] string? OtherConditions,
    IReadOnlyList<MedicationFormDto>? Medications,
    IReadOnlyList<AllergyFormDto>? Allergies,
    InsuranceFormDto? InsuranceInfo
);

public sealed record MedicationFormDto(
    [Required, MaxLength(200)] string Name,
    [MaxLength(100)] string? Dosage,
    [MaxLength(100)] string? Frequency
);

public sealed record AllergyFormDto(
    [Required, MaxLength(200)] string Allergen,
    [MaxLength(500)] string? Reaction,
    [MaxLength(50)] string? Type
);

public sealed record InsuranceFormDto(
    [MaxLength(200)] string? Provider,
    [MaxLength(100)] string? MemberId,
    [MaxLength(100)] string? GroupNumber,
    [MaxLength(200)] string? PlanName
);

// --- Response DTOs ---

public sealed record LastIntakeResponseDto(
    string? ChiefComplaint,
    IReadOnlyList<string> MedicalHistory,
    string? OtherConditions,
    IReadOnlyList<MedicationFormDto> Medications,
    IReadOnlyList<AllergyFormDto> Allergies,
    InsuranceFormDto? InsuranceInfo,
    DateTimeOffset LastUpdatedAt
);

public sealed record SubmitManualIntakeResponseDto(
    int ConversationId,
    InsurancePreCheckResponseDto? InsuranceCheck = null
);

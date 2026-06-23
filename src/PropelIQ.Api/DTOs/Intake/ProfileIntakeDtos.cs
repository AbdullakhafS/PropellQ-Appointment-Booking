using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Intake;

// --- Profile intake response (GET latest by patient) ---

public sealed record ProfileIntakeResponseDto(
    int IntakeId,
    int AppointmentId,
    int PatientId,
    string Mode,
    string Status,
    string? ChiefComplaint,
    DateTimeOffset CompletedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<ProfileHistoryDto> MedicalHistory,
    IReadOnlyList<ProfileMedicationDto> Medications,
    IReadOnlyList<ProfileAllergyDto> Allergies,
    ProfileInsuranceDto? Insurance
);

public sealed record ProfileHistoryDto(
    string ConditionName,
    string? ConditionCode,
    string ConditionStatus,
    int ConfidenceScore
);

public sealed record ProfileMedicationDto(
    string MedicationName,
    string? Dosage,
    string? Frequency,
    string? Route,
    int ConfidenceScore
);

public sealed record ProfileAllergyDto(
    string AllergenType,
    string AllergenName,
    string ReactionType,
    string? ReactionDescription,
    string? Severity,
    int ConfidenceScore
);

public sealed record ProfileInsuranceDto(
    string? InsuranceName,
    string? MemberId,
    string? GroupNumber,
    string? PlanName,
    string? VerificationStatus,
    int? ConfidenceScore
);

// --- Update intake (PATCH) ---

public sealed record UpdateIntakeRequestDto(
    [MaxLength(4000)] string? ChiefComplaint,
    IReadOnlyList<IntakeHistoryDto>? MedicalHistory,
    IReadOnlyList<IntakeMedicationDto>? Medications,
    IReadOnlyList<IntakeAllergyDto>? Allergies,
    IntakeInsuranceDto? InsuranceInfo
);

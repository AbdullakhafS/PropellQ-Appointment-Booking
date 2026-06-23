namespace PropelIQ.Application.Models;

// --- Intake storage request ---

public sealed record StoreIntakeRequest(
    int AppointmentId,
    int PatientId,
    string Mode,   // "ai" | "manual"
    string? ChiefComplaint,
    IReadOnlyList<IntakeHistoryItem> MedicalHistory,
    IReadOnlyList<IntakeMedicationItem> Medications,
    IReadOnlyList<IntakeAllergyItem> Allergies,
    IntakeInsuranceItem? InsuranceInfo,
    string? VerificationStatus,
    int? InsuranceConfidenceScore,
    string? Notes,
    int? CreatedByStaffId
);

public sealed record IntakeHistoryItem(
    string ConditionName,
    string? ConditionCode,
    int ConfidenceScore
);

public sealed record IntakeMedicationItem(
    string MedicationName,
    string? Dosage,
    string? Frequency,
    string? Route,
    int ConfidenceScore
);

public sealed record IntakeAllergyItem(
    string AllergenType,
    string AllergenName,
    string ReactionType,
    string? ReactionDescription,
    string? Severity,
    int ConfidenceScore
);

public sealed record IntakeInsuranceItem(
    string? InsuranceName,
    string? MemberId,
    string? GroupNumber,
    string? PlanName
);

// --- Result ---

public sealed record StoreIntakeResult(
    int IntakeId,
    int AppointmentId,
    DateTimeOffset CompletedAt
);

// --- Update request (profile edit) ---

public sealed record UpdateIntakeRequest(
    int IntakeId,
    int PatientId,
    string? ChiefComplaint,
    IReadOnlyList<IntakeHistoryItem> MedicalHistory,
    IReadOnlyList<IntakeMedicationItem> Medications,
    IReadOnlyList<IntakeAllergyItem> Allergies,
    IntakeInsuranceItem? InsuranceInfo,
    string ChangedBy
);

// --- Retrieval ---

public sealed record GetIntakeResult(
    int IntakeId,
    int AppointmentId,
    int PatientId,
    string Mode,
    string Status,
    string? ChiefComplaint,
    DateTimeOffset CompletedAt,
    DateTimeOffset CreatedAt,
    IReadOnlyList<IntakeHistoryItem> MedicalHistory,
    IReadOnlyList<IntakeMedicationItem> Medications,
    IReadOnlyList<IntakeAllergyItem> Allergies,
    IntakeInsuranceItem? InsuranceInfo
);

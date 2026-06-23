using PropelIQ.Domain.ValueObjects;

namespace PropelIQ.Application.Models;

// --- Manual intake requests ---

public sealed record GetLastIntakeRequest(int PatientId);

public sealed record SubmitManualIntakeRequest(
    int AppointmentId,
    int PatientId,
    string? ChiefComplaint,
    IReadOnlyList<string> MedicalHistory,
    string? OtherConditions,
    IReadOnlyList<MedicationEntryDto> Medications,
    IReadOnlyList<AllergyEntryDto> Allergies,
    InsuranceInfoDto? InsuranceInfo
);

// --- Manual intake results ---

public sealed record LastIntakeResult(
    string? ChiefComplaint,
    IReadOnlyList<string> MedicalHistory,
    string? OtherConditions,
    IReadOnlyList<MedicationEntryDto> Medications,
    IReadOnlyList<AllergyEntryDto> Allergies,
    InsuranceInfoDto? InsuranceInfo,
    DateTimeOffset LastUpdatedAt
);

public sealed record SubmitManualIntakeResult(int ConversationId);

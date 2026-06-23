namespace PropelIQ.Domain.ValueObjects;

public sealed record ExtractedIntakeData(
    string? ChiefComplaint,
    IReadOnlyList<string> MedicalHistory,
    IReadOnlyList<MedicationEntry> Medications,
    IReadOnlyList<AllergyEntry> Allergies,
    InsuranceInfo? InsuranceInfo
)
{
    public static ExtractedIntakeData Empty() =>
        new(null, [], [], [], null);
}

public sealed record MedicationEntry(string Name, string? Dosage, string? Frequency);

public sealed record AllergyEntry(string Allergen, string? Reaction, AllergyType Type);

public sealed record InsuranceInfo(
    string? Provider,
    string? MemberId,
    string? GroupNumber,
    string? PlanName = null
);

public enum AllergyType
{
    DrugAllergy,
    SideEffect,
    Unknown
}

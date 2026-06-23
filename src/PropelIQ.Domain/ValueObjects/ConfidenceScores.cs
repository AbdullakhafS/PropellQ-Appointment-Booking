namespace PropelIQ.Domain.ValueObjects;

public sealed record ConfidenceScores(
    double ChiefComplaint,
    double MedicalHistory,
    double Medications,
    double Allergies,
    double InsuranceInfo
)
{
    public static ConfidenceScores Zero() => new(0, 0, 0, 0, 0);
}

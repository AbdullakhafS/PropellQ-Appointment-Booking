namespace PropelIQ.Domain.Entities;

public sealed class IntakeMedication
{
    public int Id { get; private set; }
    public int IntakeId { get; private set; }
    public string MedicationName { get; private set; } = string.Empty;
    public string? Dosage { get; private set; }
    public string? Frequency { get; private set; }
    public string? Route { get; private set; }       // oral | injection | inhaler | etc.
    public int ConfidenceScore { get; private set; } = 100;
    public string? Notes { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private IntakeMedication() { }

    public static IntakeMedication Create(
        int intakeId,
        string medicationName,
        string? dosage,
        string? frequency,
        string? route,
        int confidenceScore,
        string? notes)
        => new()
        {
            IntakeId = intakeId,
            MedicationName = medicationName,
            Dosage = dosage,
            Frequency = frequency,
            Route = route,
            ConfidenceScore = Math.Clamp(confidenceScore, 0, 100),
            Notes = notes,
            CreatedAt = DateTimeOffset.UtcNow
        };
}

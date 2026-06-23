namespace PropelIQ.Domain.Entities;

public sealed class IntakeMedicalHistory
{
    public int Id { get; private set; }
    public int IntakeId { get; private set; }
    public string ConditionName { get; private set; } = string.Empty;
    public string? ConditionCode { get; private set; }       // ICD-10 if available
    public DateOnly? DiagnosedDate { get; private set; }
    public string Status { get; private set; } = "active";  // active | inactive | resolved
    public int ConfidenceScore { get; private set; } = 100;
    public string? Notes { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private IntakeMedicalHistory() { }

    public static IntakeMedicalHistory Create(
        int intakeId,
        string conditionName,
        string? conditionCode,
        int confidenceScore,
        string? notes)
        => new()
        {
            IntakeId = intakeId,
            ConditionName = conditionName,
            ConditionCode = conditionCode,
            ConfidenceScore = Math.Clamp(confidenceScore, 0, 100),
            Notes = notes,
            CreatedAt = DateTimeOffset.UtcNow
        };
}

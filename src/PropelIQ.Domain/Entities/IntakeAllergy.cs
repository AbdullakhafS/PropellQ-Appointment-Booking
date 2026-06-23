namespace PropelIQ.Domain.Entities;

public sealed class IntakeAllergy
{
    public int Id { get; private set; }
    public int IntakeId { get; private set; }
    public string AllergenType { get; private set; } = string.Empty;  // drug | food | environmental
    public string AllergenName { get; private set; } = string.Empty;
    public string ReactionType { get; private set; } = string.Empty;  // allergic | side_effect | unknown
    public string? ReactionDescription { get; private set; }
    public string? Severity { get; private set; }                     // mild | moderate | severe
    public int ConfidenceScore { get; private set; } = 100;
    public DateTimeOffset CreatedAt { get; private set; }

    private IntakeAllergy() { }

    public static IntakeAllergy Create(
        int intakeId,
        string allergenType,
        string allergenName,
        string reactionType,
        string? reactionDescription,
        string? severity,
        int confidenceScore)
        => new()
        {
            IntakeId = intakeId,
            AllergenType = allergenType,
            AllergenName = allergenName,
            ReactionType = reactionType,
            ReactionDescription = reactionDescription,
            Severity = severity,
            ConfidenceScore = Math.Clamp(confidenceScore, 0, 100),
            CreatedAt = DateTimeOffset.UtcNow
        };
}

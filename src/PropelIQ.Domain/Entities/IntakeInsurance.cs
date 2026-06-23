namespace PropelIQ.Domain.Entities;

public sealed class IntakeInsurance
{
    public int Id { get; private set; }
    public int IntakeId { get; private set; }
    public string? InsuranceName { get; private set; }
    public string? MemberId { get; private set; }
    public string? GroupNumber { get; private set; }
    public string? PlanName { get; private set; }
    public string? VerificationStatus { get; private set; }  // verified | unverified | manual_review
    public int? ConfidenceScore { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private IntakeInsurance() { }

    public static IntakeInsurance Create(
        int intakeId,
        string? insuranceName,
        string? memberId,
        string? groupNumber,
        string? planName,
        string? verificationStatus,
        int? confidenceScore)
        => new()
        {
            IntakeId = intakeId,
            InsuranceName = insuranceName,
            MemberId = memberId,
            GroupNumber = groupNumber,
            PlanName = planName,
            VerificationStatus = verificationStatus,
            ConfidenceScore = confidenceScore,
            CreatedAt = DateTimeOffset.UtcNow
        };
}

namespace PropelIQ.Domain.Entities;

/// <summary>
/// Audit entry written every time a staff member changes an InsuranceVerification status.
/// </summary>
public sealed class InsuranceVerificationAudit
{
    public int Id { get; private set; }
    public int InsuranceVerificationId { get; private set; }
    public string PreviousStatus { get; private set; } = string.Empty;
    public string NewStatus { get; private set; } = string.Empty;
    public int VerifiedByStaffId { get; private set; }
    public string VerificationMethod { get; private set; } = string.Empty;
    public string? Notes { get; private set; }
    public DateTimeOffset VerifiedAt { get; private set; }

    private InsuranceVerificationAudit() { }

    public static InsuranceVerificationAudit Create(
        int insuranceVerificationId,
        string previousStatus,
        string newStatus,
        int staffId,
        string verificationMethod,
        string? notes)
        => new()
        {
            InsuranceVerificationId = insuranceVerificationId,
            PreviousStatus = previousStatus,
            NewStatus = newStatus,
            VerifiedByStaffId = staffId,
            VerificationMethod = verificationMethod,
            Notes = notes,
            VerifiedAt = DateTimeOffset.UtcNow
        };
}

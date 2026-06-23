namespace PropelIQ.Domain.Entities;

/// <summary>
/// Audit record for every insurance pre-check performed during intake.
/// </summary>
public sealed class InsuranceVerification
{
    public int Id { get; private set; }
    public int AppointmentId { get; private set; }
    public int PatientId { get; private set; }
    public string? ProvidedInsuranceName { get; private set; }
    public string? ProvidedMemberId { get; private set; }
    public string? ProvidedGroupNumber { get; private set; }
    public int? MatchedPlanId { get; private set; }
    public int ConfidenceScore { get; private set; }
    public string VerificationStatus { get; private set; } = string.Empty;
    public string? Reason { get; private set; }
    public string CheckedBy { get; private set; } = "system";
    public int? VerifiedByStaffId { get; private set; }
    public DateTimeOffset? VerifiedAt { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private InsuranceVerification() { }

    public static InsuranceVerification Create(
        int appointmentId,
        int patientId,
        string? insuranceName,
        string? memberId,
        string? groupNumber,
        int? matchedPlanId,
        int confidenceScore,
        string verificationStatus,
        string? reason)
        => new()
        {
            AppointmentId = appointmentId,
            PatientId = patientId,
            ProvidedInsuranceName = insuranceName,
            ProvidedMemberId = memberId,
            ProvidedGroupNumber = groupNumber,
            MatchedPlanId = matchedPlanId,
            ConfidenceScore = confidenceScore,
            VerificationStatus = verificationStatus,
            Reason = reason,
            CreatedAt = DateTimeOffset.UtcNow
        };

    public void StaffVerify(int staffId, string status, string verificationMethod, string? notes)
    {
        VerifiedByStaffId = staffId;
        VerifiedAt = DateTimeOffset.UtcNow;
        VerificationStatus = status;
    }

    /// <summary>Legacy single-step verify (always sets status to "verified").</summary>
    public void StaffVerify(int staffId)
        => StaffVerify(staffId, "verified", "system", null);
}

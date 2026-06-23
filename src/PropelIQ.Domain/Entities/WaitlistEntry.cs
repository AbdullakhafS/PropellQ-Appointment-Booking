namespace PropelIQ.Domain.Entities;

/// <summary>
/// Represents a patient's position in the waitlist for a specific provider/slot context.
/// States: queued → offered → fulfilled | cancelled
/// </summary>
public sealed class WaitlistEntry
{
    public Guid Id { get; private set; }
    public Guid PatientId { get; private set; }
    public string PatientFullName { get; private set; } = string.Empty;
    public string ProviderId { get; private set; } = string.Empty;
    public string ProviderName { get; private set; } = string.Empty;
    public string? ClinicId { get; private set; }
    public string? PreferredTimeContext { get; private set; }  // e.g. "morning", "afternoon"
    public string Status { get; private set; } = "queued";    // queued | offered | fulfilled | cancelled
    public int Priority { get; private set; }                  // lower = higher priority (FIFO by default)
    public DateTimeOffset CreatedAt { get; private set; }

    private WaitlistEntry() { }

    public static WaitlistEntry Create(
        Guid patientId,
        string patientFullName,
        string providerId,
        string providerName,
        string? clinicId,
        string? preferredTimeContext,
        int priority)
        => new()
        {
            Id = Guid.NewGuid(),
            PatientId = patientId,
            PatientFullName = patientFullName,
            ProviderId = providerId,
            ProviderName = providerName,
            ClinicId = clinicId,
            PreferredTimeContext = preferredTimeContext,
            Status = "queued",
            Priority = priority,
            CreatedAt = DateTimeOffset.UtcNow
        };

    public void MarkOffered() => Status = "offered";
    public void MarkFulfilled() => Status = "fulfilled";
    public void MarkCancelled() => Status = "cancelled";
    public void RevertToQueued() => Status = "queued";   // when offer expires/declined — re-queue
}

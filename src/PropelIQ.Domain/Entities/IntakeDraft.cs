namespace PropelIQ.Domain.Entities;

/// <summary>
/// Persists a partial intake payload so patients can resume or switch modes without losing data.
/// Drafts expire after 24 hours (enforced at query time).
/// </summary>
public sealed class IntakeDraft
{
    public int Id { get; private set; }
    public int AppointmentId { get; private set; }
    public int PatientId { get; private set; }
    public string Mode { get; private set; } = string.Empty;
    public string DataJson { get; private set; } = "{}";
    public int SwitchCount { get; private set; }
    public DateTimeOffset LastUpdated { get; private set; }
    public DateTimeOffset ExpiresAt { get; private set; }

    private IntakeDraft() { }

    public static IntakeDraft Create(
        int appointmentId,
        int patientId,
        string mode,
        string dataJson,
        int switchCount)
        => new()
        {
            AppointmentId = appointmentId,
            PatientId = patientId,
            Mode = mode,
            DataJson = dataJson,
            SwitchCount = switchCount,
            LastUpdated = DateTimeOffset.UtcNow,
            ExpiresAt = DateTimeOffset.UtcNow.AddHours(24)
        };

    public void Update(string mode, string dataJson, int switchCount)
    {
        Mode = mode;
        DataJson = dataJson;
        SwitchCount = switchCount;
        LastUpdated = DateTimeOffset.UtcNow;
        ExpiresAt = DateTimeOffset.UtcNow.AddHours(24);
    }

    public bool IsExpired => DateTimeOffset.UtcNow >= ExpiresAt;
}

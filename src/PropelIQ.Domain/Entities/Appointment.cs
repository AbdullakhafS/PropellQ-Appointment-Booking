namespace PropelIQ.Domain.Entities;

/// <summary>
/// Appointment record. Walk-in appointments are flagged with IsWalkIn = true.
/// </summary>
public sealed class Appointment
{
    public Guid Id { get; private set; }
    public Guid PatientId { get; private set; }
    public string PatientFullName { get; private set; } = string.Empty;
    public string ProviderName { get; private set; } = string.Empty;
    public DateTimeOffset AppointmentTime { get; private set; }
    public int DurationMinutes { get; private set; }
    public bool IsWalkIn { get; private set; }
    public Guid? SlotId { get; private set; }
    public string Status { get; private set; } = "scheduled"; // scheduled | arrived | completed | cancelled
    public string? Notes { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }
    /// <summary>Set when the patient checks in (status → arrived). Used for wait-time metrics.</summary>
    public DateTimeOffset? ArrivedAt { get; private set; }

    private Appointment() { }

    public static Appointment CreateWalkIn(
        Guid patientId,
        string patientFullName,
        string providerName,
        DateTimeOffset appointmentTime,
        int durationMinutes = 30,
        string? notes = null,
        Guid? slotId = null)
        => new()
        {
            Id = Guid.NewGuid(),
            PatientId = patientId,
            PatientFullName = patientFullName,
            ProviderName = providerName,
            AppointmentTime = appointmentTime,
            DurationMinutes = durationMinutes,
            IsWalkIn = true,
            SlotId = slotId,
            Status = "scheduled",
            Notes = notes?.Trim(),
            CreatedAt = DateTimeOffset.UtcNow
        };

    public void MarkArrived()
    {
        if (Status != "scheduled")
            throw new InvalidOperationException(
                $"Cannot check in an appointment with status '{Status}'. Only 'scheduled' appointments can be checked in.");

        Status = "arrived";
        ArrivedAt = DateTimeOffset.UtcNow;
    }

    /// <summary>
    /// Rescheduling preserves IsWalkIn flag and slotId to prevent accidental flag loss.
    /// </summary>
    public void Reschedule(DateTimeOffset newTime, int durationMinutes, string? notes)
    {
        AppointmentTime = newTime;
        DurationMinutes = durationMinutes;
        Notes = notes?.Trim();
        // IsWalkIn intentionally NOT modified — flag must survive reschedules.
    }

    /// <summary>
    /// Cancels a scheduled or arrived appointment and releases the associated slot.
    /// Throws if the appointment is already completed or cancelled.
    /// </summary>
    public void Cancel(string? reason = null)
    {
        if (Status is "completed" or "cancelled")
            throw new InvalidOperationException(
                $"Cannot cancel appointment with status '{Status}'.");

        Status = "cancelled";
        if (!string.IsNullOrWhiteSpace(reason))
            Notes = reason.Trim();
    }

    /// <summary>Creates a standard (non-walk-in) appointment with IsWalkIn = false.</summary>
    public static Appointment Create(
        Guid patientId,
        string patientFullName,
        string providerName,
        DateTimeOffset appointmentTime,
        int durationMinutes = 30,
        string? notes = null)
        => new()
        {
            Id = Guid.NewGuid(),
            PatientId = patientId,
            PatientFullName = patientFullName,
            ProviderName = providerName,
            AppointmentTime = appointmentTime,
            DurationMinutes = durationMinutes,
            IsWalkIn = false,
            Status = "scheduled",
            Notes = notes?.Trim(),
            CreatedAt = DateTimeOffset.UtcNow
        };
}

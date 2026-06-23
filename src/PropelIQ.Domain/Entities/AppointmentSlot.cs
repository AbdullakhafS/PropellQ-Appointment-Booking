namespace PropelIQ.Domain.Entities;

/// <summary>
/// Represents a schedulable appointment slot for a provider.
/// A slot is "available" when it has no booked appointment and is in the future.
/// </summary>
public sealed class AppointmentSlot
{
    public Guid Id { get; private set; }
    public string ProviderId { get; private set; } = string.Empty;
    public string ProviderName { get; private set; } = string.Empty;
    public string? ClinicId { get; private set; }
    public string? Location { get; private set; }
    public DateTimeOffset StartTime { get; private set; }
    public DateTimeOffset EndTime { get; private set; }
    public bool IsBooked { get; private set; }
    public Guid? BookedAppointmentId { get; private set; }
    private int _version;

    private AppointmentSlot() { }

    public static AppointmentSlot Create(
        string providerId,
        string providerName,
        DateTimeOffset startTime,
        DateTimeOffset endTime,
        string? clinicId = null,
        string? location = null)
        => new()
        {
            Id = Guid.NewGuid(),
            ProviderId = providerId,
            ProviderName = providerName,
            StartTime = startTime,
            EndTime = endTime,
            ClinicId = clinicId,
            Location = location,
            IsBooked = false,
        };

    public int DurationMinutes => (int)(EndTime - StartTime).TotalMinutes;

    /// <summary>
    /// Atomically claim this slot for an appointment.
    /// Returns false if the slot was already booked (conflict).
    /// </summary>
    public bool TryBook(Guid appointmentId, int expectedVersion)
    {
        if (IsBooked || _version != expectedVersion) return false;
        IsBooked = true;
        BookedAppointmentId = appointmentId;
        _version++;
        return true;
    }

    public int Version => _version;
}

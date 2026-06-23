namespace PropelIQ.Domain.Entities;

/// <summary>
/// Immutable audit record for every appointment status transition.
/// Enables SLA tracking, arrival-order analysis, and patient flow metrics.
/// </summary>
public sealed class AppointmentStatusHistory
{
    public Guid Id { get; private set; }
    public Guid AppointmentId { get; private set; }
    public string PreviousStatus { get; private set; } = string.Empty;
    public string NewStatus { get; private set; } = string.Empty;
    /// <summary>UTC timestamp when the transition occurred.</summary>
    public DateTimeOffset TransitionedAtUtc { get; private set; }
    public string? Notes { get; private set; }

    private AppointmentStatusHistory() { }

    public static AppointmentStatusHistory Record(
        Guid appointmentId,
        string previousStatus,
        string newStatus,
        string? notes = null)
        => new()
        {
            Id = Guid.NewGuid(),
            AppointmentId = appointmentId,
            PreviousStatus = previousStatus,
            NewStatus = newStatus,
            TransitionedAtUtc = DateTimeOffset.UtcNow,
            Notes = notes
        };
}

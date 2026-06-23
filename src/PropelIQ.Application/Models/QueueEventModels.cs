namespace PropelIQ.Application.Models;

// --- Real-time queue events ---

public enum QueueEventType
{
    Added,        // new appointment/walk-in appeared in queue
    Updated,      // status or scheduling changed
    Removed,      // appointment cancelled or completed, no longer in same-day queue
    Reordered,    // staff reordered the queue
}

/// <summary>
/// Minimal queue event payload broadcast to all connected staff SSE clients.
/// Keep fields lean to minimise per-event bandwidth under high concurrency.
/// </summary>
public sealed record QueueEvent(
    QueueEventType EventType,
    Guid AppointmentId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    DateTimeOffset AppointmentTime,
    int DurationMinutes,
    bool IsWalkIn,
    string Status,
    DateTimeOffset OccurredAt,
    DateTimeOffset? ArrivedAt = null
)
{
    public static QueueEvent From(QueueEventType type, QueueAppointmentRow row)
        => new(type, row.AppointmentId, row.PatientId, row.PatientFullName,
               row.ProviderName, row.AppointmentTime, row.DurationMinutes,
               row.IsWalkIn, row.Status, DateTimeOffset.UtcNow, row.ArrivedAt);
}

/// <summary>Broadcast when queue order changes — carries the new ordered list of IDs.</summary>
public sealed record QueueReorderEvent(
    IReadOnlyList<Guid> OrderedIds,
    int NewVersion,
    DateTimeOffset OccurredAt
);

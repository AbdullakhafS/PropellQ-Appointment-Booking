namespace PropelIQ.Application.Models;

// --- Queue / Schedule list ---

public sealed record QueueQuery(
    DateOnly? Date,
    string? Status,
    bool? IsWalkIn,
    string? ProviderId,
    int Page = 1,
    int PageSize = 50
);

public sealed record QueueAppointmentRow(
    Guid AppointmentId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    DateTimeOffset AppointmentTime,
    int DurationMinutes,
    bool IsWalkIn,
    Guid? SlotId,
    string Status,
    DateTimeOffset CreatedAt,
    int Position = 0,   // explicit queue position; 0 = default chronological order
    DateTimeOffset? ArrivedAt = null
);

public sealed record QueueResult(
    IReadOnlyList<QueueAppointmentRow> Items,
    int TotalCount,
    int Page,
    int PageSize,
    bool HasWalkIns,
    int Version = 0   // optimistic-concurrency version for reorder operations
);

// --- Reorder ---

public sealed record ReorderQueueRequest(
    IReadOnlyList<Guid> OrderedAppointmentIds,
    int ExpectedVersion
);

public sealed record ReorderQueueResult(
    IReadOnlyList<Guid> OrderedIds,
    int NewVersion
);

// --- Reschedule ---

public sealed record RescheduleRequest(
    Guid AppointmentId,
    DateTimeOffset NewTime,
    int DurationMinutes,
    string? Notes
);

// --- Check-in ---

public sealed record CheckInResult(
    Guid AppointmentId,
    string Status,
    DateTimeOffset ArrivedAt
);

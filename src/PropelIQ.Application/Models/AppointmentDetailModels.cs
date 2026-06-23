namespace PropelIQ.Application.Models;

// --- Appointment status history ---

public sealed record AppointmentHistoryEntry(
    Guid Id,
    Guid AppointmentId,
    string PreviousStatus,
    string NewStatus,
    DateTimeOffset TransitionedAtUtc,
    string? Notes
);

// --- Appointment detail (full metadata including arrival) ---

public sealed record AppointmentDetail(
    Guid AppointmentId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    DateTimeOffset AppointmentTime,
    int DurationMinutes,
    bool IsWalkIn,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset? ArrivedAt,
    IReadOnlyList<AppointmentHistoryEntry> StatusHistory
);

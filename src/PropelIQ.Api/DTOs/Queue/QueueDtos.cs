using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Queue;

// --- Queue list ---

public sealed record QueueAppointmentDto(
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
    int Position = 0,
    DateTimeOffset? ArrivedAt = null
);

public sealed record QueueResponseDto(
    IReadOnlyList<QueueAppointmentDto> Items,
    int TotalCount,
    int Page,
    int PageSize,
    bool HasWalkIns,
    int Version = 0
);

// --- Reschedule ---

public sealed record RescheduleRequestDto(
    [Required] DateTimeOffset NewTime,
    int DurationMinutes = 30,
    [MaxLength(500)] string? Notes = null
);

// --- Reorder ---

public sealed record ReorderQueueRequestDto(
    [Required] IReadOnlyList<Guid> OrderedAppointmentIds,
    [Required] int ExpectedVersion
);

public sealed record ReorderQueueResponseDto(
    IReadOnlyList<Guid> OrderedIds,
    int NewVersion
);

// --- Check-in ---

public sealed record CheckInResponseDto(
    Guid AppointmentId,
    string Status,
    DateTimeOffset ArrivedAt
);

// --- Cancel ---

public sealed record CancelAppointmentRequestDto(
    [MaxLength(500)] string? Reason = null
);

public sealed record CancelAppointmentResponseDto(
    Guid AppointmentId,
    string Status
);

// --- Common (re-export from WalkIn if not already available) ---

public sealed record ApiResponse<T>(bool Success, T? Data, string? Error = null)
{
    public static ApiResponse<T> Ok(T data) => new(true, data);
    public static ApiResponse<T> Fail(string error) => new(false, default, error);
}

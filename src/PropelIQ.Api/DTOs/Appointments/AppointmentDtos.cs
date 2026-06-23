namespace PropelIQ.Api.DTOs.Appointments;

public sealed record AppointmentHistoryEntryDto(
    Guid Id,
    string PreviousStatus,
    string NewStatus,
    DateTimeOffset TransitionedAtUtc,
    string? Notes
);

public sealed record AppointmentDetailDto(
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
    IReadOnlyList<AppointmentHistoryEntryDto> StatusHistory
);

public sealed record ApiResponse<T>(bool Success, T? Data, string? Error = null)
{
    public static ApiResponse<T> Ok(T data) => new(true, data);
    public static ApiResponse<T> Fail(string error) => new(false, default, error);
}

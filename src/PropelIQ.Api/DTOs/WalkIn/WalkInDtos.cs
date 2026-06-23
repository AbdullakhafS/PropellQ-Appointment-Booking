using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.WalkIn;

// --- Patient search ---

public sealed record PatientSearchResponseDto(
    Guid Id,
    string FirstName,
    string LastName,
    string FullName,
    string DateOfBirth,
    string Phone,
    string? Email,
    string Gender
);

// --- Patient create ---

public sealed record CreatePatientRequestDto(
    [Required, MaxLength(100)] string FirstName,
    [Required, MaxLength(100)] string LastName,
    [Required] DateOnly DateOfBirth,
    [Required, MaxLength(30)] string Phone,
    [Required, MaxLength(20)] string Gender,
    [MaxLength(200), EmailAddress] string? Email,
    [MaxLength(300)] string? Address,
    [MaxLength(500)] string? Notes
);

// --- Walk-in booking ---

public sealed record BookWalkInRequestDto(
    [Required] Guid PatientId,
    [Required, MaxLength(200)] string ProviderName,
    [Required] DateTimeOffset AppointmentTime,
    int DurationMinutes = 30,
    [MaxLength(500)] string? Notes = null,
    Guid? SlotId = null,
    int? SlotVersion = null
);

public sealed record BookWalkInResponseDto(
    Guid AppointmentId,
    Guid PatientId,
    string PatientFullName,
    string ProviderName,
    DateTimeOffset AppointmentTime,
    int DurationMinutes,
    bool IsWalkIn,
    string Status,
    DateTimeOffset CreatedAt,
    Guid? SlotId = null
);

// --- Slot availability ---

public sealed record AvailableSlotDto(
    Guid SlotId,
    int Version,
    string ProviderId,
    string ProviderName,
    DateTimeOffset StartTime,
    DateTimeOffset EndTime,
    int DurationMinutes,
    string? Location
);

public sealed record SlotCheckRequestDto(int ExpectedVersion);

public sealed record SlotCheckResponseDto(
    Guid SlotId,
    int Version,
    string ProviderName,
    DateTimeOffset StartTime,
    DateTimeOffset EndTime,
    bool IsAvailable
);

// --- Common ---

public sealed record ApiResponse<T>(bool Success, T? Data, string? Error = null)
{
    public static ApiResponse<T> Ok(T data) => new(true, data);
    public static ApiResponse<T> Fail(string error) => new(false, default, error);
}

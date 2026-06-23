namespace PropelIQ.Application.Models;

// --- Patient search ---

public sealed record PatientSearchQuery(string Term, int MaxResults = 20);

public sealed record PatientSummary(
    Guid Id,
    string FirstName,
    string LastName,
    DateOnly DateOfBirth,
    string Phone,
    string? Email,
    string Gender
)
{
    public string FullName => $"{FirstName} {LastName}";
}

// --- Patient create ---

public sealed record CreatePatientRequest(
    string FirstName,
    string LastName,
    DateOnly DateOfBirth,
    string Phone,
    string Gender,
    string? Email,
    string? Address,
    string? Notes
);

// --- Walk-in booking ---

public sealed record BookWalkInRequest(
    Guid PatientId,
    string ProviderName,
    DateTimeOffset AppointmentTime,
    int DurationMinutes,
    string? Notes,
    Guid? SlotId = null,
    int? SlotVersion = null
);

public sealed record BookWalkInResult(
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

public sealed record SlotAvailabilityQuery(
    string? ProviderId,
    string? ClinicId,
    DateTimeOffset WindowStart,
    DateTimeOffset WindowEnd
);

public sealed record AvailableSlot(
    Guid SlotId,
    int Version,
    string ProviderId,
    string ProviderName,
    DateTimeOffset StartTime,
    DateTimeOffset EndTime,
    int DurationMinutes,
    string? Location
);

public sealed record AssignSlotRequest(
    Guid SlotId,
    int SlotVersion,
    Guid AppointmentId
);

public enum SlotAssignmentResult { Success, Conflict, NotFound }

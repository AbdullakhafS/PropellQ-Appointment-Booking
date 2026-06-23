using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;

namespace PropelIQ.Infrastructure.WalkIn;

/// <summary>
/// In-memory implementation of the walk-in booking service.
/// Replace the in-memory stores with EF Core DbContext when the data layer is wired up.
/// </summary>
public sealed class WalkInBookingService : IWalkInBookingService
{
    // Temporary in-memory stores — replace with EF Core repositories.
    // 'Appointments' is internal so QueueService can share the same list.
    internal static readonly List<Patient> _patients = [];
    internal static readonly List<Appointment> _appointments = [];
    internal static List<Appointment> Appointments => _appointments;

    private readonly IQueueEventBroadcaster _broadcaster;

    public WalkInBookingService(IQueueEventBroadcaster broadcaster)
        => _broadcaster = broadcaster;

    public Task<IReadOnlyList<PatientSummary>> SearchPatientsAsync(
        PatientSearchQuery query, CancellationToken ct = default)
    {
        var term = query.Term.Trim().ToLowerInvariant();

        var matches = _patients
            .Where(p =>
                p.FullName.Contains(term, StringComparison.OrdinalIgnoreCase) ||
                p.Phone.Contains(term, StringComparison.OrdinalIgnoreCase) ||
                (p.Email != null && p.Email.Contains(term, StringComparison.OrdinalIgnoreCase)) ||
                p.Id.ToString().Contains(term, StringComparison.OrdinalIgnoreCase))
            .Take(query.MaxResults)
            .Select(MapToSummary)
            .ToList();

        return Task.FromResult<IReadOnlyList<PatientSummary>>(matches);
    }

    public Task<PatientSummary> CreatePatientAsync(
        CreatePatientRequest request, CancellationToken ct = default)
    {
        var patient = Patient.Create(
            request.FirstName,
            request.LastName,
            request.DateOfBirth,
            request.Phone,
            request.Gender,
            request.Email,
            request.Address,
            request.Notes);

        _patients.Add(patient);
        return Task.FromResult(MapToSummary(patient));
    }

    public Task<BookWalkInResult> BookWalkInAsync(
        BookWalkInRequest request, CancellationToken ct = default)
    {
        var patient = _patients.FirstOrDefault(p => p.Id == request.PatientId)
            ?? throw new InvalidOperationException($"Patient {request.PatientId} not found.");

        var appointment = Appointment.CreateWalkIn(
            patient.Id,
            patient.FullName,
            request.ProviderName,
            request.AppointmentTime,
            request.DurationMinutes,
            request.Notes,
            request.SlotId);

        _appointments.Add(appointment);

        var result = new BookWalkInResult(
            appointment.Id,
            appointment.PatientId,
            appointment.PatientFullName,
            appointment.ProviderName,
            appointment.AppointmentTime,
            appointment.DurationMinutes,
            appointment.IsWalkIn,
            appointment.Status,
            appointment.CreatedAt,
            appointment.SlotId);

        // Publish real-time event to all connected SSE clients (task_034_002)
        _broadcaster.Publish(QueueEvent.From(QueueEventType.Added, new QueueAppointmentRow(
            result.AppointmentId, result.PatientId, result.PatientFullName,
            result.ProviderName, result.AppointmentTime, result.DurationMinutes,
            result.IsWalkIn, result.SlotId, result.Status, result.CreatedAt)));

        return Task.FromResult(result);
    }

    private static PatientSummary MapToSummary(Patient p)
        => new(p.Id, p.FirstName, p.LastName, p.DateOfBirth, p.Phone, p.Email, p.Gender);
}

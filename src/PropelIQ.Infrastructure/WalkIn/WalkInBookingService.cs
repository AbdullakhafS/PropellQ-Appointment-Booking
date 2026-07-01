using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace PropelIQ.Infrastructure.WalkIn;

/// <summary>
/// In-memory implementation of the walk-in booking service.
/// Replace the in-memory stores with EF Core DbContext when the data layer is wired up.
/// </summary>
public sealed class WalkInBookingService : IWalkInBookingService
{
    private static readonly object _sync = new();
    private static bool _isHydrated;

    // Temporary in-memory stores — replace with EF Core repositories.
    // 'Appointments' is internal so QueueService can share the same list.
    internal static readonly List<Patient> _patients = [];
    internal static readonly List<Appointment> _appointments = [];
    internal static List<Appointment> Appointments => _appointments;

    internal static void ResetStateForTests()
    {
        lock (_sync)
        {
            _patients.Clear();
            _appointments.Clear();
            _isHydrated = false;
        }
    }

    private readonly IQueueEventBroadcaster _broadcaster;
    private readonly AppDbContext _db;

    public WalkInBookingService(IQueueEventBroadcaster broadcaster, AppDbContext db)
    {
        _broadcaster = broadcaster;
        _db = db;
    }

    internal static void EnsureLoaded(AppDbContext db)
    {
        lock (_sync)
        {
            if (_isHydrated)
            {
                return;
            }
        }

        var patients = db.Set<Patient>().AsNoTracking().ToList();
        var appointments = db.Set<Appointment>().AsNoTracking().ToList();

        lock (_sync)
        {
            if (_isHydrated)
            {
                return;
            }

            _patients.Clear();
            _patients.AddRange(patients);
            _appointments.Clear();
            _appointments.AddRange(appointments);
            _isHydrated = true;
        }
    }

    internal static async Task EnsureLoadedAsync(AppDbContext db, CancellationToken ct = default)
    {
        lock (_sync)
        {
            if (_isHydrated)
            {
                return;
            }
        }

        var patients = await db.Set<Patient>().AsNoTracking().ToListAsync(ct);
        var appointments = await db.Set<Appointment>().AsNoTracking().ToListAsync(ct);

        lock (_sync)
        {
            if (_isHydrated)
            {
                return;
            }

            _patients.Clear();
            _patients.AddRange(patients);
            _appointments.Clear();
            _appointments.AddRange(appointments);
            _isHydrated = true;
        }
    }

    public Task<IReadOnlyList<PatientSummary>> SearchPatientsAsync(
        PatientSearchQuery query, CancellationToken ct = default)
    {
        EnsureLoaded(_db);

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

    public async Task<PatientSummary> CreatePatientAsync(
        CreatePatientRequest request, CancellationToken ct = default)
    {
        await EnsureLoadedAsync(_db, ct);

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
        _db.Set<Patient>().Add(patient);
        await _db.SaveChangesAsync(ct);

        return MapToSummary(patient);
    }

    public async Task<BookWalkInResult> BookWalkInAsync(
        BookWalkInRequest request, CancellationToken ct = default)
    {
        await EnsureLoadedAsync(_db, ct);

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
        _db.Set<Appointment>().Add(appointment);
        await _db.SaveChangesAsync(ct);

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

        return result;
    }

    private static PatientSummary MapToSummary(Patient p)
        => new(p.Id, p.FirstName, p.LastName, p.DateOfBirth, p.Phone, p.Email, p.Gender);
}

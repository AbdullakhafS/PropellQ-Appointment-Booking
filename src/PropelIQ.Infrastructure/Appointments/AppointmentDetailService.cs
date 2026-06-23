using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.WalkIn;

namespace PropelIQ.Infrastructure.Appointments;

/// <summary>
/// In-memory appointment detail and status-history service.
/// Singleton so the history log persists across request scopes.
/// Replace with EF Core when the data layer is wired up.
/// </summary>
public sealed class AppointmentDetailService : IAppointmentDetailService
{
    private static readonly List<AppointmentStatusHistory> _history = [];
    private static readonly object _lock = new();

    public AppointmentDetail? GetDetail(Guid appointmentId)
    {
        var appt = WalkInBookingService.Appointments.FirstOrDefault(a => a.Id == appointmentId);
        if (appt is null) return null;

        return new AppointmentDetail(
            appt.Id,
            appt.PatientId,
            appt.PatientFullName,
            appt.ProviderName,
            appt.AppointmentTime,
            appt.DurationMinutes,
            appt.IsWalkIn,
            appt.Status,
            appt.CreatedAt,
            appt.ArrivedAt,
            GetHistory(appointmentId));
    }

    public IReadOnlyList<AppointmentHistoryEntry> GetHistory(Guid appointmentId)
    {
        lock (_lock)
        {
            return _history
                .Where(h => h.AppointmentId == appointmentId)
                .OrderBy(h => h.TransitionedAtUtc)
                .Select(h => new AppointmentHistoryEntry(
                    h.Id, h.AppointmentId, h.PreviousStatus, h.NewStatus,
                    h.TransitionedAtUtc, h.Notes))
                .ToList();
        }
    }

    public void RecordTransition(Guid appointmentId, string previousStatus, string newStatus, string? notes = null)
    {
        lock (_lock)
        {
            _history.Add(AppointmentStatusHistory.Record(appointmentId, previousStatus, newStatus, notes));
        }
    }
}

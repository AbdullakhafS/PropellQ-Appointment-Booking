using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.WalkIn;

namespace PropelIQ.Infrastructure.Queue;

/// <summary>
/// In-memory queue/schedule service.
/// Shares the same static _appointments store as WalkInBookingService.
/// Replace both with an EF Core repository when persisting.
/// </summary>
public sealed class QueueService : IQueueService
{
    private readonly IQueueEventBroadcaster _broadcaster;
    private readonly IAppointmentDetailService _history;
    private readonly IAutoOfferOrchestrator _autoOffer;
    private readonly INotificationService _notifications;

    public QueueService(
        IQueueEventBroadcaster broadcaster,
        IAppointmentDetailService history,
        IAutoOfferOrchestrator autoOffer,
        INotificationService notifications)
    {
        _broadcaster = broadcaster;
        _history = history;
        _autoOffer = autoOffer;
        _notifications = notifications;
        SeedAppointments();
    }

    // Shared position store: maps AppointmentId -> explicit queue position (0 = unset)
    private static readonly Dictionary<Guid, int> _positions = new();
    private static int _queueVersion = 0;
    private static readonly object _reorderLock = new();

    public Task<QueueResult> GetQueueAsync(QueueQuery query, CancellationToken ct = default)
    {
        var all = WalkInBookingService.Appointments;

        var filtered = all.AsEnumerable();

        if (query.Date.HasValue)
        {
            var d = query.Date.Value;
            filtered = filtered.Where(a =>
                a.AppointmentTime.Date == new DateTime(d.Year, d.Month, d.Day));
        }

        if (!string.IsNullOrWhiteSpace(query.Status))
            filtered = filtered.Where(a => a.Status == query.Status);

        if (query.IsWalkIn.HasValue)
            filtered = filtered.Where(a => a.IsWalkIn == query.IsWalkIn.Value);

        if (!string.IsNullOrWhiteSpace(query.ProviderId))
            filtered = filtered.Where(a =>
                a.ProviderName.Contains(query.ProviderId, StringComparison.OrdinalIgnoreCase));

        int version;
        List<QueueAppointmentRow> page;
        int total;
        bool hasWalkIns;

        lock (_reorderLock)
        {
            version = _queueVersion;
            var all2 = WalkInBookingService.Appointments;
            hasWalkIns = all2.Any(a => a.IsWalkIn);

            // Sort by explicit position first; fall back to chronological
            var ordered = filtered
                .OrderBy(a => _positions.TryGetValue(a.Id, out var pos) ? pos : int.MaxValue)
                .ThenBy(a => a.AppointmentTime)
                .ToList();

            total = ordered.Count;

            page = ordered
                .Skip((query.Page - 1) * query.PageSize)
                .Take(query.PageSize)
                .Select((a, idx) => MapRowWithPosition(a, _positions.TryGetValue(a.Id, out var p) ? p : idx))
                .ToList();
        }

        return Task.FromResult(new QueueResult(page, total, query.Page, query.PageSize, hasWalkIns, version));
    }

    public Task<QueueAppointmentRow> RescheduleAsync(RescheduleRequest request, CancellationToken ct = default)
    {
        var appt = WalkInBookingService.Appointments.FirstOrDefault(a => a.Id == request.AppointmentId)
            ?? throw new InvalidOperationException($"Appointment {request.AppointmentId} not found.");

        // Slot conflict check (task_041_002): same provider must not have another active
        // appointment overlapping the requested new time window.
        var newEnd = request.NewTime.AddMinutes(request.DurationMinutes);
        var conflict = WalkInBookingService.Appointments.FirstOrDefault(a =>
            a.Id != request.AppointmentId &&
            a.ProviderName.Equals(appt.ProviderName, StringComparison.OrdinalIgnoreCase) &&
            a.Status is "scheduled" or "arrived" &&
            a.AppointmentTime < newEnd &&
            a.AppointmentTime.AddMinutes(a.DurationMinutes) > request.NewTime);

        if (conflict is not null)
            throw new InvalidOperationException(
                $"Reschedule conflict: provider {appt.ProviderName} already has appointment " +
                $"{conflict.Id} at {conflict.AppointmentTime:HH:mm} that overlaps the requested time.");

        // Capture released slot context before overwriting the appointment time
        var releasedSlotId = appt.SlotId;
        var releasedProviderName = appt.ProviderName;
        var releasedTime = appt.AppointmentTime;
        var patientFullName = appt.PatientFullName;

        appt.Reschedule(request.NewTime, request.DurationMinutes, request.Notes);
        var row = MapRow(appt);

        // Publish real-time update event (task_034_002 / task_041_003)
        _broadcaster.Publish(QueueEvent.From(QueueEventType.Updated, row));

        // Notification to patient and provider (task_041_005)
        _ = _notifications.NotifyRescheduleAsync(
            new AppointmentChangeNotification(
                appt.Id, patientFullName, releasedProviderName,
                AppointmentChangeType.Rescheduled,
                OldAppointmentTime: releasedTime,
                NewAppointmentTime: request.NewTime,
                Reason: request.Notes),
            ct);

        // Auto-offer pipeline: the old slot is now free (task_040_001 / task_041_004)
        _ = _autoOffer.TriggerForReleasedSlotAsync(
            new SlotReleasedEvent(
                releasedProviderName,
                releasedSlotId,
                releasedProviderName,
                releasedTime,
                "rescheduled"),
            ct);

        return Task.FromResult(row);
    }

    public Task<ReorderQueueResult> ReorderQueueAsync(ReorderQueueRequest request, CancellationToken ct = default)
    {
        lock (_reorderLock)
        {
            // Optimistic-concurrency check (task_035_003)
            if (request.ExpectedVersion != _queueVersion)
                throw new InvalidOperationException(
                    $"Queue version conflict. Expected {request.ExpectedVersion}, current is {_queueVersion}.");

            // Persist new positions
            _positions.Clear();
            for (int i = 0; i < request.OrderedAppointmentIds.Count; i++)
                _positions[request.OrderedAppointmentIds[i]] = i;

            _queueVersion++;
        }

        var result = new ReorderQueueResult(request.OrderedAppointmentIds, _queueVersion);

        // Broadcast reorder to all SSE subscribers (task_035_004)
        _broadcaster.PublishReorder(new QueueReorderEvent(
            result.OrderedIds, result.NewVersion, DateTimeOffset.UtcNow));

        return Task.FromResult(result);
    }

    public Task<CheckInResult> CheckInAsync(Guid appointmentId, CancellationToken ct = default)
    {
        var appt = WalkInBookingService.Appointments.FirstOrDefault(a => a.Id == appointmentId)
            ?? throw new InvalidOperationException($"Appointment {appointmentId} not found.");

        var previousStatus = appt.Status;
        appt.MarkArrived(); // throws if already arrived/completed/cancelled

        // Record status-transition history (task_038_002 atomicity: history written after successful transition)
        _history.RecordTransition(appointmentId, previousStatus, appt.Status);

        var row = MapRow(appt);

        // Broadcast check-in update to all SSE subscribers (task_037_004)
        _broadcaster.Publish(QueueEvent.From(QueueEventType.Updated, row));

        return Task.FromResult(new CheckInResult(appt.Id, appt.Status, appt.ArrivedAt!.Value));
    }

    public Task<CancelAppointmentResult> CancelAsync(
        Guid appointmentId, string? reason, CancellationToken ct = default)
    {
        var appt = WalkInBookingService.Appointments.FirstOrDefault(a => a.Id == appointmentId)
            ?? throw new InvalidOperationException($"Appointment {appointmentId} not found.");

        var previousStatus = appt.Status;
        appt.Cancel(reason); // throws for completed / already-cancelled

        // Record status-transition audit entry (task_038_002 pattern)
        _history.RecordTransition(appointmentId, previousStatus, appt.Status);

        var row = MapRow(appt);

        // Broadcast SSE update so live queue views reflect the cancellation immediately (task_041_003)
        _broadcaster.Publish(QueueEvent.From(QueueEventType.Removed, row));

        // Notification to patient and provider (task_041_005)
        _ = _notifications.NotifyCancellationAsync(
            new AppointmentChangeNotification(
                appt.Id, appt.PatientFullName, appt.ProviderName,
                AppointmentChangeType.Cancelled,
                OldAppointmentTime: appt.AppointmentTime,
                NewAppointmentTime: null,
                Reason: reason),
            ct);

        // Auto-offer pipeline: notify the first eligible waitlisted patient (task_040_001 / task_041_004)
        _ = _autoOffer.TriggerForReleasedSlotAsync(
            new SlotReleasedEvent(
                appt.ProviderName,   // use ProviderName as ProviderId key for waitlist matching
                appt.SlotId,
                appt.ProviderName,
                appt.AppointmentTime,
                "cancelled"),
            ct);

        return Task.FromResult(new CancelAppointmentResult(appt.Id, appt.Status));
    }

    private static QueueAppointmentRow MapRowWithPosition(Appointment a, int position)
        => new(a.Id, a.PatientId, a.PatientFullName, a.ProviderName,
               a.AppointmentTime, a.DurationMinutes, a.IsWalkIn, a.SlotId,
               a.Status, a.CreatedAt, position, a.ArrivedAt);

    private static QueueAppointmentRow MapRow(Appointment a)
        => MapRowWithPosition(a, 0);

    private static bool _seeded;
    private static readonly object _seedLock = new();

    private static void SeedAppointments()
    {
        lock (_seedLock)
        {
            if (_seeded) return;
            _seeded = true;

            // Seed a mix of walk-in and pre-booked appointments for demo purposes.
            var patients = new[]
            {
                (Guid.NewGuid(), "Alice Johnson"),
                (Guid.NewGuid(), "Bob Martinez"),
                (Guid.NewGuid(), "Carol White"),
            };

            var today = DateTimeOffset.UtcNow.Date;

            foreach (var (i, (pid, name)) in patients.Select((v, i) => (i, v)))
            {
                var apptTime = new DateTimeOffset(today.Year, today.Month, today.Day, 9 + i, 0, 0, TimeSpan.Zero);
                var isWalkIn = i % 2 == 0;

                var appt = isWalkIn
                    ? Appointment.CreateWalkIn(pid, name, $"Dr. Provider-{i + 1}", apptTime)
                    : Appointment.Create(pid, name, $"Dr. Provider-{i + 1}", apptTime);

                WalkInBookingService.Appointments.Add(appt);
            }
        }
    }
}

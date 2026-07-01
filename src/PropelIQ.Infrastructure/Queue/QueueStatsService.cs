using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Infrastructure.Data;
using PropelIQ.Infrastructure.WalkIn;

namespace PropelIQ.Infrastructure.Queue;

/// <summary>
/// Computes queue statistics synchronously from the shared in-memory appointment store.
/// Scoped per request; fast enough to call on every stats request.
/// </summary>
public sealed class QueueStatsService : IQueueStatsService
{
    private readonly AppDbContext _db;

    public QueueStatsService(AppDbContext db)
    {
        _db = db;
    }

    public QueueStats ComputeStats()
    {
        WalkInBookingService.EnsureLoaded(_db);

        var now = DateTimeOffset.UtcNow;
        var all = WalkInBookingService.Appointments;

        // Active = not completed or cancelled (i.e. scheduled or arrived)
        var active = all
            .Where(a => a.Status is "scheduled" or "arrived")
            .ToList();

        if (active.Count == 0)
        {
            return new QueueStats(
                ActivePatientCount: 0,
                WalkInCount: 0,
                ArrivedCount: 0,
                AverageWaitMinutes: 0,
                MaxWaitMinutes: 0,
                WaitHealth: WaitTimeHealth.Normal,
                ComputedAt: now);
        }

        int arrivedCount = active.Count(a => a.Status == "arrived");
        int walkInCount = active.Count(a => a.IsWalkIn);

        // Wait time = minutes from AppointmentTime to now (or ArrivedAt if checked in).
        // Patients who arrived but are waiting are measured from ArrivedAt.
        // Patients not yet arrived are measured from their scheduled time (can be negative for future appts).
        var waitMinutes = active.Select(a =>
        {
            var start = a.ArrivedAt ?? a.AppointmentTime;
            return Math.Max(0, (now - start).TotalMinutes);
        }).ToList();

        double avg = waitMinutes.Average();
        double max = waitMinutes.Max();

        var health = avg >= QueueStatThresholds.WaitCriticalMinutes
            ? WaitTimeHealth.Critical
            : avg >= QueueStatThresholds.WaitWarningMinutes
                ? WaitTimeHealth.Warning
                : WaitTimeHealth.Normal;

        return new QueueStats(
            ActivePatientCount: active.Count,
            WalkInCount: walkInCount,
            ArrivedCount: arrivedCount,
            AverageWaitMinutes: Math.Round(avg, 1),
            MaxWaitMinutes: Math.Round(max, 1),
            WaitHealth: health,
            ComputedAt: now);
    }
}

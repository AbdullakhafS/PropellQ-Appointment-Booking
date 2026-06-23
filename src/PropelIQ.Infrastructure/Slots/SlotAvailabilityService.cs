using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;

namespace PropelIQ.Infrastructure.Slots;

/// <summary>
/// In-memory slot availability and assignment service with optimistic-concurrency conflict detection.
/// Replace with EF Core persistence when the data layer is wired up.
/// </summary>
public sealed class SlotAvailabilityService : ISlotAvailabilityService
{
    // Shared in-process store; lock guards concurrent slot assignment.
    private static readonly List<AppointmentSlot> _slots = [];
    private static readonly object _lock = new();

    // Seed a realistic provider schedule on first access.
    static SlotAvailabilityService() => SeedSlots();

    public Task<IReadOnlyList<AvailableSlot>> GetAvailableSlotsAsync(
        SlotAvailabilityQuery query, CancellationToken ct = default)
    {
        var now = DateTimeOffset.UtcNow;

        IReadOnlyList<AvailableSlot> results;
        lock (_lock)
        {
            results = _slots
                .Where(s =>
                    !s.IsBooked &&
                    s.StartTime >= query.WindowStart &&
                    s.EndTime <= query.WindowEnd &&
                    s.StartTime > now &&
                    (query.ProviderId == null || s.ProviderId == query.ProviderId) &&
                    (query.ClinicId == null || s.ClinicId == query.ClinicId))
                .OrderBy(s => s.StartTime)
                .Select(s => new AvailableSlot(
                    s.Id, s.Version, s.ProviderId, s.ProviderName,
                    s.StartTime, s.EndTime, s.DurationMinutes, s.Location))
                .ToList();
        }

        return Task.FromResult(results);
    }

    public Task<SlotAssignmentResult> AssignSlotAsync(
        AssignSlotRequest request, CancellationToken ct = default)
    {
        lock (_lock)
        {
            var slot = _slots.FirstOrDefault(s => s.Id == request.SlotId);
            if (slot is null) return Task.FromResult(SlotAssignmentResult.NotFound);

            return Task.FromResult(
                slot.TryBook(request.AppointmentId, request.SlotVersion)
                    ? SlotAssignmentResult.Success
                    : SlotAssignmentResult.Conflict);
        }
    }

    private static void SeedSlots()
    {
        var providers = new[]
        {
            ("provider-001", "Dr. Adams", "clinic-a", "Suite 100"),
            ("provider-002", "Dr. Patel",  "clinic-a", "Suite 102"),
            ("provider-003", "Dr. Chen",   "clinic-b", "Suite 200"),
        };

        var today = DateTimeOffset.UtcNow.Date;

        foreach (var (pid, pname, cid, loc) in providers)
        {
            // Generate 30-minute slots from 08:00 – 17:00 for today and tomorrow.
            for (int dayOffset = 0; dayOffset <= 1; dayOffset++)
            {
                var date = today.AddDays(dayOffset);
                for (int hour = 8; hour < 17; hour++)
                {
                    for (int min = 0; min < 60; min += 30)
                    {
                        var start = new DateTimeOffset(date.Year, date.Month, date.Day, hour, min, 0, TimeSpan.Zero);
                        _slots.Add(AppointmentSlot.Create(pid, pname, start, start.AddMinutes(30), cid, loc));
                    }
                }
            }
        }
    }
}

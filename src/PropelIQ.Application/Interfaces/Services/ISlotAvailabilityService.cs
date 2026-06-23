using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface ISlotAvailabilityService
{
    /// <summary>Returns open, future appointment slots for the given provider/clinic window.</summary>
    Task<IReadOnlyList<AvailableSlot>> GetAvailableSlotsAsync(SlotAvailabilityQuery query, CancellationToken ct = default);

    /// <summary>
    /// Atomically claims a slot for an appointment.
    /// Uses optimistic concurrency (version check) to prevent double-booking.
    /// </summary>
    Task<SlotAssignmentResult> AssignSlotAsync(AssignSlotRequest request, CancellationToken ct = default);
}

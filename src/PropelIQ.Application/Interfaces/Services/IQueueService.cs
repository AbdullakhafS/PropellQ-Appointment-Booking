using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IQueueService
{
    /// <summary>Returns the appointment queue with optional walk-in filter.</summary>
    Task<QueueResult> GetQueueAsync(QueueQuery query, CancellationToken ct = default);

    /// <summary>
    /// Reschedules an appointment, preserving the IsWalkIn flag.
    /// Throws InvalidOperationException if not found.
    /// </summary>
    Task<QueueAppointmentRow> RescheduleAsync(RescheduleRequest request, CancellationToken ct = default);

    /// <summary>
    /// Saves a new queue position order with optimistic concurrency check.
    /// Returns the new version number on success.
    /// Throws InvalidOperationException if the expected version does not match (conflict).
    /// </summary>
    Task<ReorderQueueResult> ReorderQueueAsync(ReorderQueueRequest request, CancellationToken ct = default);

    /// <summary>
    /// Marks a scheduled appointment as arrived (checked in) and records the arrival timestamp.
    /// Throws InvalidOperationException if the appointment is not found or not in Scheduled status.
    /// </summary>
    Task<CheckInResult> CheckInAsync(Guid appointmentId, CancellationToken ct = default);

    /// <summary>
    /// Cancels a scheduled or arrived appointment, releases the slot, and triggers the
    /// auto-offer pipeline so the first eligible waitlisted patient is notified.
    /// Throws InvalidOperationException if the appointment is not found, completed, or already cancelled.
    /// </summary>
    Task<CancelAppointmentResult> CancelAsync(Guid appointmentId, string? reason, CancellationToken ct = default);
}

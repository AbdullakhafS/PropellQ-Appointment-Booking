using Microsoft.AspNetCore.Mvc;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

/// <summary>
/// Exposes the notification delivery audit log for observability.
/// Supports US-041 (task_041_005): delivery outcome tracking.
/// </summary>
[ApiController]
[Route("api/notifications")]
[Produces("application/json")]
public sealed class NotificationsController : ControllerBase
{
    private readonly INotificationService _notifications;

    public NotificationsController(INotificationService notifications)
        => _notifications = notifications;

    /// <summary>
    /// Returns all notification delivery records, most recent first.
    /// Use appointmentId to filter to a single appointment.
    /// </summary>
    /// <response code="200">Delivery log entries.</response>
    [HttpGet]
    [ProducesResponseType(typeof(NotificationLogResponseDto), StatusCodes.Status200OK)]
    public IActionResult GetLog([FromQuery] Guid? appointmentId = null)
    {
        var records = appointmentId.HasValue
            ? _notifications.GetDeliveryLog(appointmentId.Value)
            : _notifications.GetAllDeliveryLogs();

        var dtos = records.Select(r => new NotificationDeliveryDto(
            r.Id, r.AppointmentId, r.RecipientType, r.RecipientName,
            r.ChangeType.ToString(), r.Delivered, r.FailureReason, r.DispatchedAt))
            .ToList();

        return Ok(new NotificationLogResponseDto(dtos, dtos.Count));
    }
}

// --- DTOs -----------------------------------------------------------------------

public sealed record NotificationDeliveryDto(
    Guid Id,
    Guid AppointmentId,
    string RecipientType,
    string RecipientName,
    string ChangeType,
    bool Delivered,
    string? FailureReason,
    DateTimeOffset DispatchedAt
);

public sealed record NotificationLogResponseDto(
    IReadOnlyList<NotificationDeliveryDto> Records,
    int TotalCount
);

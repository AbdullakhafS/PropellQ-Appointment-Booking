using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Appointments;
using PropelIQ.Application.Interfaces.Services;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/appointments")]
[Produces("application/json")]
public sealed class AppointmentController : ControllerBase
{
    private readonly IAppointmentDetailService _detail;
    private readonly ILogger<AppointmentController> _logger;

    public AppointmentController(IAppointmentDetailService detail, ILogger<AppointmentController> logger)
    {
        _detail = detail;
        _logger = logger;
    }

    /// <summary>
    /// Returns full appointment detail including arrival timestamp and complete status history.
    /// </summary>
    /// <response code="200">Appointment detail with arrival metadata.</response>
    /// <response code="404">Appointment not found.</response>
    [HttpGet("{appointmentId:guid}")]
    [ProducesResponseType(typeof(ApiResponse<AppointmentDetailDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public IActionResult GetDetail(Guid appointmentId)
    {
        var detail = _detail.GetDetail(appointmentId);
        if (detail is null)
        {
            _logger.LogWarning("Appointment {Id} not found for detail lookup", appointmentId);
            return NotFound(ApiResponse<object>.Fail($"Appointment {appointmentId} not found."));
        }

        return Ok(ApiResponse<AppointmentDetailDto>.Ok(new AppointmentDetailDto(
            detail.AppointmentId,
            detail.PatientId,
            detail.PatientFullName,
            detail.ProviderName,
            detail.AppointmentTime,
            detail.DurationMinutes,
            detail.IsWalkIn,
            detail.Status,
            detail.CreatedAt,
            detail.ArrivedAt,
            detail.StatusHistory.Select(h => new AppointmentHistoryEntryDto(
                h.Id, h.PreviousStatus, h.NewStatus, h.TransitionedAtUtc, h.Notes)).ToList())));
    }

    /// <summary>
    /// Returns the status-transition history for an appointment.
    /// Supports SLA tracking, arrival-order analysis, and patient flow metrics.
    /// </summary>
    /// <response code="200">Ordered list of status transitions (oldest first).</response>
    [HttpGet("{appointmentId:guid}/history")]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<AppointmentHistoryEntryDto>>), StatusCodes.Status200OK)]
    public IActionResult GetHistory(Guid appointmentId)
    {
        var history = _detail.GetHistory(appointmentId);
        return Ok(ApiResponse<IReadOnlyList<AppointmentHistoryEntryDto>>.Ok(
            history.Select(h => new AppointmentHistoryEntryDto(
                h.Id, h.PreviousStatus, h.NewStatus, h.TransitionedAtUtc, h.Notes)).ToList()));
    }
}

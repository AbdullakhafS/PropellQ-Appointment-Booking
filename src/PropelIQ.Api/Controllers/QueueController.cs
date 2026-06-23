using Microsoft.AspNetCore.Mvc;
using System.Text.Json;
using PropelIQ.Api.DTOs.Queue;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/queue")]
[Produces("application/json")]
public sealed class QueueController : ControllerBase
{
    private readonly IQueueService _queue;
    private readonly IQueueEventBroadcaster _broadcaster;
    private readonly IQueueStatsService _stats;
    private readonly ILogger<QueueController> _logger;

    public QueueController(
        IQueueService queue,
        IQueueEventBroadcaster broadcaster,
        IQueueStatsService stats,
        ILogger<QueueController> logger)
    {
        _queue = queue;
        _broadcaster = broadcaster;
        _stats = stats;
        _logger = logger;
    }

    /// <summary>
    /// Returns the appointment queue with optional walk-in filtering.
    /// Use isWalkIn=true to show only walk-ins, isWalkIn=false for pre-booked only.
    /// </summary>
    /// <response code="200">Paginated appointment queue.</response>
    [HttpGet]
    [ProducesResponseType(typeof(ApiResponse<QueueResponseDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetQueue(
        [FromQuery] DateOnly? date = null,
        [FromQuery] string? status = null,
        [FromQuery] bool? isWalkIn = null,
        [FromQuery] string? providerId = null,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50,
        CancellationToken ct = default)
    {
        var result = await _queue.GetQueueAsync(
            new QueueQuery(date, status, isWalkIn, providerId,
                           Math.Max(1, page), Math.Clamp(pageSize, 1, 200)),
            ct);

        return Ok(ApiResponse<QueueResponseDto>.Ok(
            new QueueResponseDto(
                result.Items.Select(MapDto).ToList(),
                result.TotalCount, result.Page, result.PageSize, result.HasWalkIns, result.Version)));
    }

    /// <summary>
    /// Returns current queue statistics: active patient count, walk-in count, average wait time, and health state.
    /// </summary>
    /// <response code="200">Queue statistics snapshot.</response>
    [HttpGet("stats")]
    [ProducesResponseType(typeof(ApiResponse<QueueStatsDto>), StatusCodes.Status200OK)]
    public IActionResult GetStats()
    {
        var s = _stats.ComputeStats();
        return Ok(ApiResponse<QueueStatsDto>.Ok(new QueueStatsDto(
            s.ActivePatientCount,
            s.WalkInCount,
            s.ArrivedCount,
            s.AverageWaitMinutes,
            s.MaxWaitMinutes,
            s.WaitHealth.ToString(),
            QueueStatThresholds.WaitWarningMinutes,
            QueueStatThresholds.WaitCriticalMinutes,
            s.ComputedAt)));
    }

    /// <summary>
    /// Reschedules an existing appointment, preserving the walk-in flag.
    /// The new time is validated for provider-level slot conflicts.
    /// </summary>
    /// <response code="200">Updated appointment row.</response>
    /// <response code="404">Appointment not found.</response>
    /// <response code="409">New time conflicts with an existing appointment for the same provider.</response>
    [HttpPatch("{appointmentId:guid}/reschedule")]
    [ProducesResponseType(typeof(ApiResponse<QueueAppointmentDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Reschedule(
        Guid appointmentId,
        [FromBody] RescheduleRequestDto request,
        CancellationToken ct)
    {
        try
        {
            var row = await _queue.RescheduleAsync(
                new RescheduleRequest(appointmentId, request.NewTime, request.DurationMinutes, request.Notes), ct);

            return Ok(ApiResponse<QueueAppointmentDto>.Ok(MapDto(row)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Reschedule failed for appointment {Id}: {Message}", appointmentId, ex.Message);
            if (ex.Message.Contains("not found", StringComparison.OrdinalIgnoreCase))
                return NotFound(ApiResponse<object>.Fail(ex.Message));
            return Conflict(ApiResponse<object>.Fail(ex.Message));
        }
    }

    /// <summary>
    /// Cancels a scheduled or arrived appointment and triggers the auto-offer pipeline
    /// to notify the first eligible waitlisted patient for the freed slot.
    /// </summary>
    /// <response code="200">Appointment cancelled; auto-offer pipeline triggered if waitlist has candidates.</response>
    /// <response code="404">Appointment not found.</response>
    /// <response code="409">Appointment is already completed or cancelled.</response>
    [HttpPatch("{appointmentId:guid}/cancel")]
    [ProducesResponseType(typeof(ApiResponse<CancelAppointmentResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> CancelAppointment(
        Guid appointmentId,
        [FromBody] CancelAppointmentRequestDto request,
        CancellationToken ct)
    {
        try
        {
            var result = await _queue.CancelAsync(appointmentId, request.Reason, ct);
            return Ok(ApiResponse<CancelAppointmentResponseDto>.Ok(
                new CancelAppointmentResponseDto(result.AppointmentId, result.Status)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Cancel failed for appointment {Id}: {Message}", appointmentId, ex.Message);
            if (ex.Message.Contains("not found", StringComparison.OrdinalIgnoreCase))
                return NotFound(ApiResponse<object>.Fail(ex.Message));
            return Conflict(ApiResponse<object>.Fail(ex.Message));
        }
    }

    private static QueueAppointmentDto MapDto(QueueAppointmentRow r)
        => new(r.AppointmentId, r.PatientId, r.PatientFullName, r.ProviderName,
               r.AppointmentTime, r.DurationMinutes, r.IsWalkIn, r.SlotId,
               r.Status, r.CreatedAt, r.Position, r.ArrivedAt);

    /// <summary>
    /// Marks a scheduled appointment as arrived (checked in) and records arrival timestamp.
    /// Only Scheduled appointments can be checked in.
    /// </summary>
    /// <response code="200">Patient checked in; returns status and arrival time.</response>
    /// <response code="404">Appointment not found.</response>
    /// <response code="409">Appointment is not in Scheduled status (invalid transition).</response>
    [HttpPatch("{appointmentId:guid}/check-in")]
    [ProducesResponseType(typeof(ApiResponse<CheckInResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> CheckIn(Guid appointmentId, CancellationToken ct)
    {
        try
        {
            var result = await _queue.CheckInAsync(appointmentId, ct);
            return Ok(ApiResponse<CheckInResponseDto>.Ok(
                new CheckInResponseDto(result.AppointmentId, result.Status, result.ArrivedAt)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Check-in failed for appointment {Id}: {Message}", appointmentId, ex.Message);
            // "not found" vs "invalid transition" — both map to 409/404 based on message content
            if (ex.Message.Contains("not found", StringComparison.OrdinalIgnoreCase))
                return NotFound(ApiResponse<object>.Fail(ex.Message));
            return Conflict(ApiResponse<object>.Fail(ex.Message));
        }
    }

    /// <summary>
    /// Submit current version + the new ordered list of AppointmentIds.
    /// Returns 409 if the version does not match (another user reordered concurrently).
    /// </summary>
    /// <response code="200">Queue reordered successfully.</response>
    /// <response code="400">Empty ordered list.</response>
    /// <response code="409">Concurrent reorder conflict — refresh the queue and retry.</response>
    [HttpPatch("reorder")]
    [ProducesResponseType(typeof(ApiResponse<ReorderQueueResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Reorder(
        [FromBody] ReorderQueueRequestDto request,
        CancellationToken ct)
    {
        if (request.OrderedAppointmentIds is null or { Count: 0 })
            return BadRequest(ApiResponse<object>.Fail("OrderedAppointmentIds must not be empty."));

        try
        {
            var result = await _queue.ReorderQueueAsync(
                new ReorderQueueRequest(request.OrderedAppointmentIds, request.ExpectedVersion), ct);

            return Ok(ApiResponse<ReorderQueueResponseDto>.Ok(
                new ReorderQueueResponseDto(result.OrderedIds, result.NewVersion)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Queue reorder conflict: {Message}", ex.Message);
            return Conflict(ApiResponse<object>.Fail(ex.Message));
        }
    }

    /// <summary>
    /// Server-Sent Events stream for real-time queue updates.
    /// Connect with EventSource('/api/queue/events') in the browser.
    /// The server sends a heartbeat comment (': heartbeat') every 15 s to keep the connection alive.
    /// </summary>
    [HttpGet("events")]
    [Produces("text/event-stream")]
    public async Task StreamEvents(CancellationToken ct)
    {
        Response.Headers.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-cache";
        Response.Headers.Connection = "keep-alive";
        Response.Headers["X-Accel-Buffering"] = "no"; // disable nginx buffering

        using var heartbeatTimer = new PeriodicTimer(TimeSpan.FromSeconds(15));
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);

        // Heartbeat task — keeps the connection alive through proxies
        var heartbeatTask = Task.Run(async () =>
        {
            try
            {
                while (await heartbeatTimer.WaitForNextTickAsync(cts.Token))
                {
                    await Response.WriteAsync(": heartbeat\n\n", cts.Token);
                    await Response.Body.FlushAsync(cts.Token);
                }
            }
            catch (OperationCanceledException) { /* expected on disconnect */ }
        }, cts.Token);

        _logger.LogInformation("Queue SSE client connected. Active connections: {Count}",
            _broadcaster.ActiveConnections + 1);

        try
        {
            var broadcaster = (PropelIQ.Infrastructure.Queue.QueueEventBroadcaster)_broadcaster;
            await foreach (var msg in broadcaster.SubscribeAllAsync(cts.Token))
            {
                string eventName;
                string json;

                if (msg.Event is { } evt)
                {
                    json = JsonSerializer.Serialize(evt, new JsonSerializerOptions
                    { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
                    eventName = evt.EventType switch
                    {
                        QueueEventType.Added   => "queue.added",
                        QueueEventType.Updated => "queue.updated",
                        QueueEventType.Removed => "queue.removed",
                        _                      => "queue.event"
                    };
                }
                else if (msg.ReorderEvent is { } reorder)
                {
                    json = JsonSerializer.Serialize(reorder, new JsonSerializerOptions
                    { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
                    eventName = "queue.reordered";
                }
                else continue;

                await Response.WriteAsync($"event: {eventName}\ndata: {json}\n\n", cts.Token);
                await Response.Body.FlushAsync(cts.Token);
            }
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Queue SSE client disconnected.");
        }
        finally
        {
            cts.Cancel();
            await heartbeatTask;
        }
    }
}

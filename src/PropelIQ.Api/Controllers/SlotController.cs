using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.WalkIn;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/walk-in/slots")]
[Produces("application/json")]
public sealed class SlotController : ControllerBase
{
    private readonly ISlotAvailabilityService _slots;
    private readonly ILogger<SlotController> _logger;

    public SlotController(ISlotAvailabilityService slots, ILogger<SlotController> logger)
    {
        _slots = slots;
        _logger = logger;
    }

    /// <summary>
    /// Returns available appointment slots for walk-in scheduling.
    /// </summary>
    /// <response code="200">List of open slots (may be empty if fully booked).</response>
    [HttpGet]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<AvailableSlotDto>>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAvailableSlots(
        [FromQuery] string? providerId = null,
        [FromQuery] string? clinicId = null,
        [FromQuery] int windowHours = 8,
        CancellationToken ct = default)
    {
        var now = DateTimeOffset.UtcNow;
        var query = new SlotAvailabilityQuery(
            providerId,
            clinicId,
            now,
            now.AddHours(Math.Clamp(windowHours, 1, 48)));

        var slots = await _slots.GetAvailableSlotsAsync(query, ct);

        return Ok(ApiResponse<IReadOnlyList<AvailableSlotDto>>.Ok(
            slots.Select(s => new AvailableSlotDto(
                s.SlotId, s.Version, s.ProviderId, s.ProviderName,
                s.StartTime, s.EndTime, s.DurationMinutes, s.Location)).ToList()));
    }

    /// <summary>
    /// Validates slot availability at save time and assigns the slot (conflict check).
    /// Called server-side when BookWalkIn includes a SlotId.
    /// Exposed here for explicit pre-submit checks from the UI if needed.
    /// </summary>
    /// <response code="200">Slot is still available.</response>
    /// <response code="409">Slot is no longer available (conflict).</response>
    /// <response code="404">Slot not found.</response>
    [HttpPost("{slotId:guid}/check")]
    [ProducesResponseType(typeof(ApiResponse<SlotCheckResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> CheckSlot(
        Guid slotId,
        [FromBody] SlotCheckRequestDto request,
        CancellationToken ct)
    {
        var slots = await _slots.GetAvailableSlotsAsync(
            new SlotAvailabilityQuery(null, null, DateTimeOffset.UtcNow, DateTimeOffset.UtcNow.AddHours(48)), ct);

        var slot = slots.FirstOrDefault(s => s.SlotId == slotId);
        if (slot is null)
            return NotFound(ApiResponse<object>.Fail("Slot not found."));

        if (slot.Version != request.ExpectedVersion)
            return Conflict(ApiResponse<object>.Fail("Slot is no longer available. Please select another slot."));

        return Ok(ApiResponse<SlotCheckResponseDto>.Ok(new SlotCheckResponseDto(
            slot.SlotId, slot.Version, slot.ProviderName, slot.StartTime, slot.EndTime, true)));
    }
}

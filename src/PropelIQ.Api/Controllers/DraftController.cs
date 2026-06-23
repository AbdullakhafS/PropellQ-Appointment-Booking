using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/intake/{appointmentId:int}/draft")]
[Produces("application/json")]
public sealed class DraftController : ControllerBase
{
    private readonly IIntakeDraftService _draftService;
    private readonly ILogger<DraftController> _logger;

    public DraftController(IIntakeDraftService draftService, ILogger<DraftController> logger)
    {
        _draftService = draftService;
        _logger = logger;
    }

    /// <summary>
    /// Returns the active partial intake draft for an appointment, or 204 if none exists.
    /// </summary>
    /// <response code="200">Active draft found.</response>
    /// <response code="204">No active (non-expired) draft for this appointment.</response>
    [HttpGet]
    [ProducesResponseType(typeof(ApiResponse<GetDraftResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> GetDraft(int appointmentId, CancellationToken ct)
    {
        var result = await _draftService.GetDraftAsync(appointmentId, ct);
        if (result is null) return NoContent();

        return Ok(ApiResponse<GetDraftResponseDto>.Ok(
            new GetDraftResponseDto(result.Mode, result.DataJson, result.SwitchCount, result.LastUpdated, result.ExpiresAt)));
    }

    /// <summary>
    /// Saves or overwrites the partial intake draft for an appointment.
    /// </summary>
    /// <response code="204">Draft saved.</response>
    /// <response code="400">Validation error.</response>
    [HttpPost]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> SaveDraft(
        int appointmentId,
        [FromBody] SaveDraftRequestDto request,
        CancellationToken ct)
    {
        if (appointmentId <= 0)
            return BadRequest(ApiResponse<object>.Fail("Invalid appointmentId."));

        await _draftService.SaveDraftAsync(
            new SaveDraftRequest(appointmentId, request.PatientId, request.Mode, request.DataJson, request.SwitchCount),
            ct);

        return NoContent();
    }

    /// <summary>
    /// Deletes the draft after successful submission.
    /// </summary>
    /// <response code="204">Draft deleted (or did not exist).</response>
    [HttpDelete]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> DeleteDraft(int appointmentId, CancellationToken ct)
    {
        await _draftService.DeleteDraftAsync(appointmentId, ct);
        return NoContent();
    }
}

using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.WalkIn;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/walk-in")]
[Produces("application/json")]
public sealed class WalkInController : ControllerBase
{
    private readonly IWalkInBookingService _service;
    private readonly ISlotAvailabilityService _slots;
    private readonly ILogger<WalkInController> _logger;

    public WalkInController(
        IWalkInBookingService service,
        ISlotAvailabilityService slots,
        ILogger<WalkInController> logger)
    {
        _service = service;
        _slots = slots;
        _logger = logger;
    }

    /// <summary>
    /// Searches patients by name, phone, email, or patient ID.
    /// </summary>
    /// <response code="200">Matching patient records.</response>
    /// <response code="400">Search term too short.</response>
    [HttpGet("patients/search")]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<PatientSearchResponseDto>>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> SearchPatients(
        [FromQuery] string q,
        [FromQuery] int limit = 20,
        CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(q) || q.Trim().Length < 2)
            return BadRequest(ApiResponse<object>.Fail("Search term must be at least 2 characters."));

        var results = await _service.SearchPatientsAsync(new PatientSearchQuery(q, Math.Clamp(limit, 1, 50)), ct);

        return Ok(ApiResponse<IReadOnlyList<PatientSearchResponseDto>>.Ok(
            results.Select(p => new PatientSearchResponseDto(
                p.Id, p.FirstName, p.LastName, p.FullName,
                p.DateOfBirth.ToString("yyyy-MM-dd"), p.Phone, p.Email, p.Gender)).ToList()));
    }

    /// <summary>
    /// Creates a new patient record for walk-in registration.
    /// </summary>
    /// <response code="201">Patient created.</response>
    /// <response code="400">Validation error.</response>
    [HttpPost("patients")]
    [ProducesResponseType(typeof(ApiResponse<PatientSearchResponseDto>), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreatePatient(
        [FromBody] CreatePatientRequestDto request,
        CancellationToken ct)
    {
        var patient = await _service.CreatePatientAsync(new CreatePatientRequest(
            request.FirstName, request.LastName, request.DateOfBirth,
            request.Phone, request.Gender, request.Email, request.Address, request.Notes), ct);

        var dto = new PatientSearchResponseDto(
            patient.Id, patient.FirstName, patient.LastName, patient.FullName,
            patient.DateOfBirth.ToString("yyyy-MM-dd"), patient.Phone, patient.Email, patient.Gender);

        return CreatedAtAction(nameof(SearchPatients), new { q = patient.Id.ToString() },
            ApiResponse<PatientSearchResponseDto>.Ok(dto));
    }

    /// <summary>
    /// Books a walk-in appointment for a selected/created patient.
    /// Always persists IsWalkIn = true.
    /// </summary>
    /// <response code="201">Appointment booked.</response>
    /// <response code="400">Validation error.</response>
    /// <response code="404">Patient not found.</response>
    [HttpPost("appointments")]
    [ProducesResponseType(typeof(ApiResponse<BookWalkInResponseDto>), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> BookWalkIn(
        [FromBody] BookWalkInRequestDto request,
        CancellationToken ct)
    {
        try
        {
            // Real-time slot conflict check at save time (task_032_003)
            if (request.SlotId.HasValue && request.SlotVersion.HasValue)
            {
                var assignResult = await _slots.AssignSlotAsync(
                    new AssignSlotRequest(request.SlotId.Value, request.SlotVersion.Value, Guid.Empty), ct);

                if (assignResult == SlotAssignmentResult.NotFound)
                    return NotFound(ApiResponse<object>.Fail("Selected slot not found."));

                if (assignResult == SlotAssignmentResult.Conflict)
                    return Conflict(ApiResponse<object>.Fail(
                        "The selected slot is no longer available. Please choose another slot."));
            }

            var result = await _service.BookWalkInAsync(new BookWalkInRequest(
                request.PatientId, request.ProviderName,
                request.AppointmentTime, request.DurationMinutes, request.Notes,
                request.SlotId, request.SlotVersion), ct);

            var dto = new BookWalkInResponseDto(
                result.AppointmentId, result.PatientId, result.PatientFullName,
                result.ProviderName, result.AppointmentTime, result.DurationMinutes,
                result.IsWalkIn, result.Status, result.CreatedAt, result.SlotId);

            return CreatedAtAction(nameof(BookWalkIn), new { id = dto.AppointmentId },
                ApiResponse<BookWalkInResponseDto>.Ok(dto));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Walk-in booking failed for patient {PatientId}", request.PatientId);
            return NotFound(ApiResponse<object>.Fail(ex.Message));
        }
    }
}

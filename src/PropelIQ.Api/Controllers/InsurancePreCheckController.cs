using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/intake")]
[Produces("application/json")]
public sealed class InsurancePreCheckController : ControllerBase
{
    private readonly IInsurancePreCheckService _preCheckService;
    private readonly ILogger<InsurancePreCheckController> _logger;

    public InsurancePreCheckController(
        IInsurancePreCheckService preCheckService,
        ILogger<InsurancePreCheckController> logger)
    {
        _preCheckService = preCheckService;
        _logger = logger;
    }

    /// <summary>
    /// Performs a soft insurance pre-check against the predefined plans database.
    /// Always returns a result — never blocks booking on unverified outcome.
    /// </summary>
    /// <response code="200">Pre-check result with confidence score and status.</response>
    /// <response code="400">Validation error in request body.</response>
    [HttpPost("insurance-check")]
    [ProducesResponseType(typeof(ApiResponse<InsurancePreCheckResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<InsurancePreCheckResponseDto>), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> InsuranceCheck(
        [FromBody] InsurancePreCheckRequestDto request,
        CancellationToken ct)
    {
        var result = await _preCheckService.CheckAsync(
            new InsurancePreCheckRequest(
                request.AppointmentId,
                request.PatientId,
                request.InsuranceName,
                request.MemberId,
                request.GroupNumber),
            ct);

        return Ok(ApiResponse<InsurancePreCheckResponseDto>.Ok(
            new InsurancePreCheckResponseDto(
                result.MatchedPlanId,
                result.MatchedPlanName,
                result.ConfidenceScore,
                result.VerificationStatus,
                result.Reason,
                result.VerificationStatus == "verified")));
    }
}

using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Insurance;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/insurance")]
[Produces("application/json")]
public sealed class InsuranceReviewController : ControllerBase
{
    private readonly IInsuranceReviewService _reviewService;
    private readonly ILogger<InsuranceReviewController> _logger;

    public InsuranceReviewController(
        IInsuranceReviewService reviewService,
        ILogger<InsuranceReviewController> logger)
    {
        _reviewService = reviewService;
        _logger = logger;
    }

    /// <summary>
    /// Returns a paginated, filtered, sorted list of insurance verifications for staff review.
    /// </summary>
    /// <response code="200">Pending insurance verification rows.</response>
    [HttpGet("pending")]
    [ProducesResponseType(typeof(ApiResponse<PendingInsuranceResponseDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetPending(
        [FromQuery] string? status = "unverified",
        [FromQuery] string? insurance = null,
        [FromQuery] int? dateRangeDays = null,
        [FromQuery] string sortBy = "date",
        [FromQuery] bool sortAsc = true,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50,
        CancellationToken ct = default)
    {
        pageSize = Math.Clamp(pageSize, 1, 200);
        page = Math.Max(1, page);

        var result = await _reviewService.GetPendingAsync(
            new PendingInsuranceQuery(status, insurance, dateRangeDays, sortBy, sortAsc, page, pageSize),
            ct);

        return Ok(ApiResponse<PendingInsuranceResponseDto>.Ok(
            new PendingInsuranceResponseDto(
                result.Items.Select(MapRow).ToList(),
                result.TotalCount,
                result.Page,
                result.PageSize)));
    }

    /// <summary>
    /// Returns the audit history for a specific insurance verification record.
    /// </summary>
    /// <response code="200">Audit history entries.</response>
    /// <response code="404">Verification not found.</response>
    [HttpGet("{id:int}/audit")]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<AuditEntryDto>>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetAuditHistory(int id, CancellationToken ct)
    {
        var entries = await _reviewService.GetAuditHistoryAsync(id, ct);
        return Ok(ApiResponse<IReadOnlyList<AuditEntryDto>>.Ok(
            entries.Select(a => new AuditEntryDto(
                a.Id, a.PreviousStatus, a.NewStatus,
                a.VerifiedByStaffId, a.VerificationMethod, a.Notes, a.VerifiedAt)).ToList()));
    }

    /// <summary>
    /// Marks a single insurance verification record as verified/manual_review.
    /// </summary>
    /// <response code="200">Verification updated.</response>
    /// <response code="400">Validation error.</response>
    /// <response code="404">Verification not found.</response>
    [HttpPatch("{id:int}/verify")]
    [ProducesResponseType(typeof(ApiResponse<VerifyInsuranceResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> VerifySingle(
        int id,
        [FromBody] VerifyInsuranceRequestDto request,
        CancellationToken ct)
    {
        try
        {
            var result = await _reviewService.VerifyAsync(
                new VerifyInsuranceRequest(id, request.StaffId, request.NewStatus, request.VerificationMethod, request.Notes),
                ct);

            return Ok(ApiResponse<VerifyInsuranceResponseDto>.Ok(
                new VerifyInsuranceResponseDto(result.Id, result.VerificationStatus, result.VerifiedByStaffId, result.VerifiedAt)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "InsuranceVerification {Id} not found for verify", id);
            return NotFound();
        }
    }

    /// <summary>
    /// Marks multiple insurance verification records as verified in a single batch.
    /// </summary>
    /// <response code="200">Batch result with updated records and failure count.</response>
    [HttpPatch("verify/batch")]
    [ProducesResponseType(typeof(ApiResponse<BatchVerifyResponseDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> VerifyBatch(
        [FromBody] BatchVerifyRequestDto request,
        CancellationToken ct)
    {
        if (request.Ids is null or { Count: 0 })
            return BadRequest(ApiResponse<object>.Fail("At least one ID is required."));

        var requests = request.Ids.Select(id =>
            new VerifyInsuranceRequest(id, request.StaffId, request.NewStatus, request.VerificationMethod, request.Notes))
            .ToList();

        var results = await _reviewService.VerifyBatchAsync(requests, ct);
        var failed = request.Ids.Count - results.Count;

        return Ok(ApiResponse<BatchVerifyResponseDto>.Ok(
            new BatchVerifyResponseDto(
                results.Select(r => new VerifyInsuranceResponseDto(r.Id, r.VerificationStatus, r.VerifiedByStaffId, r.VerifiedAt)).ToList(),
                failed)));
    }

    private static PendingInsuranceRowDto MapRow(PendingInsuranceRow r)
        => new(r.Id, r.AppointmentId, r.PatientId, r.PatientName,
               r.InsuranceName, r.MemberId, r.MatchedPlanId, r.MatchedPlanName,
               r.ConfidenceScore, r.VerificationStatus, r.AppointmentDate, r.LastVerifiedAt, r.CreatedAt);
}

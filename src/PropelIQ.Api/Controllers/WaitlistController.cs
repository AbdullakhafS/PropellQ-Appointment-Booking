using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Waitlist;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/waitlist")]
[Produces("application/json")]
public sealed class WaitlistController : ControllerBase
{
    private readonly IWaitlistService _waitlist;
    private readonly IAutoOfferOrchestrator _orchestrator;
    private readonly ILogger<WaitlistController> _logger;

    public WaitlistController(
        IWaitlistService waitlist,
        IAutoOfferOrchestrator orchestrator,
        ILogger<WaitlistController> logger)
    {
        _waitlist = waitlist;
        _orchestrator = orchestrator;
        _logger = logger;
    }

    /// <summary>Returns all active (queued/offered) waitlist entries, optionally filtered by provider.</summary>
    [HttpGet]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<WaitlistEntryDto>>), StatusCodes.Status200OK)]
    public IActionResult GetEntries([FromQuery] string? providerId = null)
    {
        var entries = _waitlist.GetEntries(providerId);
        return Ok(ApiResponse<IReadOnlyList<WaitlistEntryDto>>.Ok(entries.Select(MapEntry).ToList()));
    }

    /// <summary>
    /// Adds a patient to the waitlist. Returns existing entry if already active.
    /// </summary>
    /// <response code="201">Waitlist entry created.</response>
    /// <response code="200">Patient already on waitlist (idempotent).</response>
    [HttpPost]
    [ProducesResponseType(typeof(ApiResponse<WaitlistEntryDto>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<WaitlistEntryDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> Join([FromBody] JoinWaitlistRequestDto request, CancellationToken ct)
    {
        var result = await _waitlist.JoinAsync(new JoinWaitlistRequest(
            request.PatientId, request.PatientFullName,
            request.ProviderId, request.ProviderName,
            request.ClinicId, request.PreferredTimeContext), ct);

        var dto = MapEntry(result);
        return StatusCode(StatusCodes.Status201Created, ApiResponse<WaitlistEntryDto>.Ok(dto));
    }

    /// <summary>Cancels a queued waitlist entry.</summary>
    [HttpDelete("{entryId:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public IActionResult Cancel(Guid entryId)
    {
        _waitlist.Cancel(entryId);
        return NoContent();
    }

    /// <summary>
    /// Issues a slot offer to the next eligible patient in the waitlist.
    /// Returns 204 if no eligible candidates remain.
    /// </summary>
    [HttpPost("offers/issue")]
    [ProducesResponseType(typeof(ApiResponse<WaitlistOfferDto>), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> IssueOffer([FromBody] IssueOfferRequestDto request, CancellationToken ct)
    {
        var offer = await _waitlist.IssueNextOfferAsync(
            request.ProviderId, request.SlotId, request.ProviderName, request.SlotStartTime, ct);

        if (offer is null) return NoContent();

        return StatusCode(StatusCodes.Status201Created,
            ApiResponse<WaitlistOfferDto>.Ok(MapOffer(offer)));
    }

    /// <summary>Returns all pending (non-expired) offers.</summary>
    [HttpGet("offers/pending")]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<WaitlistOfferDto>>), StatusCodes.Status200OK)]
    public IActionResult GetPendingOffers()
    {
        var offers = _waitlist.GetPendingOffers();
        return Ok(ApiResponse<IReadOnlyList<WaitlistOfferDto>>.Ok(offers.Select(MapOffer).ToList()));
    }

    /// <summary>
    /// Accepts or declines a pending offer.
    /// Accept converts the waitlist entry to a confirmed appointment.
    /// Decline progresses the offer to the next eligible patient.
    /// </summary>
    /// <response code="200">Offer response recorded.</response>
    /// <response code="404">Offer not found.</response>
    /// <response code="409">Offer is no longer pending (already responded or expired).</response>
    [HttpPatch("offers/{offerId:guid}/respond")]
    [ProducesResponseType(typeof(ApiResponse<OfferConversionResultDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Respond(
        Guid offerId,
        [FromBody] RespondToOfferRequestDto request,
        CancellationToken ct)
    {
        try
        {
            var result = await _waitlist.RespondAsync(new RespondToOfferRequest(offerId, request.IsAccept), ct);
            return Ok(ApiResponse<OfferConversionResultDto>.Ok(
                new OfferConversionResultDto(result.OfferId, result.OfferStatus, result.AppointmentId)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Waitlist offer respond failed: {Message}", ex.Message);
            if (ex.Message.Contains("not found", StringComparison.OrdinalIgnoreCase))
                return NotFound(ApiResponse<object>.Fail(ex.Message));
            return Conflict(ApiResponse<object>.Fail(ex.Message));
        }
    }

    /// <summary>Processes expired offers and advances waitlist to next eligible candidates.</summary>
    [HttpPost("offers/process-expired")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> ProcessExpired(CancellationToken ct)
    {
        await _waitlist.ProcessExpiredOffersAsync(ct);
        return NoContent();
    }

    /// <summary>
    /// Explicitly triggers the waitlist processing pipeline for a released slot.
    /// Useful for testing, observability, and manual operator-initiated processing.
    /// Returns the trigger outcome: issued, no_candidates.
    /// </summary>
    /// <response code="200">Pipeline ran; outcome in body.</response>
    [HttpPost("process-slot")]
    [ProducesResponseType(typeof(ApiResponse<ProcessSlotResponseDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> ProcessSlot(
        [FromBody] ProcessSlotRequestDto request,
        CancellationToken ct)
    {
        var result = await _orchestrator.TriggerForReleasedSlotAsync(
            new SlotReleasedEvent(
                request.ProviderId,
                request.SlotId,
                request.ProviderName,
                request.SlotTime,
                request.ReleaseReason ?? "manual"),
            ct);

        return Ok(ApiResponse<ProcessSlotResponseDto>.Ok(
            new ProcessSlotResponseDto(result.OfferIssued, result.OfferId, result.Reason)));
    }

    private static WaitlistEntryDto MapEntry(WaitlistEntryResult r)
        => new(r.WaitlistEntryId, r.PatientId, r.PatientFullName, r.ProviderName, r.Status, r.Priority, r.CreatedAt);

    private static WaitlistOfferDto MapOffer(WaitlistOfferResult o)
        => new(o.OfferId, o.WaitlistEntryId, o.PatientId, o.PatientFullName, o.ProviderName,
               o.SlotStartTime, o.Status, o.ExpiresAt, o.RespondedAt, o.ConvertedAppointmentId);
}

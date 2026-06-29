using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using Microsoft.Extensions.Logging;

namespace PropelIQ.Infrastructure.Waitlist;

/// <summary>
/// Orchestrates the auto-offer pipeline when an appointment slot is released (US-040, US-042).
/// Pipeline:
///   1. Select the first eligible FIFO waitlist candidate (IWaitlistService — idempotent).
///   2. Issue an offer record with 30-minute expiry.
///   3. Dispatch an offer notification to the patient (INotificationService — US-042 task_042_003).
/// </summary>
public sealed class AutoOfferOrchestrator : IAutoOfferOrchestrator
{
    private readonly IWaitlistService _waitlist;
    private readonly INotificationService _notifications;
    private readonly ILogger<AutoOfferOrchestrator> _logger;

    public AutoOfferOrchestrator(
        IWaitlistService waitlist,
        INotificationService notifications,
        ILogger<AutoOfferOrchestrator> logger)
    {
        _waitlist = waitlist;
        _notifications = notifications;
        _logger = logger;
    }

    public async Task<AutoOfferTriggerResult> TriggerForReleasedSlotAsync(
        SlotReleasedEvent slotEvent,
        CancellationToken ct = default)
    {
        _logger.LogInformation(
            "Auto-offer triggered: provider={Provider} slot={SlotId} reason={Reason}",
            slotEvent.ProviderName, slotEvent.SlotId, slotEvent.ReleaseReason);

        // Step 1 + 2: FIFO candidate selection and offer creation (idempotent)
        WaitlistOfferResult? offer = await _waitlist.IssueNextOfferAsync(
            slotEvent.ProviderId,
            slotEvent.SlotId,
            slotEvent.ProviderName,
            slotEvent.SlotTime,
            ct);

        if (offer is null)
        {
            _logger.LogInformation(
                "Auto-offer: no waitlist candidates for provider={Provider}", slotEvent.ProviderName);
            return new AutoOfferTriggerResult(false, null, "no_candidates");
        }

        _logger.LogInformation(
            "Auto-offer: offer={OfferId} issued to entry={EntryId} patient={PatientId}",
            offer.OfferId, offer.WaitlistEntryId, offer.PatientId);

        // Step 3: Notify the patient their slot offer is ready (US-042 task_042_003)
        // Fire-and-forget: notification failure must not block the offer pipeline.
        _ = _notifications.NotifyWaitlistOfferAsync(
            new WaitlistOfferNotification(
                offer.OfferId,
                offer.PatientId,
                offer.PatientFullName,
                offer.ProviderName,
                offer.SlotStartTime,
                offer.ExpiresAt),
            ct);

        return new AutoOfferTriggerResult(true, offer.OfferId, "issued");
    }
}

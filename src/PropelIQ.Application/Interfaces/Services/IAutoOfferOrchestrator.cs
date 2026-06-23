using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

/// <summary>
/// Orchestrates the automatic offer pipeline when a slot is released.
/// Responsibilities:
///   1. Select the first eligible FIFO waitlist candidate for the freed provider/slot.
///   2. Issue an offer via IWaitlistService with idempotency (no duplicate offers per slot).
///   3. Return the trigger outcome for observability.
/// </summary>
public interface IAutoOfferOrchestrator
{
    /// <summary>
    /// Runs the auto-offer pipeline for the given released slot.
    /// Returns the outcome: issued, no_candidates, or idempotent_skip.
    /// </summary>
    Task<AutoOfferTriggerResult> TriggerForReleasedSlotAsync(
        SlotReleasedEvent slotEvent,
        CancellationToken ct = default);
}

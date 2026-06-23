using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IWaitlistService
{
    /// <summary>Adds a patient to the waitlist. Prevents duplicate active entries.</summary>
    Task<WaitlistEntryResult> JoinAsync(JoinWaitlistRequest request, CancellationToken ct = default);

    /// <summary>Returns all active waitlist entries ordered by priority then created_at.</summary>
    IReadOnlyList<WaitlistEntryResult> GetEntries(string? providerId = null);

    /// <summary>
    /// Creates an offer for the next eligible patient in the waitlist for a given provider/slot.
    /// Returns null if no eligible candidates remain.
    /// </summary>
    Task<WaitlistOfferResult?> IssueNextOfferAsync(string providerId, Guid? slotId, string providerName, DateTimeOffset slotStartTime, CancellationToken ct = default);

    /// <summary>Accepts or declines a pending offer. Converts to appointment on accept.</summary>
    Task<OfferConversionResult> RespondAsync(RespondToOfferRequest request, CancellationToken ct = default);

    /// <summary>Marks expired offers and advances to next eligible candidates.</summary>
    Task ProcessExpiredOffersAsync(CancellationToken ct = default);

    /// <summary>Returns all pending offers.</summary>
    IReadOnlyList<WaitlistOfferResult> GetPendingOffers();

    /// <summary>Cancels a queued waitlist entry.</summary>
    void Cancel(Guid waitlistEntryId);
}

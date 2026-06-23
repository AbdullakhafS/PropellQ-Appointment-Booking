using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.WalkIn;

namespace PropelIQ.Infrastructure.Waitlist;

/// <summary>
/// In-memory waitlist service.
/// Singleton so entries and offers persist across request scopes.
/// Replace with EF Core when the data layer is wired up.
/// </summary>
public sealed class WaitlistService : IWaitlistService
{
    private static readonly List<WaitlistEntry> _entries = [];
    private static readonly List<WaitlistOffer> _offers = [];
    private static readonly object _lock = new();

    // --- Join ---

    public Task<WaitlistEntryResult> JoinAsync(JoinWaitlistRequest request, CancellationToken ct = default)
    {
        lock (_lock)
        {
            // Duplicate guard: same patient + same provider with queued/offered status
            var duplicate = _entries.FirstOrDefault(e =>
                e.PatientId == request.PatientId &&
                e.ProviderId == request.ProviderId &&
                e.Status is "queued" or "offered");

            if (duplicate is not null)
                return Task.FromResult(MapEntry(duplicate));

            // FIFO priority = count of existing active entries + 1
            int priority = _entries.Count(e => e.Status is "queued" or "offered") + 1;

            var entry = WaitlistEntry.Create(
                request.PatientId, request.PatientFullName,
                request.ProviderId, request.ProviderName,
                request.ClinicId, request.PreferredTimeContext, priority);

            _entries.Add(entry);
            return Task.FromResult(MapEntry(entry));
        }
    }

    // --- List entries ---

    public IReadOnlyList<WaitlistEntryResult> GetEntries(string? providerId = null)
    {
        lock (_lock)
        {
            var q = _entries.AsEnumerable().Where(e => e.Status is "queued" or "offered");
            if (!string.IsNullOrWhiteSpace(providerId))
                q = q.Where(e => e.ProviderId.Equals(providerId, StringComparison.OrdinalIgnoreCase));
            return q.OrderBy(e => e.Priority).ThenBy(e => e.CreatedAt).Select(MapEntry).ToList();
        }
    }

    // --- Issue offer ---

    public Task<WaitlistOfferResult?> IssueNextOfferAsync(
        string providerId, Guid? slotId, string providerName,
        DateTimeOffset slotStartTime, CancellationToken ct = default)
    {
        lock (_lock)
        {
            // Idempotency guard (task_040_003): if a non-expired pending offer already
            // exists for this exact slot, return it instead of creating a duplicate.
            if (slotId.HasValue)
            {
                var existing = _offers.FirstOrDefault(o =>
                    o.OfferedSlotId == slotId &&
                    o.Status == "pending" &&
                    !o.IsExpired);

                if (existing is not null)
                {
                    var existingEntry = _entries.FirstOrDefault(e => e.Id == existing.WaitlistEntryId);
                    return Task.FromResult<WaitlistOfferResult?>(MapOffer(existing, existingEntry?.PatientFullName ?? string.Empty));
                }
            }

            // Find next queued patient for this provider
            var next = _entries
                .Where(e => e.ProviderId.Equals(providerId, StringComparison.OrdinalIgnoreCase) && e.Status == "queued")
                .OrderBy(e => e.Priority).ThenBy(e => e.CreatedAt)
                .FirstOrDefault();

            if (next is null) return Task.FromResult<WaitlistOfferResult?>(null);

            next.MarkOffered();

            var offer = WaitlistOffer.Create(next.Id, next.PatientId, slotId, providerName, slotStartTime);
            _offers.Add(offer);

            return Task.FromResult<WaitlistOfferResult?>(MapOffer(offer, next.PatientFullName));
        }
    }

    // --- Accept / Decline ---

    public Task<OfferConversionResult> RespondAsync(RespondToOfferRequest request, CancellationToken ct = default)
    {
        lock (_lock)
        {
            var offer = _offers.FirstOrDefault(o => o.Id == request.OfferId)
                ?? throw new InvalidOperationException($"Offer {request.OfferId} not found.");

            if (!offer.IsPending)
                throw new InvalidOperationException(
                    $"Offer {request.OfferId} is {offer.Status} and cannot be responded to.");

            var entry = _entries.First(e => e.Id == offer.WaitlistEntryId);

            if (request.IsAccept)
            {
                // Convert to appointment (task_039_004)
                var appointment = Appointment.Create(
                    offer.PatientId,
                    entry.PatientFullName,
                    offer.ProviderName,
                    offer.SlotStartTime);

                WalkInBookingService.Appointments.Add(appointment);

                offer.Accept(appointment.Id);
                entry.MarkFulfilled();

                return Task.FromResult(new OfferConversionResult(offer.Id, offer.Status, appointment.Id));
            }
            else
            {
                offer.Decline();
                entry.RevertToQueued(); // Put back in queue with same priority

                // Issue offer to next eligible patient (same provider context)
                _ = IssueNextOfferAsync(entry.ProviderId, offer.OfferedSlotId,
                    offer.ProviderName, offer.SlotStartTime, ct);

                return Task.FromResult(new OfferConversionResult(offer.Id, offer.Status, null));
            }
        }
    }

    // --- Expire pending offers (task_039_005) ---

    public Task ProcessExpiredOffersAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            var expiredOffers = _offers
                .Where(o => o.Status == "pending" && o.IsExpired)
                .ToList();

            foreach (var offer in expiredOffers)
            {
                offer.MarkExpired();

                var entry = _entries.FirstOrDefault(e => e.Id == offer.WaitlistEntryId);
                if (entry is not null && entry.Status == "offered")
                {
                    entry.RevertToQueued();

                    // Advance to next candidate
                    _ = IssueNextOfferAsync(entry.ProviderId, offer.OfferedSlotId,
                        offer.ProviderName, offer.SlotStartTime, ct);
                }
            }
        }

        return Task.CompletedTask;
    }

    // --- Pending offers list ---

    public IReadOnlyList<WaitlistOfferResult> GetPendingOffers()
    {
        lock (_lock)
        {
            return _offers
                .Where(o => o.Status == "pending" && !o.IsExpired)
                .OrderBy(o => o.CreatedAt)
                .Select(o =>
                {
                    var entry = _entries.FirstOrDefault(e => e.Id == o.WaitlistEntryId);
                    return MapOffer(o, entry?.PatientFullName ?? string.Empty);
                })
                .ToList();
        }
    }

    // --- Cancel ---

    public void Cancel(Guid waitlistEntryId)
    {
        lock (_lock)
        {
            var entry = _entries.FirstOrDefault(e => e.Id == waitlistEntryId);
            entry?.MarkCancelled();
        }
    }

    // --- Mappers ---

    private static WaitlistEntryResult MapEntry(WaitlistEntry e)
        => new(e.Id, e.PatientId, e.PatientFullName, e.ProviderName, e.Status, e.Priority, e.CreatedAt);

    private static WaitlistOfferResult MapOffer(WaitlistOffer o, string patientFullName = "")
        => new(o.Id, o.WaitlistEntryId, o.PatientId, patientFullName, o.ProviderName,
               o.SlotStartTime, o.Status, o.ExpiresAt, o.RespondedAt, o.ConvertedAppointmentId);
}

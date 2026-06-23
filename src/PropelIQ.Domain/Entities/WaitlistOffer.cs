namespace PropelIQ.Domain.Entities;

/// <summary>
/// A time-limited offer sent to a waitlisted patient when a slot opens.
/// States: pending → accepted | declined | expired
/// Default expiry window: 30 minutes.
/// </summary>
public sealed class WaitlistOffer
{
    public static readonly TimeSpan DefaultExpiryWindow = TimeSpan.FromMinutes(30);

    public Guid Id { get; private set; }
    public Guid WaitlistEntryId { get; private set; }
    public Guid PatientId { get; private set; }
    public Guid? OfferedSlotId { get; private set; }
    public string ProviderName { get; private set; } = string.Empty;
    public DateTimeOffset SlotStartTime { get; private set; }
    public string Status { get; private set; } = "pending";   // pending | accepted | declined | expired
    public DateTimeOffset CreatedAt { get; private set; }
    public DateTimeOffset ExpiresAt { get; private set; }
    public DateTimeOffset? RespondedAt { get; private set; }
    /// <summary>AppointmentId populated when offer is accepted and booking confirmed.</summary>
    public Guid? ConvertedAppointmentId { get; private set; }

    private WaitlistOffer() { }

    public static WaitlistOffer Create(
        Guid waitlistEntryId,
        Guid patientId,
        Guid? offeredSlotId,
        string providerName,
        DateTimeOffset slotStartTime)
        => new()
        {
            Id = Guid.NewGuid(),
            WaitlistEntryId = waitlistEntryId,
            PatientId = patientId,
            OfferedSlotId = offeredSlotId,
            ProviderName = providerName,
            SlotStartTime = slotStartTime,
            Status = "pending",
            CreatedAt = DateTimeOffset.UtcNow,
            ExpiresAt = DateTimeOffset.UtcNow.Add(DefaultExpiryWindow)
        };

    public bool IsExpired => DateTimeOffset.UtcNow >= ExpiresAt;
    public bool IsPending => Status == "pending" && !IsExpired;

    public void Accept(Guid appointmentId)
    {
        if (!IsPending) throw new InvalidOperationException("Offer is not in a pending state or has expired.");
        Status = "accepted";
        RespondedAt = DateTimeOffset.UtcNow;
        ConvertedAppointmentId = appointmentId;
    }

    public void Decline()
    {
        if (!IsPending) throw new InvalidOperationException("Offer is not in a pending state or has expired.");
        Status = "declined";
        RespondedAt = DateTimeOffset.UtcNow;
    }

    public void MarkExpired()
    {
        if (Status == "pending") Status = "expired";
    }
}

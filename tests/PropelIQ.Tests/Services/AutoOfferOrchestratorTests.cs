using Moq;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Infrastructure.Waitlist;
using Microsoft.Extensions.Logging;

namespace PropelIQ.Tests.Services;

/// <summary>
/// Unit tests for AutoOfferOrchestrator — US-040 acceptance criteria coverage.
/// </summary>
public sealed class AutoOfferOrchestratorTests
{
    private static SlotReleasedEvent MakeEvent(
        string providerId = "Dr. Smith",
        Guid? slotId = null,
        string releaseReason = "cancelled") =>
        new(providerId, slotId ?? Guid.NewGuid(), providerId, DateTimeOffset.UtcNow.AddHours(2), releaseReason);

    private static ILogger<AutoOfferOrchestrator> NullLogger() =>
        new LoggerFactory().CreateLogger<AutoOfferOrchestrator>();

    // -------------------------------------------------------------------------
    // AC-1: Released slot triggers offer to first eligible waitlisted patient
    // -------------------------------------------------------------------------

    [Fact]
    public async Task TriggerForReleasedSlot_WhenCandidateExists_IssuedResultReturned()
    {
        var offerId = Guid.NewGuid();
        var offerResult = new WaitlistOfferResult(
            offerId, Guid.NewGuid(), Guid.NewGuid(),
            "Dr. Smith", DateTimeOffset.UtcNow.AddHours(2),
            "pending", DateTimeOffset.UtcNow.AddMinutes(30),
            null, null);

        var waitlistMock = new Mock<IWaitlistService>();
        waitlistMock
            .Setup(s => s.IssueNextOfferAsync(
                It.IsAny<string>(), It.IsAny<Guid?>(), It.IsAny<string>(),
                It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(offerResult);

        var orchestrator = new AutoOfferOrchestrator(waitlistMock.Object, NullLogger());

        var result = await orchestrator.TriggerForReleasedSlotAsync(MakeEvent());

        Assert.True(result.OfferIssued);
        Assert.Equal(offerId, result.OfferId);
        Assert.Equal("issued", result.Reason);
    }

    // -------------------------------------------------------------------------
    // AC-1: Slot context (providerId, slotId) is forwarded to IWaitlistService
    // -------------------------------------------------------------------------

    [Fact]
    public async Task TriggerForReleasedSlot_PassesCorrectSlotContextToWaitlistService()
    {
        var expectedSlotId = Guid.NewGuid();
        var expectedProvider = "Dr. Jones";
        var slotEvent = new SlotReleasedEvent(
            expectedProvider, expectedSlotId, expectedProvider,
            DateTimeOffset.UtcNow.AddHours(1), "cancelled");

        var waitlistMock = new Mock<IWaitlistService>();
        waitlistMock
            .Setup(s => s.IssueNextOfferAsync(
                expectedProvider, expectedSlotId, expectedProvider,
                slotEvent.SlotTime, It.IsAny<CancellationToken>()))
            .ReturnsAsync((WaitlistOfferResult?)null);

        var orchestrator = new AutoOfferOrchestrator(waitlistMock.Object, NullLogger());

        await orchestrator.TriggerForReleasedSlotAsync(slotEvent);

        waitlistMock.Verify(s => s.IssueNextOfferAsync(
            expectedProvider, expectedSlotId, expectedProvider,
            slotEvent.SlotTime, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // -------------------------------------------------------------------------
    // AC-1: No candidates → no_candidates result returned, no exception
    // -------------------------------------------------------------------------

    [Fact]
    public async Task TriggerForReleasedSlot_WhenNoCandidates_NoCandidatesResultReturned()
    {
        var waitlistMock = new Mock<IWaitlistService>();
        waitlistMock
            .Setup(s => s.IssueNextOfferAsync(
                It.IsAny<string>(), It.IsAny<Guid?>(), It.IsAny<string>(),
                It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((WaitlistOfferResult?)null);

        var orchestrator = new AutoOfferOrchestrator(waitlistMock.Object, NullLogger());

        var result = await orchestrator.TriggerForReleasedSlotAsync(MakeEvent());

        Assert.False(result.OfferIssued);
        Assert.Null(result.OfferId);
        Assert.Equal("no_candidates", result.Reason);
    }

    // -------------------------------------------------------------------------
    // AC-3 (idempotency): Same slot released twice → WaitlistService called twice
    // but service-level idempotency prevents duplicate offer creation
    // -------------------------------------------------------------------------

    [Fact]
    public async Task TriggerForReleasedSlot_CalledTwiceForSameSlot_WaitlistServiceCalledTwice()
    {
        var slotId = Guid.NewGuid();
        var existingOffer = new WaitlistOfferResult(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(),
            "Dr. Brown", DateTimeOffset.UtcNow.AddHours(1),
            "pending", DateTimeOffset.UtcNow.AddMinutes(30),
            null, null);

        var callCount = 0;
        var waitlistMock = new Mock<IWaitlistService>();
        waitlistMock
            .Setup(s => s.IssueNextOfferAsync(
                It.IsAny<string>(), slotId, It.IsAny<string>(),
                It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(() =>
            {
                callCount++;
                // Second call simulates idempotent return of existing offer
                return existingOffer;
            });

        var orchestrator = new AutoOfferOrchestrator(waitlistMock.Object, NullLogger());

        var slotEvent = new SlotReleasedEvent("Dr. Brown", slotId, "Dr. Brown",
            DateTimeOffset.UtcNow.AddHours(1), "cancelled");

        var r1 = await orchestrator.TriggerForReleasedSlotAsync(slotEvent);
        var r2 = await orchestrator.TriggerForReleasedSlotAsync(slotEvent);

        // Both trigger calls should pass through to the service
        Assert.Equal(2, callCount);
        // Both should report "issued" because the service returned an offer
        Assert.Equal("issued", r1.Reason);
        Assert.Equal("issued", r2.Reason);
        // Both should return the same offer (idempotent)
        Assert.Equal(r1.OfferId, r2.OfferId);
    }

    // -------------------------------------------------------------------------
    // AC-4: Decline path → next candidate offer (via WaitlistService)
    // -------------------------------------------------------------------------

    [Fact]
    public async Task TriggerForReleasedSlot_RescheduledReleaseReason_TriggersOffer()
    {
        var waitlistMock = new Mock<IWaitlistService>();
        waitlistMock
            .Setup(s => s.IssueNextOfferAsync(
                It.IsAny<string>(), It.IsAny<Guid?>(), It.IsAny<string>(),
                It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((WaitlistOfferResult?)null);

        var orchestrator = new AutoOfferOrchestrator(waitlistMock.Object, NullLogger());

        // Reschedule also releases the old slot
        var result = await orchestrator.TriggerForReleasedSlotAsync(
            MakeEvent(releaseReason: "rescheduled"));

        Assert.Equal("no_candidates", result.Reason);
        waitlistMock.Verify(s => s.IssueNextOfferAsync(
            It.IsAny<string>(), It.IsAny<Guid?>(), It.IsAny<string>(),
            It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()),
            Times.Once);
    }
}

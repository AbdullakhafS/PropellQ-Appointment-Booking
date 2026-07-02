using Moq;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Notifications;
using PropelIQ.Infrastructure.Queue;
using PropelIQ.Infrastructure.Waitlist;
using PropelIQ.Infrastructure.WalkIn;
using Microsoft.Extensions.Logging;
using PropelIQ.Infrastructure.Data;
using PropelIQ.Tests.TestInfrastructure;

namespace PropelIQ.Tests.Services;

/// <summary>
/// Integration-style unit tests for US-041: Cancellation/Reschedule Logic.
/// Validates state transitions, conflict detection, SSE events, notification dispatch,
/// and waitlist trigger behavior.
/// </summary>
public sealed class CancellationRescheduleTests
{
    public CancellationRescheduleTests()
    {
        QueueService.ResetStateForTests();
        WalkInBookingService.ResetStateForTests();
        WaitlistService.ResetStateForTests();
    }

    // Helpers ---------------------------------------------------------------

    private static ILogger<T> NullLogger<T>() =>
        new LoggerFactory().CreateLogger<T>();

    private static Appointment MakeAppt(
        AppDbContext db,
        string providerName = "Dr. Smith",
        int hourOffset = 2,
        int durationMinutes = 30)
    {
        var appt = Appointment.Create(
            Guid.NewGuid(), "Test Patient", providerName,
            DateTimeOffset.UtcNow.AddHours(hourOffset), durationMinutes);
        db.Set<Appointment>().Add(appt);
        db.SaveChanges();
        db.Entry(appt).State = Microsoft.EntityFrameworkCore.EntityState.Detached;
        return appt;
    }

    private static (QueueService svc,
                    Mock<IQueueEventBroadcaster> broadcasterMock,
                    Mock<INotificationService> notificationMock,
                    AppDbContext db) BuildService()
    {
        var broadcasterMock = new Mock<IQueueEventBroadcaster>();
        var historyMock = new Mock<IAppointmentDetailService>();
        var autoOfferMock = new Mock<IAutoOfferOrchestrator>();
        var notificationMock = new Mock<INotificationService>();
        var db = TestServiceFactory.CreateDbContext();

        autoOfferMock
            .Setup(o => o.TriggerForReleasedSlotAsync(It.IsAny<SlotReleasedEvent>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new AutoOfferTriggerResult(false, null, "no_candidates"));

        var svc = new QueueService(
            broadcasterMock.Object,
            historyMock.Object,
            autoOfferMock.Object,
            notificationMock.Object,
            db);

        return (svc, broadcasterMock, notificationMock, db);
    }

    // ==========================================================================
    // task_041_001: Cancellation state transitions
    // ==========================================================================

    [Fact]
    public async Task Cancel_ScheduledAppointment_TransitionsToCancelled()
    {
        var (svc, _, _, db) = BuildService();
        var appt = MakeAppt(db);

        var result = await svc.CancelAsync(appt.Id, "Patient request");

        Assert.Equal("cancelled", result.Status);
        Assert.Equal(appt.Id, result.AppointmentId);
    }

    [Fact]
    public async Task Cancel_AlreadyCancelled_ThrowsInvalidOperation()
    {
        var (svc, _, _, db) = BuildService();
        var appt = MakeAppt(db);

        await svc.CancelAsync(appt.Id, null);

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            svc.CancelAsync(appt.Id, null));
    }

    [Fact]
    public async Task Cancel_CompletedAppointment_ThrowsInvalidOperation()
    {
        // Simulate a completed appointment directly via domain object
        var (svc, _, _, db) = BuildService();
        var appt = Appointment.Create(Guid.NewGuid(), "Patient", "Dr. X", DateTimeOffset.UtcNow.AddHours(1));
        // Mark arrived then complete via a workaround — force status through reflection for test only
        var statusProp = typeof(Appointment).GetProperty("Status")!;
        statusProp.SetValue(appt, "completed");
        db.Set<Appointment>().Add(appt);
        db.SaveChanges();
        db.Entry(appt).State = Microsoft.EntityFrameworkCore.EntityState.Detached;

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            svc.CancelAsync(appt.Id, null));
    }

    // ==========================================================================
    // task_041_003: SSE broadcast on cancellation
    // ==========================================================================

    [Fact]
    public async Task Cancel_BroadcastsRemovedEvent()
    {
        var (svc, broadcasterMock, _, db) = BuildService();
        var appt = MakeAppt(db);

        await svc.CancelAsync(appt.Id, null);

        broadcasterMock.Verify(
            b => b.Publish(It.Is<QueueEvent>(e => e.EventType == QueueEventType.Removed)),
            Times.Once);
    }

    [Fact]
    public async Task Reschedule_BroadcastsUpdatedEvent()
    {
        var (svc, broadcasterMock, _, db) = BuildService();
        var appt = MakeAppt(db, hourOffset: 5);

        var newTime = appt.AppointmentTime.AddHours(3);
        await svc.RescheduleAsync(new RescheduleRequest(appt.Id, newTime, 30, null));

        broadcasterMock.Verify(
            b => b.Publish(It.Is<QueueEvent>(e => e.EventType == QueueEventType.Updated)),
            Times.Once);
    }

    // ==========================================================================
    // task_041_005: Notifications dispatched
    // ==========================================================================

    [Fact]
    public async Task Cancel_SendsCancellationNotification()
    {
        var (svc, _, notificationMock, db) = BuildService();
        var appt = MakeAppt(db);

        await svc.CancelAsync(appt.Id, "Test reason");

        notificationMock.Verify(
            n => n.NotifyCancellationAsync(
                It.Is<AppointmentChangeNotification>(n =>
                    n.ChangeType == AppointmentChangeType.Cancelled &&
                    n.AppointmentId == appt.Id),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [Fact]
    public async Task Reschedule_SendsRescheduleNotification()
    {
        var (svc, _, notificationMock, db) = BuildService();
        var appt = MakeAppt(db, hourOffset: 6);

        var newTime = appt.AppointmentTime.AddHours(2);
        await svc.RescheduleAsync(new RescheduleRequest(appt.Id, newTime, 30, null));

        notificationMock.Verify(
            n => n.NotifyRescheduleAsync(
                It.Is<AppointmentChangeNotification>(n =>
                    n.ChangeType == AppointmentChangeType.Rescheduled &&
                    n.AppointmentId == appt.Id &&
                    n.NewAppointmentTime == newTime),
                It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // ==========================================================================
    // task_041_002: Reschedule slot conflict validation
    // ==========================================================================

    [Fact]
    public async Task Reschedule_WithNoConflict_Succeeds()
    {
        var provider = $"Dr.ConflictTest-{Guid.NewGuid():N}";
        var (svc, _, _, db) = BuildService();
        var appt = MakeAppt(db, providerName: provider, hourOffset: 10);

        // Schedule to a slot 4 hours away — no conflict
        var newTime = DateTimeOffset.UtcNow.AddHours(14);
        var row = await svc.RescheduleAsync(new RescheduleRequest(appt.Id, newTime, 30, null));

        Assert.Equal(newTime, row.AppointmentTime);
    }

    [Fact]
    public async Task Reschedule_WhenConflictExists_ThrowsInvalidOperation()
    {
        var provider = $"Dr.ConflictTest-{Guid.NewGuid():N}";
        var (svc, _, _, db) = BuildService();

        // Two appointments for the same provider 30 minutes apart
        var appt1 = MakeAppt(db, providerName: provider, hourOffset: 20);
        var appt2 = MakeAppt(db, providerName: provider, hourOffset: 21);

        // Try to reschedule appt1 to overlap with appt2 (same start time)
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            svc.RescheduleAsync(new RescheduleRequest(
                appt1.Id,
                appt2.AppointmentTime, // exact overlap
                30, null)));
    }

    // ==========================================================================
    // NotificationService: delivery log audit (task_041_005)
    // ==========================================================================

    [Fact]
    public async Task NotificationService_RecordsDeliveryForBothRecipients()
    {
        var service = new NotificationService(NullLogger<NotificationService>());
        var apptId = Guid.NewGuid();
        var notification = new AppointmentChangeNotification(
            apptId, "Jane Doe", "Dr. Provider",
            AppointmentChangeType.Cancelled,
            DateTimeOffset.UtcNow.AddHours(-1), null, "test reason");

        await service.NotifyCancellationAsync(notification);

        var log = service.GetDeliveryLog(apptId);

        Assert.Equal(2, log.Count); // patient + provider
        Assert.Contains(log, r => r.RecipientType == "patient" && r.Delivered);
        Assert.Contains(log, r => r.RecipientType == "provider" && r.Delivered);
    }

    [Fact]
    public async Task NotificationService_RescheduleRecordsNewTimeDetails()
    {
        var service = new NotificationService(NullLogger<NotificationService>());
        var apptId = Guid.NewGuid();
        var oldTime = DateTimeOffset.UtcNow.AddHours(1);
        var newTime = DateTimeOffset.UtcNow.AddHours(3);

        var notification = new AppointmentChangeNotification(
            apptId, "Bob Smith", "Dr. Jones",
            AppointmentChangeType.Rescheduled,
            OldAppointmentTime: oldTime,
            NewAppointmentTime: newTime,
            Reason: null);

        await service.NotifyRescheduleAsync(notification);

        var log = service.GetDeliveryLog(apptId);

        Assert.Equal(2, log.Count);
        Assert.All(log, r => Assert.Equal(AppointmentChangeType.Rescheduled, r.ChangeType));
    }
}

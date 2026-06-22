# FALL-1: Non-Critical Dependency Fallback Guidelines

**Status:** Published  
**Version:** 1.0  
**Date:** 2026-06-22  
**Audience:** Backend engineers, platform architects

---

## 1. Overview

This document defines fallback patterns for graceful degradation when non-critical dependencies fail, ensuring core booking workflows remain available under partial outages.

**Principles:**
- Core booking path must never fail due to non-critical dependency outage
- Degrade gracefully, not catastrophically
- Fallback behavior is predictable and documented
- Users are informed when degraded

---

## 2. Dependency Classification

### 2.1 Critical vs Non-Critical

| Dependency | Classification | If Fails | Action |
|---|---|---|---|
| **Booking Database** | 🔴 CRITICAL | No fallback | Fail request (unfallback-able) |
| **User Authentication** | 🔴 CRITICAL | No fallback | Reject request (auth required) |
| **Payment Processor** | 🔴 CRITICAL | No fallback | Fail transaction (money at stake) |
| **Search Service** | 🟡 NON-CRITICAL | Return empty results | Fallback to browse all |
| **Recommendation Engine** | 🟡 NON-CRITICAL | Skip recommendations | Show list without suggestions |
| **Notification Service** | 🟡 NON-CRITICAL | Skip notification | Retry async, don't block |
| **Analytics** | 🟡 NON-CRITICAL | Skip event | Log for later retry |
| **Appointment Reminders** | 🟡 NON-CRITICAL | Skip reminder | Queue for batch retry |

---

## 3. Fallback Patterns

### 3.1 Return Empty/Default Value

**Use case:** Search service down

```csharp
public async Task<List<Appointment>> SearchAppointments(string query)
{
    try
    {
        return await _searchService.Query(query);
    }
    catch (SearchServiceException)
    {
        _logger.LogWarning("Search service unavailable, returning empty results");
        _telemetry.TrackFallback("SearchService");
        
        // Fallback: return empty instead of failing
        return new List<Appointment>();
    }
}
```

**User impact:** Search feature temporarily unavailable, users can browse

### 3.2 Use Cached/Stale Data

**Use case:** Recommendation engine down

```typescript
async function getRecommendedSlots(appointmentId: string): Promise<Slot[]> {
  try {
    return await recommendationEngine.getTopSlots(appointmentId, { limit: 5 });
  } catch (error) {
    logger.warn(`Recommendation service failed: ${error.message}`);
    telemetry.trackFallback('RecommendationEngine');
    
    // Fallback: return cached recommendations from 1 hour ago
    const cachedRecs = await cache.get(`recs:${appointmentId}`);
    if (cachedRecs) {
      return cachedRecs;
    }
    
    // If no cache, return empty
    return [];
  }
}
```

**User impact:** Recommendations may be stale, better than nothing

### 3.3 Queue for Async Retry

**Use case:** Notification service down

```python
async def send_notification(appointment_id: str, user_id: str):
    try:
        await notification_service.send_appointment_confirmation(
            user_id=user_id,
            appointment_id=appointment_id
        )
    except NotificationServiceException as e:
        logger.warning(f"Notification failed: {str(e)}")
        telemetry.track_fallback('NotificationService')
        
        # Fallback: queue for retry
        await retry_queue.push({
            'type': 'notification',
            'user_id': user_id,
            'appointment_id': appointment_id,
            'attempt': 1,
            'retry_after': datetime.now() + timedelta(minutes=5)
        })
        
        # Don't block booking creation
        return
```

**User impact:** Notification delayed but not lost, booking still created

### 3.4 Simplified/Fallback Logic

**Use case:** Availability calculation service down

```csharp
public async Task<bool> IsSlotAvailable(string slotId)
{
    try
    {
        // Normal path: complex availability check
        var result = await _availabilityEngine.CheckComplex(slotId);
        return result.IsAvailable;
    }
    catch (AvailabilityEngineException)
    {
        _logger.LogWarning("Availability engine down, using simple check");
        _telemetry.TrackFallback("AvailabilityEngine");
        
        // Fallback: simple check from database
        var slot = await _db.Slots.FirstOrDefaultAsync(s => s.Id == slotId);
        return slot?.BookedCount < slot?.Capacity;
    }
}
```

**User impact:** Simplified availability logic, may miss edge cases but mostly works

---

## 4. Core Booking Path Resilience

### 4.1 Booking Journey - Must Succeed

```
POST /appointments (create booking)
  ├─ Authenticate user        [🔴 CRITICAL - no fallback]
  ├─ Check availability       [🔴 CRITICAL - no fallback]
  ├─ Create booking record    [🔴 CRITICAL - no fallback]
  ├─ Process payment          [🔴 CRITICAL - no fallback]
  ├─ Send confirmation email  [🟡 NON-CRITICAL - queue for retry]
  ├─ Update analytics         [🟡 NON-CRITICAL - skip if unavailable]
  └─ Send push notification   [🟡 NON-CRITICAL - queue for retry]
  
Result: ✅ Booking created (even if notif service down)
```

### 4.2 List Appointments - Degrade Gracefully

```
GET /appointments
  ├─ Fetch appointments       [🔴 CRITICAL - no fallback]
  ├─ Enrich with slots        [🟡 NON-CRITICAL - skip enrichment]
  ├─ Add recommendations      [🟡 NON-CRITICAL - skip recommendations]
  └─ Include analytics        [🟡 NON-CRITICAL - skip analytics]
  
Result: ✅ Appointments returned (with fewer fields)
```

### 4.3 Confirm Appointment - Strict but Recoverable

```
POST /appointments/{id}/confirm
  ├─ Authenticate user        [🔴 CRITICAL - no fallback]
  ├─ Fetch appointment        [🔴 CRITICAL - no fallback]
  ├─ Update status            [🔴 CRITICAL - no fallback]
  ├─ Reserve resource         [🔴 CRITICAL - no fallback]
  ├─ Process payment          [🔴 CRITICAL - no fallback]
  └─ Send notification        [🟡 NON-CRITICAL - queue for retry]
  
Result: ✅ Confirmed (even if notification delayed)
```

---

## 5. Fallback Configuration

### 5.1 Configuration Template

```yaml
Fallbacks:
  SearchService:
    IsNonCritical: true
    FallbackBehavior: ReturnEmpty
    RetryQueue: false
    
  RecommendationEngine:
    IsNonCritical: true
    FallbackBehavior: UseCachedData
    CacheMaxAge: 3600          # 1 hour
    RetryQueue: false
    
  NotificationService:
    IsNonCritical: true
    FallbackBehavior: QueueForRetry
    RetryQueueName: notification_retry
    MaxRetries: 5
    RetryIntervalMs: 300000     # 5 minutes
    
  AnalyticsService:
    IsNonCritical: true
    FallbackBehavior: Skip
    LogForDebug: true
```

---

## 6. Testing Fallback Behavior

### 6.1 Unit Test - Fallback on Failure

```csharp
[TestMethod]
public async Task SearchAppointments_SearchServiceDown_ReturnEmpty()
{
    var searchServiceMock = new Mock<ISearchService>();
    searchServiceMock
        .Setup(s => s.Query(It.IsAny<string>()))
        .ThrowsAsync(new SearchServiceException());
    
    var service = new AppointmentService(searchServiceMock.Object);
    
    var result = await service.SearchAppointments("test");
    
    Assert.IsNotNull(result);
    Assert.AreEqual(0, result.Count);
}
```

### 6.2 Integration Test - Core Path Succeeds with Fallback

```typescript
describe('Booking resilience', () => {
  it('should create booking even if notification service down', async () => {
    // Mock notification service to fail
    mockNotificationService.send.mockRejectedValue(
      new Error('Notification service unavailable')
    );
    
    const booking = await bookingService.createBooking({
      userId: 'user123',
      slotId: 'slot456',
      notes: 'Test booking'
    });
    
    expect(booking).toBeDefined();
    expect(booking.id).toBeTruthy();
    expect(booking.status).toBe('confirmed');
    
    // Verify notification was queued for retry
    const queuedItems = await retryQueue.getItems('notification');
    expect(queuedItems.length).toBe(1);
    expect(queuedItems[0].appointmentId).toBe(booking.id);
  });
});
```

### 6.3 Chaos Test - Dependency Failure Injection

```python
async def test_booking_creation_with_email_down():
    """Simulate email service down during booking creation."""
    
    # Inject failure
    with patch('email_service.send') as mock_email:
        mock_email.side_effect = Exception("Email service down")
        
        # Create booking should still succeed
        booking = await booking_service.create_booking({
            'user_id': 'user123',
            'slot_id': 'slot456'
        })
        
        assert booking is not None
        assert booking['id']
        assert booking['status'] == 'confirmed'
        
        # Verify email was queued for retry
        queued_emails = await email_retry_queue.get_pending()
        assert len(queued_emails) == 1
        assert queued_emails[0]['booking_id'] == booking['id']
```

---

## 7. Success Criteria

- [ ] Non-critical dependencies identified and documented
- [ ] Fallback patterns defined for each non-critical dependency
- [ ] Core booking path has NO non-critical dependencies
- [ ] Graceful degradation tested and validated
- [ ] User messaging handles degraded state
- [ ] Async retry queues operational for delayed operations
- [ ] Unit/integration tests validate fallback behavior
- [ ] Documentation published for engineers

---

## References

- Resilience4J Fallback: https://resilience4j.readme.io/docs/getting-started
- Circuit Breaker with Fallback: https://martinfowler.com/bliki/CircuitBreaker.html

**Next:** [FALL-2: Override Governance](fall-override-governance.md)

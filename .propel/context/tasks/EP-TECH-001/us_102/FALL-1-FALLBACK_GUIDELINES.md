# FALL-1: Non-Critical Dependency Fallback Guidelines

**Document ID**: FALL-1  
**Acceptance Criteria**: AC-5  
**Last Updated**: 2026-06-22  
**Status**: Active

---

## Overview

This policy defines fallback patterns for when non-critical dependencies fail. The goal is to keep the core booking workflow available even when non-essential services are degraded or unavailable.

---

## 1. Critical vs Non-Critical Services

### 1.1 Critical Services (Must Never Fallback)

Services that are **part of the core booking path**:

```yaml
critical_services:
  - name: "appointment_database"
    reason: "Core booking data storage"
    fallback_available: false
  
  - name: "availability_engine"
    reason: "Check appointment availability"
    fallback_available: false
  
  - name: "payment_processor"
    reason: "Process payments for bookings"
    fallback_available: false
```

**Behavior when critical service fails**:
- Circuit breaker opens
- User sees error message
- Booking transaction fails
- No fallback; system degrades

### 1.2 Non-Critical Services (Fallback Available)

Services that **enhance** the core booking but aren't required:

```yaml
non_critical_services:
  - name: "sms_notifications"
    reason: "Send confirmation SMS"
    fallback: "queue_for_async_retry"
    degradation: "Notification delayed; user still books"
  
  - name: "recommendation_engine"
    reason: "Suggest related services"
    fallback: "return_empty_suggestions"
    degradation: "No suggestions shown; booking unaffected"
  
  - name: "analytics_service"
    reason: "Track booking events"
    fallback: "skip_tracking"
    degradation: "Metrics not recorded; booking works"
  
  - name: "rating_service"
    reason: "Show provider ratings"
    fallback: "return_cached_ratings"
    degradation: "Stale ratings shown; booking unaffected"
```

---

## 2. Fallback Patterns

### 2.1 Pattern: Return Cached Data

**When**: Service is down but we have recent cached value

```python
def get_provider_ratings(provider_id: str) -> dict:
    """Get provider ratings, fallback to cache if service down."""
    try:
        # Try to get fresh ratings
        return rating_service.get(provider_id)
    except (TimeoutError, ServiceUnavailableError):
        # Fallback to cached ratings
        cached = cache.get(f"ratings:{provider_id}")
        if cached:
            log.warning(f"Using cached ratings for {provider_id}")
            return cached
        else:
            # No cache available; return neutral
            return {"rating": 5.0, "count": 0, "cached": True}
```

**Best for**: Read-heavy operations, non-time-critical data

---

### 2.2 Pattern: Queue for Async Retry

**When**: Operation is important but can be done later

```python
def send_booking_confirmation(booking_id: str) -> None:
    """Send confirmation SMS, queue for retry if service down."""
    try:
        sms_service.send(booking_id)
    except (TimeoutError, ServiceUnavailableError):
        # Queue for later retry
        async_queue.enqueue(
            "send_sms_confirmation",
            booking_id=booking_id,
            retry_count=0,
            retry_until="2026-06-24"  # 48 hours
        )
        log.warning(f"Queued SMS for booking {booking_id}")
```

**Best for**: Notifications, follow-up actions, non-blocking operations

---

### 2.3 Pattern: Return Empty/Default

**When**: Service provides optional data only

```python
def get_recommendations(booking_id: str) -> list:
    """Get recommendations, return empty if service down."""
    try:
        return recommendations.get(booking_id)
    except (TimeoutError, ServiceUnavailableError):
        log.warning("Recommendations unavailable; returning empty")
        return []  # Empty list instead of error
```

**Best for**: Optional features, suggestions, non-essential data

---

### 2.4 Pattern: Graceful Degradation

**When**: Can provide reduced functionality

```python
def search_appointments(query: dict, include_advanced_filters: bool = True) -> list:
    """Search appointments, disable advanced filters if service down."""
    try:
        if include_advanced_filters:
            # Try advanced search
            return advanced_search_service.search(query)
        else:
            # Use basic search
            return basic_search_engine.search(query)
    except (TimeoutError, ServiceUnavailableError):
        # Fallback to basic search
        log.warning("Advanced search unavailable; using basic search")
        return basic_search_engine.search(query)
```

**Best for**: Features with basic/advanced modes

---

## 3. Booking Path Continuity

### 3.1 Booking Completion Flow

```
User requests booking
    ↓
1. Check availability (CRITICAL) → must succeed
    ↓
2. Validate payment info (CRITICAL) → must succeed
    ↓
3. Process payment (CRITICAL) → must succeed
    ↓
4. Create appointment (CRITICAL) → must succeed
    ↓
5. Send confirmation SMS (NON-CRITICAL) → fallback: queue
    ├─ SUCCESS → User gets SMS
    └─ FAIL → Queue for retry
    ↓
6. Log analytics (NON-CRITICAL) → fallback: skip
    ├─ SUCCESS → Metrics recorded
    └─ FAIL → No metrics (booking still works)
    ↓
7. Send recommendations (NON-CRITICAL) → fallback: empty
    ├─ SUCCESS → Show recommendations
    └─ FAIL → Show no recommendations (booking still works)
    ↓
✅ Booking complete (even if 5, 6, 7 failed)
```

### 3.2 Failure Scenarios

**Scenario 1: SMS service fails**
```
Booking succeeds → SMS not sent → Queued for retry
User sees: ✅ Booking confirmed! (we'll send SMS)
Backend: SMS queued; will retry for 48 hours
Result: User still has booking; SMS sent later
```

**Scenario 2: Payment service fails**
```
Booking attempted → Payment fails → ❌ Circuit opens
User sees: ❌ Payment processing failed. Please try again.
Backend: No booking created; circuit breaker open
Result: User must retry; no fallback (critical path)
```

**Scenario 3: Availability service fails**
```
User requests dates → Availability check fails → ❌ Error
User sees: ❌ Unable to check availability. Try again.
Backend: Can't proceed without availability check (critical)
Result: Core workflow blocked; no fallback
```

---

## 4. Fallback Configuration

### 4.1 Service Fallback Rules

```yaml
fallback_policies:
  - service: "sms_notifications"
    criticality: "non_critical"
    fallback_strategy: "queue_and_retry"
    queue_ttl_hours: 48
    max_retries: 10
    
  - service: "recommendations"
    criticality: "non_critical"
    fallback_strategy: "return_empty"
    
  - service: "analytics"
    criticality: "non_critical"
    fallback_strategy: "skip_operation"
    
  - service: "ratings_cache"
    criticality: "non_critical"
    fallback_strategy: "cached_data"
    cache_max_age_hours: 24
    
  - service: "appointment_database"
    criticality: "critical"
    fallback_strategy: "none"
    
  - service: "payment_processor"
    criticality: "critical"
    fallback_strategy: "none"
```

### 4.2 Per-Endpoint Fallback

```yaml
endpoint_fallbacks:
  - endpoint: "POST /bookings"
    critical_steps: [
      "check_availability",
      "validate_payment",
      "process_payment",
      "create_appointment"
    ]
    fallback_steps: [
      "send_sms",        # Fallback: queue
      "log_analytics",   # Fallback: skip
      "get_recommendations"  # Fallback: empty
    ]
```

---

## 5. Async Queue Configuration

### 5.1 Queue Settings

```yaml
async_queue:
  - name: "sms_notifications"
    backend: "redis"  # or "rabbitmq", "sqs"
    ttl_seconds: 172800  # 48 hours
    max_retries: 10
    backoff_strategy: "exponential"  # 1s, 2s, 4s, ...
    dead_letter_queue: "sms_notifications_dlq"
  
  - name: "email_notifications"
    backend: "redis"
    ttl_seconds: 604800  # 7 days
    max_retries: 20
    backoff_strategy: "exponential"
    dead_letter_queue: "email_notifications_dlq"
```

### 5.2 Queue Monitoring

```yaml
queue_alerts:
  - queue: "sms_notifications"
    alert_if_size_exceeds: 10000  # More than 10k pending
    alert_if_age_exceeds_hours: 24  # Message pending >24hrs
    severity: "WARNING"
    action: "page_on_call"
```

---

## 6. Monitoring Fallback Activations

### 6.1 Metrics

```
- fallback_activations_per_minute (how often fallbacks triggered)
- fallback_type (queue, cache, empty, skip)
- fallback_service (which service triggered fallback)
- booking_completion_despite_fallback (bookings still complete)
```

### 6.2 Alerts

**Alert: High fallback activation rate**
- Threshold: > 100 fallback activations per minute
- Severity: WARNING
- Action: Investigate which service is failing

**Alert: Async queue growing**
- Threshold: Queue size > 50,000
- Severity: CRITICAL
- Action: Page on-call; restart queue processor

---

## 7. Recovery from Fallback

### 7.1 Processing Queued Operations

When service recovers:

```python
async def process_queued_sms():
    """Process SMS messages queued during service outage."""
    while True:
        message = queue.get_next()
        if not message:
            break
        
        try:
            sms_service.send(message)
            queue.mark_processed(message)
        except Exception as e:
            # Retry on next run
            queue.increment_retry_count(message)
            if queue.retry_count(message) >= MAX_RETRIES:
                queue.send_to_dlq(message)
```

### 7.2 Verifying Completeness

After recovery, verify queued operations were processed:

```python
def verify_queued_operations_processed():
    """Alert if queued operations aren't being processed."""
    oldest_message_age = queue.get_oldest_message_age()
    
    if oldest_message_age > timedelta(hours=1):
        log.error(f"Oldest queued SMS is {oldest_message_age} old")
        alert("Queued operations not being processed")
```

---

## 8. Booking Continuity Test

### 8.1 Test Scenario

```python
def test_booking_completes_with_sms_failure():
    """Verify booking succeeds even if SMS fails."""
    with mock_sms_service_down():
        # User requests booking
        response = client.post("/bookings", json={
            "provider_id": 123,
            "date": "2026-06-23",
            "time": "10:00"
        })
        
        # Booking succeeds despite SMS failure
        assert response.status_code == 201
        assert response.json()["id"] > 0
        
        # SMS was queued for retry
        queued_sms = queue.get_messages_for_booking(response.json()["id"])
        assert len(queued_sms) == 1
```

---

## 9. Related Documents

- RES-1: Timeouts (trigger for fallbacks)
- RES-3: Circuit breaker (determines when to activate fallback)
- FALL-2: Override governance (approving critical/non-critical classification changes)

---

**Document Owner**: Infrastructure Team  
**Last Review**: 2026-06-22  
**Next Review**: 2026-09-22

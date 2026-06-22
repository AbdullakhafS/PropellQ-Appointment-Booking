"""
Log Query Builder and Search Experience

Implements SEARCH-1 and DOC-1:
- SEARCH-1: Query and timeline experience for incident debugging
- AC-2: Cross-service events discoverable by correlation ID
- AC-5: Incident search supports service/env/severity/correlation filters
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass


class TimelineEventType(Enum):
    """Types of events in a correlation timeline."""
    REQUEST_START = "request_start"
    REQUEST_END = "request_end"
    SERVICE_CALL = "service_call"
    DATABASE_QUERY = "database_query"
    ERROR = "error"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    ASYNC_TASK = "async_task"


@dataclass
class TimelineEvent:
    """Single event in a request correlation timeline (AC-2)."""
    
    timestamp: datetime
    event_type: TimelineEventType
    service_name: str
    correlation_id: str
    parent_id: Optional[str]
    
    # Context
    actor: Optional[str]
    route: Optional[str]
    status: Optional[str]  # "success", "failure", etc.
    http_status: Optional[int]
    
    # Details
    message: str
    duration_ms: Optional[float]
    details: Dict[str, Any]
    
    severity: str  # "ERROR", "WARNING", "INFO", "DEBUG"


class QueryBuilder:
    """
    Fluent builder for constructing log queries (SEARCH-1, AC-5).
    
    Supports filtering by:
    - correlation_id: End-to-end tracing
    - service: Service identifier
    - environment: Production/staging/development
    - severity: ERROR, WARNING, INFO, DEBUG
    - time_range: Start and end timestamps
    - route: HTTP path or operation name
    - status: success/failure
    """
    
    def __init__(self):
        """Initialize query builder."""
        self.filters: Dict[str, Any] = {}
        self.time_start: Optional[datetime] = None
        self.time_end: Optional[datetime] = None
        self.limit = 1000
        self.sort_by = "timestamp"
        self.sort_order = "desc"
    
    def with_correlation_id(self, correlation_id: str) -> "QueryBuilder":
        """
        Filter by correlation ID (AC-2).
        
        Returns all events in a request lifecycle for end-to-end tracing.
        """
        self.filters["correlation_id"] = correlation_id
        return self
    
    def with_service(self, service_name: str) -> "QueryBuilder":
        """
        Filter by service name (AC-5).
        
        Example: "appointment_service", "booking_service"
        """
        self.filters["service_name"] = service_name
        return self
    
    def with_services(self, service_names: List[str]) -> "QueryBuilder":
        """Filter by multiple services."""
        self.filters["service_name"] = {"$in": service_names}
        return self
    
    def with_environment(self, environment: str) -> "QueryBuilder":
        """
        Filter by environment (AC-5).
        
        Values: "local", "development", "staging", "production"
        """
        self.filters["environment"] = environment
        return self
    
    def with_severity(self, severity: str) -> "QueryBuilder":
        """
        Filter by severity level (AC-5).
        
        Values: "EMERGENCY", "ALERT", "CRITICAL", "ERROR",
                "WARNING", "NOTICE", "INFO", "DEBUG"
        """
        self.filters["severity"] = severity
        return self
    
    def with_severity_min(self, severity: str) -> "QueryBuilder":
        """
        Filter by minimum severity (AC-5).
        
        Returns events at or above this severity level.
        """
        severity_order = {
            "EMERGENCY": 0, "ALERT": 1, "CRITICAL": 2, "ERROR": 3,
            "WARNING": 4, "NOTICE": 5, "INFO": 6, "DEBUG": 7
        }
        min_value = severity_order.get(severity, 6)
        self.filters["severity_numeric"] = {"$lte": min_value}
        return self
    
    def with_error_only(self) -> "QueryBuilder":
        """Filter to errors and higher severity."""
        return self.with_severity_min("ERROR")
    
    def with_time_range(
        self,
        start: datetime,
        end: Optional[datetime] = None
    ) -> "QueryBuilder":
        """
        Filter by time range.
        
        Args:
            start: Start of range
            end: End of range (defaults to now)
        """
        self.time_start = start
        self.time_end = end or datetime.utcnow()
        self.filters["timestamp"] = {
            "$gte": start.isoformat(),
            "$lte": self.time_end.isoformat()
        }
        return self
    
    def with_last_minutes(self, minutes: int) -> "QueryBuilder":
        """Filter to last N minutes."""
        start = datetime.utcnow() - timedelta(minutes=minutes)
        return self.with_time_range(start)
    
    def with_last_hours(self, hours: int) -> "QueryBuilder":
        """Filter to last N hours."""
        start = datetime.utcnow() - timedelta(hours=hours)
        return self.with_time_range(start)
    
    def with_route(self, route: str) -> "QueryBuilder":
        """
        Filter by HTTP route or operation name (AC-5).
        
        Example: "/api/appointments/search"
        """
        self.filters["route"] = route
        return self
    
    def with_actor(self, actor_id: str) -> "QueryBuilder":
        """
        Filter by actor (user/service performing action).
        
        Example: "user_123", "service_booking"
        """
        self.filters["actor"] = actor_id
        return self
    
    def with_status(self, status: str) -> "QueryBuilder":
        """
        Filter by operation status (AC-5).
        
        Values: "success", "failure", "partial"
        """
        self.filters["status"] = status
        return self
    
    def with_failures_only(self) -> "QueryBuilder":
        """Filter to failed operations."""
        return self.with_status("failure")
    
    def with_limit(self, limit: int) -> "QueryBuilder":
        """Set result limit."""
        self.limit = limit
        return self
    
    def sort_by_time_asc(self) -> "QueryBuilder":
        """Sort by timestamp ascending (oldest first)."""
        self.sort_by = "timestamp"
        self.sort_order = "asc"
        return self
    
    def sort_by_time_desc(self) -> "QueryBuilder":
        """Sort by timestamp descending (newest first)."""
        self.sort_by = "timestamp"
        self.sort_order = "desc"
        return self
    
    def to_query_dict(self) -> Dict[str, Any]:
        """Convert to query dictionary for execution."""
        return {
            "filters": self.filters,
            "limit": self.limit,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order
        }


class TimelineBuilder:
    """
    Constructs event timelines for a correlation ID (AC-2, DOC-1).
    
    Timeline shows:
    - Request start/end
    - Cross-service calls
    - Database operations
    - Errors and warnings
    - Total duration
    - Critical path
    """
    
    def __init__(self, correlation_id: str):
        """Initialize timeline builder."""
        self.correlation_id = correlation_id
        self.events: List[TimelineEvent] = []
    
    def add_event(self, event: TimelineEvent) -> None:
        """Add event to timeline."""
        self.events.append(event)
    
    def build(self) -> Dict[str, Any]:
        """
        Build timeline visualization (AC-2).
        
        Returns:
            Timeline data with critical path analysis
        """
        if not self.events:
            return {
                "correlation_id": self.correlation_id,
                "events": [],
                "total_duration_ms": 0,
                "error_count": 0
            }
        
        # Sort events by timestamp
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        
        # Calculate metrics
        start_time = sorted_events[0].timestamp
        end_time = sorted_events[-1].timestamp
        total_duration = (end_time - start_time).total_seconds() * 1000
        
        error_count = sum(1 for e in sorted_events if e.severity == "ERROR")
        warning_count = sum(1 for e in sorted_events if e.severity == "WARNING")
        
        # Build timeline
        timeline_events = []
        for event in sorted_events:
            timeline_events.append({
                "timestamp": event.timestamp.isoformat(),
                "type": event.event_type.value,
                "service": event.service_name,
                "message": event.message,
                "severity": event.severity,
                "duration_ms": event.duration_ms,
                "status": event.status,
                "details": event.details
            })
        
        return {
            "correlation_id": self.correlation_id,
            "events": timeline_events,
            "total_duration_ms": total_duration,
            "error_count": error_count,
            "warning_count": warning_count,
            "event_count": len(timeline_events),
            "services_involved": list(set(e.service_name for e in sorted_events)),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }


class IncidentQuery:
    """
    Helper for common incident investigation queries (DOC-1).
    
    Provides standard queries for typical incident debugging:
    - Find all events for a request
    - Find all errors in a time window
    - Find slow requests
    - Find failed operations by service
    """
    
    @staticmethod
    def all_events_for_correlation(
        correlation_id: str
    ) -> Dict[str, Any]:
        """Get all events for a correlation ID (AC-2)."""
        return QueryBuilder()\
            .with_correlation_id(correlation_id)\
            .sort_by_time_asc()\
            .to_query_dict()
    
    @staticmethod
    def errors_in_last_hour() -> Dict[str, Any]:
        """Get all errors in the last hour (AC-5)."""
        return QueryBuilder()\
            .with_error_only()\
            .with_last_hours(1)\
            .sort_by_time_desc()\
            .to_query_dict()
    
    @staticmethod
    def service_failures(
        service_name: str,
        hours: int = 1
    ) -> Dict[str, Any]:
        """Get all failures for a service (AC-5)."""
        return QueryBuilder()\
            .with_service(service_name)\
            .with_failures_only()\
            .with_last_hours(hours)\
            .sort_by_time_desc()\
            .to_query_dict()
    
    @staticmethod
    def production_errors(minutes: int = 10) -> Dict[str, Any]:
        """Get production errors in last N minutes (AC-5)."""
        return QueryBuilder()\
            .with_environment("production")\
            .with_error_only()\
            .with_last_minutes(minutes)\
            .sort_by_time_desc()\
            .to_query_dict()
    
    @staticmethod
    def route_timeline(route: str) -> Dict[str, Any]:
        """Get timeline of requests to a route."""
        return QueryBuilder()\
            .with_route(route)\
            .with_last_hours(1)\
            .sort_by_time_desc()\
            .to_query_dict()


# Standard query templates
QUERY_TEMPLATES = {
    "correlation_id_timeline": """
    -- All events for a correlation ID (AC-2)
    SELECT * FROM logs
    WHERE correlation_id = ?
    ORDER BY timestamp ASC
    """,
    
    "service_errors": """
    -- All errors for a service (AC-5)
    SELECT * FROM logs
    WHERE service_name = ?
      AND severity IN ('ERROR', 'CRITICAL', 'ALERT')
      AND timestamp >= NOW() - INTERVAL '1 hour'
    ORDER BY timestamp DESC
    """,
    
    "slow_requests": """
    -- Requests slower than threshold (AC-5)
    SELECT correlation_id, service_name, duration_ms, message
    FROM logs
    WHERE source = 'API'
      AND duration_ms > ?
      AND environment = 'production'
      AND timestamp >= NOW() - INTERVAL '1 hour'
    ORDER BY duration_ms DESC
    LIMIT 100
    """,
    
    "error_timeline": """
    -- Error timeline for debugging (DOC-1, AC-2)
    SELECT timestamp, service_name, message, details
    FROM logs
    WHERE correlation_id = ?
      AND severity IN ('ERROR', 'CRITICAL', 'WARNING')
    ORDER BY timestamp ASC
    """,
}

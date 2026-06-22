"""
Structured Logging Schema and Correlation ID Management

Implements LOG-1 and LOG-2:
- LOG-1: Standardized JSON schema for all logs
- LOG-2: Correlation ID generation and propagation
- AC-1: Missing correlation IDs are generated
"""

from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
import json
import uuid
import re


class LogSeverity(Enum):
    """Standard log severity levels (ACM syslog order)."""
    EMERGENCY = "EMERGENCY"  # 0 - System unusable
    ALERT = "ALERT"          # 1 - Action must be taken immediately
    CRITICAL = "CRITICAL"    # 2 - Critical conditions
    ERROR = "ERROR"           # 3 - Error conditions
    WARNING = "WARNING"       # 4 - Warning conditions
    NOTICE = "NOTICE"         # 5 - Normal but significant
    INFO = "INFO"             # 6 - Informational
    DEBUG = "DEBUG"            # 7 - Debug-level messages

    def numeric_value(self) -> int:
        """Return numeric severity (lower is more severe)."""
        return {"EMERGENCY": 0, "ALERT": 1, "CRITICAL": 2, "ERROR": 3,
                "WARNING": 4, "NOTICE": 5, "INFO": 6, "DEBUG": 7}[self.value]


class LogSource(Enum):
    """Origin of log event."""
    API = "API"                    # HTTP API endpoint
    MIDDLEWARE = "MIDDLEWARE"      # Request/response middleware
    SERVICE = "SERVICE"            # Business logic service
    DATABASE = "DATABASE"          # Database operation
    CACHE = "CACHE"                # Cache operation
    SCHEDULER = "SCHEDULER"        # Scheduled task/job
    WEBHOOK = "WEBHOOK"            # Webhook handler
    ASYNC_WORKER = "ASYNC_WORKER"  # Background worker
    SYSTEM = "SYSTEM"              # System-level event


class LogEnvironment(Enum):
    """Deployment environment."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class CorrelationContext:
    """
    Correlation ID context for end-to-end request tracing.
    
    Propagates across service boundaries:
    - Synchronous calls: HTTP headers
    - Async workers: Message metadata
    - Database operations: Query context
    
    AC-1: Missing correlation IDs are generated on ingress.
    """
    correlation_id: str
    parent_id: Optional[str] = None  # For nested operations
    trace_id: Optional[str] = None   # Root trace for aggregation
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None  # HTTP request ID if applicable
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new correlation ID (UUID v4)."""
        return str(uuid.uuid4())
    
    @staticmethod
    def create_new() -> "CorrelationContext":
        """Create a new correlation context with generated ID."""
        return CorrelationContext(
            correlation_id=CorrelationContext.generate_id(),
            trace_id=CorrelationContext.generate_id()
        )
    
    @staticmethod
    def from_headers(headers: Dict[str, str]) -> "CorrelationContext":
        """
        Extract correlation context from HTTP headers.
        
        Expected headers:
        - X-Correlation-ID: Main correlation ID (required)
        - X-Parent-ID: Parent operation ID (optional)
        - X-Trace-ID: Root trace ID (optional)
        - X-User-ID: User identifier (optional)
        - X-Session-ID: Session identifier (optional)
        
        AC-1: If X-Correlation-ID missing, generate new ID.
        """
        correlation_id = headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = CorrelationContext.generate_id()
        
        return CorrelationContext(
            correlation_id=correlation_id,
            parent_id=headers.get("X-Parent-ID"),
            trace_id=headers.get("X-Trace-ID", correlation_id),
            user_id=headers.get("X-User-ID"),
            session_id=headers.get("X-Session-ID"),
            request_id=headers.get("X-Request-ID")
        )
    
    def to_headers(self) -> Dict[str, str]:
        """Convert correlation context to HTTP headers for propagation (LOG-2)."""
        headers = {
            "X-Correlation-ID": self.correlation_id,
            "X-Trace-ID": self.trace_id or self.correlation_id
        }
        if self.parent_id:
            headers["X-Parent-ID"] = self.parent_id
        if self.user_id:
            headers["X-User-ID"] = self.user_id
        if self.session_id:
            headers["X-Session-ID"] = self.session_id
        if self.request_id:
            headers["X-Request-ID"] = self.request_id
        return headers
    
    def create_child(self) -> "CorrelationContext":
        """
        Create child correlation context for nested operations (LOG-2).
        Maintains parent chain for debugging.
        """
        return CorrelationContext(
            correlation_id=CorrelationContext.generate_id(),
            parent_id=self.correlation_id,
            trace_id=self.trace_id or self.correlation_id,
            user_id=self.user_id,
            session_id=self.session_id
        )


@dataclass
class StructuredLogEntry:
    """
    Standard structured log entry (LOG-1, AC-1).
    
    Required fields ensure consistency and searchability:
    - timestamp: ISO 8601 UTC timestamp
    - correlation_id: End-to-end request tracing
    - severity: ACM syslog level
    - source: Log origin (API, SERVICE, etc.)
    - environment: Deployment environment
    
    Optional fields add context:
    - actor: User/service making the action
    - route: HTTP path or operation name
    - status: Result status (success, failure, partial)
    - http_status: HTTP status code
    - message: Human-readable summary
    - details: Additional context (dict)
    """
    
    # Required fields
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    correlation_id: str = field(default_factory=CorrelationContext.generate_id)
    severity: LogSeverity = LogSeverity.INFO
    source: LogSource = LogSource.SERVICE
    environment: LogEnvironment = LogEnvironment.DEVELOPMENT
    
    # Context fields
    actor: Optional[str] = None
    route: Optional[str] = None
    status: Optional[str] = None  # "success", "failure", "partial"
    http_status: Optional[int] = None
    
    # Message and details
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    service_name: Optional[str] = None
    instance_id: Optional[str] = None
    version: str = "1.0"
    trace_id: Optional[str] = None
    parent_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Serialize to JSON string for log shipping."""
        return json.dumps(asdict(self), default=str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        data = asdict(self)
        # Convert enums to strings
        if isinstance(self.severity, LogSeverity):
            data["severity"] = self.severity.value
        if isinstance(self.source, LogSource):
            data["source"] = self.source.value
        if isinstance(self.environment, LogEnvironment):
            data["environment"] = self.environment.value
        return data
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StructuredLogEntry":
        """Reconstruct from dictionary."""
        # Convert string enums back to enums
        if "severity" in data and isinstance(data["severity"], str):
            data["severity"] = LogSeverity[data["severity"]]
        if "source" in data and isinstance(data["source"], str):
            data["source"] = LogSource[data["source"]]
        if "environment" in data and isinstance(data["environment"], str):
            data["environment"] = LogEnvironment[data["environment"]]
        return StructuredLogEntry(**data)


@dataclass
class LogContext:
    """
    Contextual information for logging throughout a request lifecycle.
    
    Flows through middleware and service calls (LOG-2).
    """
    correlation: CorrelationContext
    service_name: str
    environment: LogEnvironment
    instance_id: Optional[str] = None
    
    def create_log_entry(
        self,
        message: str,
        severity: LogSeverity = LogSeverity.INFO,
        source: LogSource = LogSource.SERVICE,
        status: Optional[str] = None,
        http_status: Optional[int] = None,
        route: Optional[str] = None,
        actor: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> StructuredLogEntry:
        """Factory method to create log entry with context."""
        return StructuredLogEntry(
            correlation_id=self.correlation.correlation_id,
            severity=severity,
            source=source,
            environment=self.environment,
            message=message,
            service_name=self.service_name,
            instance_id=self.instance_id,
            status=status,
            http_status=http_status,
            route=route,
            actor=actor,
            details=details or {},
            trace_id=self.correlation.trace_id,
            parent_id=self.correlation.parent_id
        )


class CorrelationPropagator:
    """
    Propagates correlation IDs across service boundaries (LOG-2, AC-1).
    
    Handles:
    - Extracting from HTTP headers
    - Propagating to outbound calls
    - Attaching to async tasks
    - Passing through database connections
    """
    
    _current_context: Optional[CorrelationContext] = None
    
    @classmethod
    def get_current(cls) -> CorrelationContext:
        """Get current correlation context (thread-safe in production)."""
        if not cls._current_context:
            cls._current_context = CorrelationContext.create_new()
        return cls._current_context
    
    @classmethod
    def set_current(cls, context: CorrelationContext) -> None:
        """Set current correlation context."""
        cls._current_context = context
    
    @classmethod
    def set_from_headers(cls, headers: Dict[str, str]) -> CorrelationContext:
        """Extract and set correlation context from headers."""
        context = CorrelationContext.from_headers(headers)
        cls.set_current(context)
        return context
    
    @classmethod
    def clear(cls) -> None:
        """Clear current context."""
        cls._current_context = None


# Global log context stack (for nested operations)
_log_context_stack: list = []


def push_context(context: LogContext) -> None:
    """Push a log context onto the stack."""
    _log_context_stack.append(context)


def pop_context() -> Optional[LogContext]:
    """Pop and return the current log context."""
    if _log_context_stack:
        return _log_context_stack.pop()
    return None


def current_context() -> Optional[LogContext]:
    """Get the current log context without removing it."""
    if _log_context_stack:
        return _log_context_stack[-1]
    return None


def get_correlation_id() -> str:
    """
    Get current correlation ID.
    AC-1: Returns generated ID if none exists.
    """
    ctx = current_context()
    if ctx:
        return ctx.correlation.correlation_id
    return CorrelationPropagator.get_current().correlation_id

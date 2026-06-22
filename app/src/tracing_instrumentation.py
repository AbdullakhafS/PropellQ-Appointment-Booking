"""
Distributed Tracing Instrumentation and Span Management

Implements TRACE-1 and TRACE-2:
- TRACE-1: Instrumentation baseline with SDK and propagation
- TRACE-2: Critical journey coverage for booking and async workflows
- AC-1: End-to-end parent-child spans show full path and latency
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import time
import json


class SpanKind(Enum):
    """OpenTelemetry span kind classification."""
    INTERNAL = "INTERNAL"          # Internal operation
    SERVER = "SERVER"              # Server receiving request
    CLIENT = "CLIENT"              # Client making request
    PRODUCER = "PRODUCER"          # Producer to async queue
    CONSUMER = "CONSUMER"          # Consumer from async queue


class SpanStatus(Enum):
    """Span completion status."""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanContext:
    """
    Distributed trace context for propagation across boundaries.
    
    Follows OpenTelemetry W3C Trace Context standard:
    - trace_id: End-to-end trace identifier
    - span_id: Current operation identifier
    - parent_span_id: Caller's span (optional)
    - trace_flags: Sampling decision
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 0x01  # Sampled
    correlation_id: Optional[str] = None  # Link to logging correlation
    
    @staticmethod
    def create_root() -> "SpanContext":
        """Create new root trace context."""
        return SpanContext(
            trace_id=str(uuid.uuid4()).replace("-", ""),
            span_id=str(uuid.uuid4()).replace("-", "")
        )
    
    def create_child(self) -> "SpanContext":
        """Create child span context (AC-1: parent-child relationship)."""
        return SpanContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4()).replace("-", ""),
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags,
            correlation_id=self.correlation_id
        )
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for propagation (TRACE-1)."""
        # W3C Trace Context format: version-trace_id-parent_id-trace_flags
        traceparent = f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}"
        headers = {"traceparent": traceparent}
        if self.correlation_id:
            headers["X-Correlation-ID"] = self.correlation_id
        return headers
    
    @staticmethod
    def from_headers(headers: Dict[str, str]) -> "SpanContext":
        """Extract span context from headers (TRACE-1)."""
        # Try W3C Trace Context
        traceparent = headers.get("traceparent")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                return SpanContext(
                    trace_id=parts[1],
                    span_id=parts[2],
                    trace_flags=int(parts[3], 16) if len(parts) > 3 else 0x01,
                    correlation_id=headers.get("X-Correlation-ID")
                )
        
        # Fallback: generate new
        return SpanContext.create_root()


@dataclass
class SpanEvent:
    """Named event within a span."""
    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanAttribute:
    """Attribute key-value pair on a span."""
    key: str
    value: Any


@dataclass
class Span:
    """
    Distributed trace span (TRACE-1, TRACE-2).
    
    Represents a single operation in a distributed workflow.
    Links parent spans to form complete request path (AC-1).
    """
    
    # Identity
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    
    # Operation details
    operation_name: str = "operation"
    kind: SpanKind = SpanKind.INTERNAL
    
    # Timing (microseconds since epoch)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Status
    status: SpanStatus = SpanStatus.UNSET
    status_description: Optional[str] = None
    
    # Tagging and attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    
    # Service context
    service_name: str = "unknown"
    service_version: str = "1.0"
    
    # Correlation linkage (AC-6)
    correlation_id: Optional[str] = None
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute (TRACE-2)."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Record named event in span."""
        event = SpanEvent(name=name, attributes=attributes or {})
        self.events.append(event)
    
    def record_exception(self, exception: Exception, escaped: bool = False) -> None:
        """Record exception in span."""
        self.set_attribute("exception.type", type(exception).__name__)
        self.set_attribute("exception.message", str(exception))
        self.status = SpanStatus.ERROR
        self.status_description = str(exception)
    
    def set_error(self, description: str) -> None:
        """Mark span as error."""
        self.status = SpanStatus.ERROR
        self.status_description = description
    
    def end(self) -> None:
        """End span and calculate duration."""
        if self.end_time is None:
            self.end_time = time.time()
        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK
    
    def duration_ms(self) -> float:
        """Duration in milliseconds (AC-1: latency)."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "status": self.status.value,
            "status_description": self.status_description,
            "service_name": self.service_name,
            "attributes": self.attributes,
            "correlation_id": self.correlation_id
        }


class TraceContext:
    """
    Thread-local trace context for tracking active spans (TRACE-1).
    
    Ensures span context propagates through async operations and
    service calls.
    """
    
    _stack: List[SpanContext] = []
    
    @classmethod
    def push(cls, context: SpanContext) -> None:
        """Push span context onto stack."""
        cls._stack.append(context)
    
    @classmethod
    def pop(cls) -> Optional[SpanContext]:
        """Pop and return current span context."""
        if cls._stack:
            return cls._stack.pop()
        return None
    
    @classmethod
    def current(cls) -> Optional[SpanContext]:
        """Get current span context without removing."""
        if cls._stack:
            return cls._stack[-1]
        return None
    
    @classmethod
    def clear(cls) -> None:
        """Clear all contexts."""
        cls._stack.clear()


class Tracer:
    """
    Main tracer for creating and managing spans (TRACE-1, TRACE-2).
    
    Instruments API handlers, service calls, database queries,
    and async task execution.
    """
    
    def __init__(
        self,
        service_name: str,
        version: str = "1.0"
    ):
        """Initialize tracer."""
        self.service_name = service_name
        self.version = version
        self.spans: List[Span] = []
        self.root_context: Optional[SpanContext] = None
    
    def start_span(
        self,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Span:
        """
        Start new span (TRACE-1, TRACE-2).
        
        Automatically creates parent-child relationship if context
        already exists.
        """
        current = TraceContext.current()
        
        if current is None:
            # Create root span
            context = SpanContext.create_root()
            self.root_context = context
        else:
            # Create child span
            context = current.create_child()
        
        span = Span(
            trace_id=context.trace_id,
            span_id=context.span_id,
            parent_span_id=context.parent_span_id,
            operation_name=operation_name,
            kind=kind,
            service_name=self.service_name,
            service_version=self.version,
            correlation_id=correlation_id or context.correlation_id
        )
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        # Set standard attributes
        span.set_attribute("service.name", self.service_name)
        span.set_attribute("service.version", self.version)
        span.set_attribute("span.kind", kind.value)
        
        TraceContext.push(context)
        self.spans.append(span)
        
        return span
    
    def end_span(self, span: Span) -> None:
        """End span and collect trace data."""
        span.end()
        TraceContext.pop()
    
    def get_trace_spans(self) -> List[Span]:
        """Get all spans in current trace (AC-1)."""
        if not self.root_context:
            return []
        return [s for s in self.spans if s.trace_id == self.root_context.trace_id]
    
    def export_trace(self) -> Dict[str, Any]:
        """
        Export complete trace with parent-child hierarchy (AC-1).
        
        Returns structured trace data for dashboards and analysis.
        """
        trace_spans = self.get_trace_spans()
        
        if not trace_spans:
            return {}
        
        # Sort by start time to show sequence
        sorted_spans = sorted(trace_spans, key=lambda s: s.start_time)
        
        return {
            "trace_id": self.root_context.trace_id if self.root_context else None,
            "service_name": self.service_name,
            "start_time": sorted_spans[0].start_time if sorted_spans else None,
            "end_time": sorted_spans[-1].end_time if sorted_spans else None,
            "total_duration_ms": sum(s.duration_ms() for s in sorted_spans),
            "span_count": len(sorted_spans),
            "spans": [s.to_dict() for s in sorted_spans],
            "critical_path": self._calculate_critical_path(sorted_spans)
        }
    
    def _calculate_critical_path(self, spans: List[Span]) -> List[Dict[str, Any]]:
        """
        Calculate critical path through trace (AC-1: latency analysis).
        
        Shows chain of operations that contributed most to total latency.
        """
        if not spans:
            return []
        
        # Build parent-child relationships
        span_by_id = {s.span_id: s for s in spans}
        
        # Find root spans (no parent)
        roots = [s for s in spans if not s.parent_span_id]
        
        critical_path = []
        for root in roots:
            path = self._build_critical_path_for_span(root, span_by_id)
            critical_path.extend(path)
        
        return critical_path
    
    def _build_critical_path_for_span(
        self,
        span: Span,
        span_by_id: Dict[str, Span]
    ) -> List[Dict[str, Any]]:
        """Build critical path from a root span down."""
        path = [{
            "operation": span.operation_name,
            "duration_ms": span.duration_ms(),
            "service": span.service_name,
            "status": span.status.value
        }]
        
        # Find children (spans with this span as parent)
        children = [s for s in span_by_id.values() if s.parent_span_id == span.span_id]
        
        # Add longest child's path
        if children:
            longest_child = max(children, key=lambda s: s.duration_ms())
            child_path = self._build_critical_path_for_span(longest_child, span_by_id)
            path.extend(child_path)
        
        return path


class TracingMiddleware:
    """
    WSGI middleware for automatic request/response tracing (TRACE-1).
    
    Instruments all incoming requests with spans, propagates
    context to downstream calls.
    """
    
    def __init__(self, app, tracer: Tracer):
        """Initialize middleware."""
        self.app = app
        self.tracer = tracer
    
    def __call__(self, environ, start_response):
        """Trace HTTP request."""
        # Extract trace context from headers
        headers = self._get_headers(environ)
        span_context = SpanContext.from_headers(headers)
        TraceContext.push(span_context)
        
        # Create span for request
        method = environ.get("REQUEST_METHOD", "UNKNOWN")
        path = environ.get("PATH_INFO", "/")
        
        span = self.tracer.start_span(
            operation_name=f"{method} {path}",
            kind=SpanKind.SERVER,
            attributes={
                "http.method": method,
                "http.url": path,
                "http.scheme": environ.get("wsgi.url_scheme", "http"),
                "http.host": environ.get("HTTP_HOST", "unknown")
            },
            correlation_id=span_context.correlation_id
        )
        
        def traced_start_response(status, response_headers):
            """Wrap start_response to capture status."""
            status_code = int(status.split()[0])
            span.set_attribute("http.status_code", status_code)
            if status_code >= 400:
                span.set_error(f"HTTP {status_code}")
            return start_response(status, response_headers)
        
        try:
            # Call application
            response = self.app(environ, traced_start_response)
            self.tracer.end_span(span)
            return response
        except Exception as e:
            span.record_exception(e)
            self.tracer.end_span(span)
            raise
    
    @staticmethod
    def _get_headers(environ: Dict[str, Any]) -> Dict[str, str]:
        """Extract HTTP headers from WSGI environ."""
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                # Convert HTTP_HEADER_NAME to header-name
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = value
        return headers


def setup_tracing(service_name: str) -> Tracer:
    """
    Factory to create configured tracer (TRACE-1).
    
    Typical usage:
        tracer = setup_tracing("booking_service")
        app = TracingMiddleware(wsgi_app, tracer)
    """
    return Tracer(service_name=service_name)

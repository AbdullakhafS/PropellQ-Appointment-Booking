"""
Trace-Log Correlation and Cross-Linking

Implements TRACE-3 and LINK-1:
- TRACE-3: Correlation linkage metadata on spans
- LINK-1: Cross-link experience for trace-log pivoting
- AC-6: Trace and logs are cross-linked by correlation ID
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class TraceLogLink:
    """
    Link between trace span and log entry (AC-6).
    
    Enables navigation from trace spans to correlated logs
    and vice versa.
    """
    
    trace_id: str
    span_id: str
    correlation_id: str  # Links to logging system
    log_count: int = 0
    first_log_time: Optional[datetime] = None
    last_log_time: Optional[datetime] = None


@dataclass
class SpanWithLogs:
    """
    Span enriched with cross-linked logs (AC-6).
    
    Contains span data plus associated log entries for
    unified incident investigation.
    """
    
    # Span data
    span_id: str
    trace_id: str
    operation_name: str
    duration_ms: float
    status: str
    
    # Correlation
    correlation_id: str
    
    # Associated logs (by correlation)
    logs: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.logs is None:
            self.logs = []


class TraceLinkRegistry:
    """
    Registry mapping traces to logs via correlation IDs (LINK-1, AC-6).
    
    Enables bidirectional navigation between traces and logs.
    """
    
    def __init__(self):
        """Initialize registry."""
        # Maps correlation_id -> trace_ids
        self.correlation_to_traces: Dict[str, List[str]] = {}
        # Maps trace_id -> correlation_id
        self.trace_to_correlation: Dict[str, str] = {}
        # Maps correlation_id -> log_entries
        self.correlation_to_logs: Dict[str, List[Dict[str, Any]]] = {}
    
    def register_trace(
        self,
        trace_id: str,
        correlation_id: str
    ) -> None:
        """
        Register trace with correlation ID (TRACE-3, AC-6).
        
        Creates bidirectional mappings for cross-linking.
        """
        self.trace_to_correlation[trace_id] = correlation_id
        
        if correlation_id not in self.correlation_to_traces:
            self.correlation_to_traces[correlation_id] = []
        
        if trace_id not in self.correlation_to_traces[correlation_id]:
            self.correlation_to_traces[correlation_id].append(trace_id)
    
    def register_log(
        self,
        correlation_id: str,
        log_entry: Dict[str, Any]
    ) -> None:
        """
        Register log entry with correlation ID (LINK-1, AC-6).
        
        Makes log discoverable from trace.
        """
        if correlation_id not in self.correlation_to_logs:
            self.correlation_to_logs[correlation_id] = []
        
        self.correlation_to_logs[correlation_id].append(log_entry)
    
    def get_logs_for_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all logs for a trace (AC-6).
        
        Enables trace → logs navigation.
        """
        correlation_id = self.trace_to_correlation.get(trace_id)
        if not correlation_id:
            return []
        
        return self.correlation_to_logs.get(correlation_id, [])
    
    def get_traces_for_correlation(self, correlation_id: str) -> List[str]:
        """
        Get all traces for a correlation ID (AC-6).
        
        Enables logs → traces navigation.
        """
        return self.correlation_to_traces.get(correlation_id, [])
    
    def get_trace_with_logs(
        self,
        span_data: Dict[str, Any]
    ) -> SpanWithLogs:
        """
        Get span enriched with cross-linked logs (AC-6).
        
        Used for unified incident investigation views.
        """
        trace_id = span_data.get("trace_id")
        correlation_id = span_data.get("correlation_id")
        
        logs = []
        if correlation_id:
            logs = self.correlation_to_logs.get(correlation_id, [])
        
        return SpanWithLogs(
            span_id=span_data.get("span_id"),
            trace_id=trace_id,
            operation_name=span_data.get("operation_name"),
            duration_ms=span_data.get("duration_ms", 0),
            status=span_data.get("status"),
            correlation_id=correlation_id,
            logs=logs
        )


class TraceLogNavigator:
    """
    Enables navigation between traces and logs (LINK-1, AC-6).
    
    Used by incident response dashboards and investigation tools
    to pivot between distributed trace data and centralized logs.
    """
    
    def __init__(self, registry: TraceLinkRegistry):
        """Initialize navigator."""
        self.registry = registry
    
    def investigate_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Get investigation view for a trace (AC-6).
        
        Combines trace spans with correlated logs.
        """
        correlation_id = self.registry.trace_to_correlation.get(trace_id)
        logs = self.registry.get_logs_for_trace(trace_id)
        
        return {
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "log_count": len(logs),
            "logs": logs,
            "navigation_url": f"/traces/{trace_id}/logs",
            "export_url": f"/traces/{trace_id}/export"
        }
    
    def investigate_logs(self, correlation_id: str) -> Dict[str, Any]:
        """
        Get investigation view for correlated logs (AC-6).
        
        Shows all traces related to correlation ID.
        """
        logs = self.registry.correlation_to_logs.get(correlation_id, [])
        traces = self.registry.get_traces_for_correlation(correlation_id)
        
        return {
            "correlation_id": correlation_id,
            "log_count": len(logs),
            "trace_count": len(traces),
            "traces": traces,
            "logs": logs,
            "navigation_url": f"/logs/{correlation_id}/traces",
            "export_url": f"/logs/{correlation_id}/export"
        }
    
    def create_investigation_report(
        self,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Create unified incident investigation report (AC-6, DOC-1).
        
        Combines traces, logs, and timeline for incident response.
        """
        logs = self.registry.correlation_to_logs.get(correlation_id, [])
        traces = self.registry.get_traces_for_correlation(correlation_id)
        
        # Analyze logs
        errors = [l for l in logs if l.get("severity") in ["ERROR", "CRITICAL"]]
        first_log = min(logs, key=lambda x: x.get("timestamp", "")) if logs else None
        last_log = max(logs, key=lambda x: x.get("timestamp", "")) if logs else None
        
        return {
            "correlation_id": correlation_id,
            "incident_summary": {
                "trace_count": len(traces),
                "log_count": len(logs),
                "error_count": len(errors),
                "duration": "See timeline below"
            },
            "traces": traces,
            "log_timeline": logs,
            "errors": errors,
            "critical_events": self._extract_critical_events(logs),
            "investigation_checkpoints": [
                f"1. Review error logs: {len(errors)} errors found",
                f"2. Check trace spans: {len(traces)} traces involved",
                f"3. Analyze critical path from traces",
                f"4. Cross-reference timing between traces and logs"
            ]
        }
    
    @staticmethod
    def _extract_critical_events(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract critical events from logs for report."""
        critical = []
        for log in logs:
            if log.get("severity") in ["ERROR", "CRITICAL", "ALERT"]:
                critical.append({
                    "timestamp": log.get("timestamp"),
                    "service": log.get("service_name"),
                    "message": log.get("message"),
                    "severity": log.get("severity")
                })
        return critical

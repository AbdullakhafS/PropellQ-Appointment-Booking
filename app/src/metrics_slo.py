"""
Metrics Collection and SLO Management

Implements METRIC-1 and SLO-1:
- METRIC-1: Golden signal metric extraction (latency, availability, error-rate)
- SLO-1: SLO and error budget definition
- AC-2: p95 latency/error metrics visible per critical endpoint
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"           # Monotonically increasing value
    GAUGE = "gauge"               # Point-in-time value
    HISTOGRAM = "histogram"       # Distribution of values
    SUMMARY = "summary"           # Summary statistics


@dataclass
class Percentile:
    """Percentile value from distribution."""
    percentile: float  # e.g., 0.95 for p95
    value: float


@dataclass
class MetricDataPoint:
    """Single metric measurement."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class GoldenSignal:
    """
    Golden signal metrics (latency, availability, errors).
    
    From Google SRE book:
    - Latency: How long it takes to serve requests
    - Traffic: How much demand is being placed on service
    - Errors: Rate of requests that fail
    - Saturation: How full the service is
    """
    
    # Latency (milliseconds)
    latency_mean: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0   # AC-2: Required metric
    latency_p99: float = 0.0
    
    # Availability
    request_count: int = 0
    error_count: int = 0
    success_rate: float = 1.0  # 0-1
    availability: float = 1.0  # 0-1 (uptime)
    
    # Traffic
    request_rate: float = 0.0  # Requests per second
    
    def error_rate(self) -> float:
        """Calculate error rate (AC-2)."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


@dataclass
class SLOTarget:
    """SLO (Service Level Objective) target definition (SLO-1)."""
    
    name: str
    description: str
    metric_type: str  # "latency", "availability", "error_rate"
    target_value: float  # e.g., 99.9 for 99.9% availability
    window_seconds: int  # Measurement window (e.g., 30*24*3600 for monthly)
    severity: str = "HIGH"  # Alert severity if violated
    
    def error_budget_seconds(self) -> float:
        """
        Calculate total error budget for window (SLO-1).
        
        If SLO is 99.9% availability over 30 days:
        Error budget = 0.1% * 30 days = 43.2 minutes
        """
        if self.metric_type == "availability":
            # availability target is 0-1 (e.g., 0.999)
            error_fraction = 1.0 - self.target_value
            return error_fraction * self.window_seconds
        return 0.0
    
    def error_budget_remaining(self, actual_errors: int, actual_seconds: int) -> float:
        """
        Calculate remaining error budget.
        
        If we're halfway through month and already spent half budget,
        remaining is 0.
        """
        budget = self.error_budget_seconds()
        spent = (actual_errors / 100.0) * actual_seconds if actual_errors > 0 else 0
        return max(0.0, budget - spent)
    
    def burn_rate(self, errors_in_window: int, total_requests: int) -> float:
        """
        Calculate how fast error budget is being consumed (SLO-1).
        
        Burn rate 1.0 = consuming error budget at expected rate
        Burn rate 2.0 = consuming at 2x the expected rate (alert!)
        """
        if total_requests == 0:
            return 0.0
        
        error_rate = errors_in_window / total_requests
        expected_error_rate = 1.0 - self.target_value
        
        if expected_error_rate == 0:
            return 0.0
        
        return error_rate / expected_error_rate


@dataclass
class MetricBuffer:
    """
    Buffers measurements for a specific metric dimension.
    
    Collects raw latency values and computes percentiles on demand.
    """
    
    labels: Dict[str, str]  # e.g., {"endpoint": "/api/book", "service": "booking"}
    latencies: List[float] = field(default_factory=list)  # milliseconds
    errors: int = 0
    success_count: int = 0
    max_size: int = 10000  # Prevent memory exhaustion
    
    def add_request(self, latency_ms: float, success: bool = True) -> None:
        """Record request metric."""
        if len(self.latencies) < self.max_size:
            self.latencies.append(latency_ms)
        
        if success:
            self.success_count += 1
        else:
            self.errors += 1
    
    def calculate_golden_signal(self) -> GoldenSignal:
        """Calculate golden signal metrics (AC-2)."""
        if not self.latencies:
            return GoldenSignal()
        
        sorted_latencies = sorted(self.latencies)
        total_requests = self.success_count + self.errors
        
        return GoldenSignal(
            latency_mean=statistics.mean(self.latencies),
            latency_p50=self._percentile(sorted_latencies, 0.50),
            latency_p95=self._percentile(sorted_latencies, 0.95),  # AC-2
            latency_p99=self._percentile(sorted_latencies, 0.99),
            request_count=total_requests,
            error_count=self.errors,
            success_rate=self.success_count / total_requests if total_requests > 0 else 1.0,
            availability=self.success_count / total_requests if total_requests > 0 else 1.0
        )
    
    @staticmethod
    def _percentile(sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]


class MetricsCollector:
    """
    Collects and aggregates metrics by dimension (METRIC-1, SLO-1, AC-2).
    
    Tracks golden signals per service, endpoint, and operation.
    Computes SLO compliance and error budget burn rate.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.buffers: Dict[str, MetricBuffer] = {}
        self.slo_targets: Dict[str, SLOTarget] = {}
        self.snapshots: List[Tuple[datetime, Dict[str, GoldenSignal]]] = []
    
    def _buffer_key(self, labels: Dict[str, str]) -> str:
        """Generate unique key for label set."""
        items = sorted(labels.items())
        return "|".join(f"{k}={v}" for k, v in items)
    
    def record_request(
        self,
        latency_ms: float,
        success: bool = True,
        service: str = "unknown",
        endpoint: str = "unknown",
        operation: str = "unknown"
    ) -> None:
        """
        Record request metric (METRIC-1, AC-2).
        
        Dimensions: service, endpoint, operation
        """
        labels = {
            "service": service,
            "endpoint": endpoint,
            "operation": operation
        }
        
        key = self._buffer_key(labels)
        
        if key not in self.buffers:
            self.buffers[key] = MetricBuffer(labels=labels)
        
        self.buffers[key].add_request(latency_ms, success)
    
    def register_slo(self, slo: SLOTarget) -> None:
        """Register SLO target (SLO-1)."""
        self.slo_targets[slo.name] = slo
    
    def get_metrics_snapshot(self, service: Optional[str] = None) -> Dict[str, GoldenSignal]:
        """
        Get current metrics snapshot (AC-2).
        
        Returns golden signals for all buffers (or filtered by service).
        """
        snapshot = {}
        
        for key, buffer in self.buffers.items():
            if service and buffer.labels.get("service") != service:
                continue
            
            label_str = " ".join(f"{k}={v}" for k, v in sorted(buffer.labels.items()))
            snapshot[label_str] = buffer.calculate_golden_signal()
        
        # Store snapshot for reporting
        self.snapshots.append((datetime.utcnow(), snapshot))
        
        return snapshot
    
    def get_endpoint_metrics(self, endpoint: str, service: str) -> Optional[GoldenSignal]:
        """Get metrics for specific endpoint (AC-2)."""
        labels = {"service": service, "endpoint": endpoint}
        key = self._buffer_key(labels)
        
        if key not in self.buffers:
            return None
        
        return self.buffers[key].calculate_golden_signal()
    
    def calculate_slo_compliance(
        self,
        slo_name: str,
        metric_snapshot: Dict[str, GoldenSignal]
    ) -> Dict[str, any]:
        """
        Calculate SLO compliance for named SLO (SLO-1).
        
        Returns compliance status, error budget, and burn rate.
        """
        if slo_name not in self.slo_targets:
            return {}
        
        slo = self.slo_targets[slo_name]
        
        # Aggregate metrics
        total_requests = sum(m.request_count for m in metric_snapshot.values())
        total_errors = sum(m.error_count for m in metric_snapshot.values())
        
        # Calculate compliance
        if slo.metric_type == "availability":
            actual_availability = 1.0 - (total_errors / total_requests) if total_requests > 0 else 1.0
            compliant = actual_availability >= slo.target_value
        else:
            compliant = False  # TODO: implement other metric types
        
        # Calculate burn rate
        burn_rate = slo.burn_rate(total_errors, total_requests)
        
        return {
            "slo_name": slo_name,
            "target": slo.target_value,
            "actual": actual_availability if slo.metric_type == "availability" else 0,
            "compliant": compliant,
            "error_budget_seconds": slo.error_budget_seconds(),
            "burn_rate": burn_rate,
            "window_seconds": slo.window_seconds
        }
    
    def get_top_failing_endpoints(self, service: Optional[str] = None, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Get endpoints with highest error rates (AC-2, AC-4).
        
        Useful for dashboard "top failing endpoints" panel.
        """
        endpoints = []
        
        for key, buffer in self.buffers.items():
            if service and buffer.labels.get("service") != service:
                continue
            
            signal = buffer.calculate_golden_signal()
            if signal.request_count > 0:
                endpoint = buffer.labels.get("endpoint", "unknown")
                error_rate = signal.error_rate()
                endpoints.append((endpoint, error_rate))
        
        # Sort by error rate, descending
        endpoints.sort(key=lambda x: x[1], reverse=True)
        return endpoints[:limit]
    
    def reset(self) -> None:
        """Clear all metrics (for testing)."""
        self.buffers.clear()
        self.snapshots.clear()
